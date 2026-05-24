#!/usr/bin/env python3
"""Check local paper-writing tooling: Zotero, LaTeX, Perl, and Codex plugins."""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"
KNOWN_MIKTEX_BIN_DIRS = [
    Path(r"C:\Program Files\MiKTeX\miktex\bin\x64"),
    Path.home() / "AppData" / "Local" / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
    Path.home() / "AppData" / "Local" / "Programs" / "MiKTeX" / "miktex" / "bin",
]


def http_status(url: str, timeout: int = 3) -> dict[str, Any]:
    """Return a lightweight HTTP probe result for local Zotero endpoints."""

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(240).decode("utf-8", errors="replace")
            return {"ok": 200 <= response.status < 300, "status": response.status, "body": body}
    except urllib.error.HTTPError as exc:
        body = exc.read(240).decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "body": body}
    except Exception as exc:  # pragma: no cover - depends on local Zotero state
        return {"ok": False, "status": None, "error": str(exc)}


def detect_command(name: str) -> dict[str, Any]:
    """Detect a command on PATH or in common MiKTeX installation folders."""

    path = shutil.which(name)
    known_path = None
    for bin_dir in KNOWN_MIKTEX_BIN_DIRS:
        candidate = bin_dir / f"{name}.exe"
        if candidate.exists():
            known_path = str(candidate)
            break
    return {"found": bool(path or known_path), "path": path, "known_path": known_path}


def find_plugin_skill(pattern: str) -> list[str]:
    """Find a skill entry inside the Codex plugin cache."""

    cache = CODEX_HOME / "plugins" / "cache"
    if not cache.exists():
        return []
    return [str(path) for path in cache.rglob(pattern)]


def build_report() -> dict[str, Any]:
    """Build a structured status report for terminal and CI-style checks."""

    commands = {
        name: detect_command(name)
        for name in [
            "zotero",
            "perl",
            "pdflatex",
            "xelatex",
            "latexmk",
            "tectonic",
            "pandoc",
            "bibtex",
            "biber",
        ]
    }
    zotero_api = http_status("http://127.0.0.1:23119/api/schema")
    zotero_connector = http_status("http://127.0.0.1:23119/connector/ping")
    latex_skills = find_plugin_skill("latex-compile/SKILL.md")
    zotero_skills = find_plugin_skill("zotero/SKILL.md")
    bundled_tectonic = find_plugin_skill("tectonic.exe")
    paper_main = ROOT / "paper" / "latex" / "main.tex"
    return {
        "commands": commands,
        "zotero": {
            "local_api": zotero_api,
            "connector": zotero_connector,
            "codex_skill": zotero_skills,
        },
        "latex": {
            "codex_compile_skill": latex_skills,
            "bundled_tectonic": bundled_tectonic,
            "main_tex_exists": paper_main.exists(),
        },
        "ready": {
            "zotero_local_api": zotero_api.get("ok") is True,
            "zotero_connector": zotero_connector.get("ok") is True,
            "zotero_skill_available": bool(zotero_skills),
            "latex_plugin_available": bool(latex_skills),
            "system_tex_available": any(commands[name]["found"] for name in ["pdflatex", "xelatex", "latexmk"]),
            "system_tex_on_path": any(commands[name]["path"] for name in ["pdflatex", "xelatex", "latexmk"]),
            "perl_available": commands["perl"]["found"],
            "latexmk_chain_ready": commands["latexmk"]["found"] and commands["perl"]["found"],
            "biber_available": commands["biber"]["found"],
            "paper_main_tex_exists": paper_main.exists(),
            "bundled_tectonic_available": bool(bundled_tectonic),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print("Paper tooling readiness")
    for key, value in report["ready"].items():
        print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
