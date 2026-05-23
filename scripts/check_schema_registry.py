"""校验 Phase 2 runtime schema registry 的覆盖与迁移护栏。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "backend" / "app"
VERSION_LITERAL_PATTERN = re.compile(r"""["']([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\.v\d+)["']""")
REQUIRE_SCHEMA_PATTERN = re.compile(r"""require_schema_version\(["']([a-z][a-z0-9_]*)["']\)""")
VERSION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\.v\d+$")
REQUIRED_DEFINITION_FIELDS = {
    "id",
    "version",
    "owner",
    "status",
    "description",
    "producer",
    "debugSurface",
    "requiredFields",
    "notes",
}


def main() -> None:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.runtime.schema_registry import (  # noqa: PLC0415
        SCHEMA_DEFINITIONS,
        SCHEMA_REGISTRY_VERSION,
        RuntimeSchemaDefinition,
        schema_registry_snapshot,
        schema_version_map,
    )

    errors: list[str] = []
    warnings: list[str] = []

    _check_registry_shape(
        SCHEMA_DEFINITIONS,
        RuntimeSchemaDefinition,
        SCHEMA_REGISTRY_VERSION,
        schema_registry_snapshot(),
        schema_version_map(),
        errors,
    )
    _check_source_usage(SCHEMA_DEFINITIONS, errors, warnings)

    result = {
        "ok": not errors,
        "registryVersion": SCHEMA_REGISTRY_VERSION,
        "schemaCount": len(SCHEMA_DEFINITIONS),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


def _check_registry_shape(
    definitions: dict[str, Any],
    definition_type: type,
    registry_version: str,
    snapshot: dict[str, Any],
    versions: dict[str, str],
    errors: list[str],
) -> None:
    """校验 registry 内部结构，防止版本表和快照分叉。"""
    if registry_version != "schema_registry.v1":
        errors.append(f"SCHEMA_REGISTRY_VERSION 应为 schema_registry.v1，实际为 {registry_version}")
    if set(definitions) != set(versions):
        errors.append("SCHEMA_DEFINITIONS 与 schema_version_map key 不一致")
    if snapshot.get("registryVersion") != registry_version:
        errors.append("schema_registry_snapshot.registryVersion 与 SCHEMA_REGISTRY_VERSION 不一致")
    if snapshot.get("versions") != versions:
        errors.append("schema_registry_snapshot.versions 与 schema_version_map 不一致")

    schemas = snapshot.get("schemas")
    if not isinstance(schemas, list) or len(schemas) != len(definitions):
        errors.append("schema_registry_snapshot.schemas 数量应等于 SCHEMA_DEFINITIONS")
    else:
        for index, schema in enumerate(schemas):
            _check_snapshot_schema(index, schema, errors)

    for schema_id, definition in definitions.items():
        if not isinstance(definition, definition_type):
            errors.append(f"{schema_id}: registry definition 类型错误")
            continue
        if schema_id != definition.schema_id:
            errors.append(f"{schema_id}: dict key 与 schema_id 不一致：{definition.schema_id}")
        if not VERSION_PATTERN.match(definition.version):
            errors.append(f"{schema_id}: version 格式非法：{definition.version}")
        if not definition.owner:
            errors.append(f"{schema_id}: owner 不能为空")
        if definition.status not in {"active", "legacy_compat"}:
            errors.append(f"{schema_id}: status 非法：{definition.status}")
        if not definition.description or not definition.producer or not definition.debug_surface:
            errors.append(f"{schema_id}: description / producer / debug_surface 不能为空")
        if not definition.required_fields:
            errors.append(f"{schema_id}: required_fields 不能为空")
        if len(set(definition.required_fields)) != len(definition.required_fields):
            errors.append(f"{schema_id}: required_fields 存在重复字段")


def _check_snapshot_schema(index: int, schema: Any, errors: list[str]) -> None:
    """校验对外快照条目，避免 Debug / Eval 消费者拿到缺字段对象。"""
    if not isinstance(schema, dict):
        errors.append(f"schemas[{index}] 应为对象")
        return
    missing = sorted(REQUIRED_DEFINITION_FIELDS - set(schema))
    if missing:
        errors.append(f"schemas[{index}] 缺少字段：{missing}")
    if not isinstance(schema.get("requiredFields"), list) or not schema.get("requiredFields"):
        errors.append(f"schemas[{index}].requiredFields 应为非空数组")
    if not isinstance(schema.get("notes"), list):
        errors.append(f"schemas[{index}].notes 应为数组")


def _check_source_usage(definitions: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    """扫描源码中的 schema 使用，禁止生产者绕过 registry 写版本字面量。"""
    registry_path = (BACKEND_APP / "runtime" / "schema_registry.py").resolve()
    schema_ids = set(definitions)
    managed_versions = {str(definition.version) for definition in definitions.values()}
    managed_prefixes = {version.rsplit(".v", 1)[0] for version in managed_versions}
    referenced_ids: set[str] = set()
    stray_version_literals: list[str] = []

    for path in sorted(BACKEND_APP.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for match in REQUIRE_SCHEMA_PATTERN.finditer(text):
            schema_id = match.group(1)
            referenced_ids.add(schema_id)
            if schema_id not in schema_ids:
                line_no = text[: match.start()].count("\n") + 1
                errors.append(f"{relative}:{line_no}: require_schema_version 引用了未知 schema id：{schema_id}")

        if path.resolve() == registry_path:
            continue
        for match in VERSION_LITERAL_PATTERN.finditer(text):
            version_literal = match.group(1)
            version_prefix = version_literal.rsplit(".v", 1)[0]
            if version_literal not in managed_versions and version_prefix not in managed_prefixes:
                continue
            line_no = text[: match.start()].count("\n") + 1
            stray_version_literals.append(f"{relative}:{line_no}: {version_literal}")

    if stray_version_literals:
        errors.append("schema version 字面量只能出现在 backend/app/runtime/schema_registry.py")
        errors.extend(stray_version_literals)

    unused_ids = sorted(schema_ids - referenced_ids - {"schema_registry"})
    if unused_ids:
        warnings.append(f"registry 中存在当前源码未直接 require 的 schema id：{unused_ids}")


if __name__ == "__main__":
    main()
