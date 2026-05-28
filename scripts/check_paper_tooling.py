#!/usr/bin/env python3
"""Check local paper-writing tooling: Zotero, LaTeX, Mermaid, Perl, and Codex plugins."""

from __future__ import annotations

import argparse
import json
import os
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
BROWSER_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
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


def detect_local_mmdc() -> dict[str, Any]:
    """Detect the project-local Mermaid CLI installed by npm."""

    candidates = [ROOT / "node_modules" / ".bin" / "mmdc.cmd", ROOT / "node_modules" / ".bin" / "mmdc"]
    path = shutil.which("mmdc")
    local_path = next((str(candidate) for candidate in candidates if candidate.exists()), None)
    return {"found": bool(path or local_path), "path": path, "local_path": local_path}


def detect_browser() -> dict[str, Any]:
    """Detect a browser usable by Puppeteer / Mermaid CLI."""

    env_path = None
    for key in ["PUPPETEER_EXECUTABLE_PATH", "CHROME_BIN"]:
        value = os.environ.get(key)
        if value and Path(value).exists():
            env_path = value
            break
    command_path = shutil.which("chrome") or shutil.which("msedge")
    known_path = next((str(candidate) for candidate in BROWSER_CANDIDATES if candidate.exists()), None)
    return {"found": bool(env_path or command_path or known_path), "env_path": env_path, "path": command_path, "known_path": known_path}


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
    mmdc = detect_local_mmdc()
    browser = detect_browser()
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
        "mermaid": {
            "mmdc": mmdc,
            "browser": browser,
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
            "mermaid_cli_available": mmdc["found"],
            "mermaid_browser_available": browser["found"],
            "mermaid_render_ready": mmdc["found"] and browser["found"],
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
