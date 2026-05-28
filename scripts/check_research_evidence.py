from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMOTED_DIR = ROOT / ".run" / "eval-promoted"
ROBUSTNESS_SUITE = "evidence_robustness"
STRICT_GATE_VERSION = "phase2.evidence_robustness.strict_gate.v1"
EXPECTED_DOMAIN_GROUPS = {"loomstead.coding.v0", "loomstead.town.v0"}
EXPECTED_SIGNATURE_IDS = {
    "process_signature.v1",
    "phase2.evidence_robustness.domain_signature.v2.coding",
    "phase2.evidence_robustness.domain_signature.v2.narrative",
}
EXPECTED_ARTIFACT_KINDS = {
    "summary_json",
    "process_robustness_json",
    "domain_robustness_json",
    "strict_gate_json",
    "signature_summary_json",
    "perturbation_details_jsonl",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check promoted research evidence gates.")
    parser.add_argument("--promoted-dir", type=Path, default=DEFAULT_PROMOTED_DIR)
    parser.add_argument("--suite", default=ROBUSTNESS_SUITE)
    parser.add_argument("--min-seeds", type=int, default=5)
    args = parser.parse_args()

    promoted_dir = args.promoted_dir if args.promoted_dir.is_absolute() else ROOT / args.promoted_dir
    manifest_path = _latest_manifest(promoted_dir, suite=str(args.suite))
    errors: list[str] = []
    warnings: list[str] = []
    if manifest_path is None:
        errors.append(f"missing promoted manifest for suite={args.suite}: {promoted_dir}")
        _print_result(None, errors, warnings)
        raise SystemExit(1)

    manifest = _read_json(manifest_path)
    _check_robustness_manifest(manifest, errors=errors, warnings=warnings, min_seeds=max(1, int(args.min_seeds)))
    _print_result(manifest_path, errors, warnings, manifest=manifest)
    if errors:
        raise SystemExit(1)


def _latest_manifest(promoted_dir: Path, *, suite: str) -> Path | None:
    candidates: list[tuple[tuple[int, float | str], Path]] = []
    if not promoted_dir.exists():
        return None
    for manifest_path in promoted_dir.glob("*/manifest.json"):
        try:
            manifest = _read_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("suite") != suite:
            continue
        candidates.append((_time_key(manifest.get("createdAt"), manifest_path.stat().st_mtime), manifest_path))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def _check_robustness_manifest(
    manifest: dict[str, Any],
    *,
    errors: list[str],
    warnings: list[str],
    min_seeds: int,
) -> None:
    if manifest.get("manifestVersion") != "phase2.eval_manifest.v1":
        errors.append(f"manifestVersion mismatch: {manifest.get('manifestVersion')}")
    if manifest.get("suite") != ROBUSTNESS_SUITE:
        errors.append(f"suite mismatch: {manifest.get('suite')}")
    if not bool(manifest.get("ok")):
        errors.append("manifest ok=false")
    git = manifest.get("git", {}) if isinstance(manifest.get("git"), dict) else {}
    if bool(git.get("dirty")):
        errors.append("manifest git.dirty=true")

    seed_count = manifest.get("seedCount", {}) if isinstance(manifest.get("seedCount"), dict) else {}
    for key in ("process", "domain"):
        observed = int(seed_count.get(key) or 0)
        if observed < min_seeds:
            errors.append(f"seedCount.{key}={observed}, expected >= {min_seeds}")

    scenario_ids = [str(item) for item in manifest.get("scenarioIds", []) if str(item)] if isinstance(manifest.get("scenarioIds"), list) else []
    scenario_counts = {
        "process": sum(1 for item in scenario_ids if item.startswith("pf.")),
        "coding": sum(1 for item in scenario_ids if item.startswith("coding.")),
        "narrative": sum(1 for item in scenario_ids if item.startswith("narrative.")),
    }
    if scenario_counts["process"] < 4:
        errors.append(f"process scenarioIds too small: {scenario_counts['process']}")
    if scenario_counts["coding"] < 8:
        errors.append(f"coding scenarioIds too small: {scenario_counts['coding']}")
    if scenario_counts["narrative"] < 3:
        errors.append(f"narrative scenarioIds too small: {scenario_counts['narrative']}")

    eval_gates = manifest.get("evalGates", {}) if isinstance(manifest.get("evalGates"), dict) else {}
    strict_gate = eval_gates.get("strictGate", {}) if isinstance(eval_gates.get("strictGate"), dict) else {}
    if strict_gate.get("gateVersion") != STRICT_GATE_VERSION:
        errors.append(f"strict gate version mismatch: {strict_gate.get('gateVersion')}")
    if not bool(strict_gate.get("pass")):
        errors.append("strict gate pass=false")
    if int(strict_gate.get("failedCheckCount") or 0) != 0:
        errors.append(f"strict gate failedCheckCount={strict_gate.get('failedCheckCount')}")

    signature_ids = _signature_ids(eval_gates.get("signatureKinds"))
    missing_signatures = sorted(EXPECTED_SIGNATURE_IDS - signature_ids)
    if missing_signatures:
        errors.append(f"missing signature kinds: {missing_signatures}")

    domain_groups = _domain_groups(eval_gates.get("domainGroups"))
    missing_groups = sorted(EXPECTED_DOMAIN_GROUPS - set(domain_groups))
    if missing_groups:
        errors.append(f"missing domain groups: {missing_groups}")
    for group_id in sorted(EXPECTED_DOMAIN_GROUPS & set(domain_groups)):
        group = domain_groups[group_id]
        if not bool(group.get("allStable")):
            errors.append(f"domain group {group_id} allStable=false")
        if float(group.get("overallInvarianceRate") or 0.0) < 1.0:
            errors.append(f"domain group {group_id} invariance < 1.0")
        if int(group.get("total") or 0) <= 0:
            errors.append(f"domain group {group_id} has no checks")

    artifact_kinds = {
        str(artifact.get("kind") or "")
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, dict)
    }
    missing_artifacts = sorted(EXPECTED_ARTIFACT_KINDS - artifact_kinds)
    if missing_artifacts:
        errors.append(f"missing artifact kinds: {missing_artifacts}")
    if manifest.get("llmEvidence"):
        warnings.append("robustness manifest unexpectedly carries llmEvidence")


def _signature_ids(signature_kinds: Any) -> set[str]:
    ids: set[str] = set()
    if not isinstance(signature_kinds, dict):
        return ids
    for values in signature_kinds.values():
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict) and item.get("signatureId"):
                ids.add(str(item["signatureId"]))
    return ids


def _domain_groups(raw_groups: Any) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_groups, list):
        return groups
    for item in raw_groups:
        if isinstance(item, dict) and item.get("groupId"):
            groups[str(item["groupId"])] = item
    return groups


def _print_result(
    manifest_path: Path | None,
    errors: list[str],
    warnings: list[str],
    *,
    manifest: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "ok": not errors,
        "check": "research_evidence.robustness_strict_gate",
        "manifestPath": _repo_relative(manifest_path) if manifest_path else None,
        "errors": errors,
        "warnings": warnings,
    }
    if manifest:
        payload["runDirName"] = manifest.get("runDirName")
        payload["git"] = manifest.get("git", {})
        payload["seedCount"] = manifest.get("seedCount")
        payload["scenarioCount"] = len(manifest.get("scenarioIds", [])) if isinstance(manifest.get("scenarioIds"), list) else 0
        payload["evalGates"] = manifest.get("evalGates", {})
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _time_key(value: Any, fallback: float) -> tuple[int, float | str]:
    if not value:
        return (0, fallback)
    try:
        return (1, datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return (0, str(value))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_relative(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
