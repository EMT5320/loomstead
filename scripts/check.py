"""跨平台检查脚本：编译 Python 后端、检查前端 JS、运行 smoke test。"""

from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KNOWN_NODE_PATHS = [
    Path("/mnt/c/Program Files/nodejs/node.exe"),
    Path("/mnt/c/Program Files (x86)/nodejs/node.exe"),
]


def find_node() -> str:
    """优先使用当前环境 Node；WSL 下可回退到 Windows Node。"""
    for command in ("node", "node.exe"):
        found = shutil.which(command)
        if found:
            return found
    for path in KNOWN_NODE_PATHS:
        if path.exists():
            return str(path)
    raise RuntimeError("未找到 Node.js，可安装 WSL Node 或使用 Windows Node。")

# Windows 上仓库内的 __pycache__ 可能被权限或占用状态卡住。
# 检查脚本只需要验证 Python 文件能编译通过，因此把字节码写到临时目录，避免污染源码树。
with tempfile.TemporaryDirectory(prefix="agent-town-check-") as cache_dir:
    cache_root = Path(cache_dir)
    for path in sorted((ROOT / "backend" / "app").rglob("*.py")):
        relative = path.relative_to(ROOT).with_suffix(".pyc")
        cfile = cache_root / relative
        cfile.parent.mkdir(parents=True, exist_ok=True)
        py_compile.compile(str(path), cfile=str(cfile), doraise=True)

frontend_check = subprocess.run([find_node(), "--check", "frontend/app.js"], cwd=ROOT)
if frontend_check.returncode != 0:
    raise SystemExit(frontend_check.returncode)

model_config_check = subprocess.run([sys.executable, "scripts/check_model_config.py"], cwd=ROOT)
if model_config_check.returncode != 0:
    raise SystemExit(model_config_check.returncode)

smoke = subprocess.run([sys.executable, "scripts/smoke_test.py"], cwd=ROOT)
if smoke.returncode != 0:
    raise SystemExit(smoke.returncode)

agent_eval = subprocess.run([sys.executable, "scripts/run_agent_eval.py"], cwd=ROOT)
if agent_eval.returncode != 0:
    raise SystemExit(agent_eval.returncode)

domain_eval = subprocess.run([sys.executable, "scripts/run_agent_eval.py", "--suite", "domain"], cwd=ROOT)
if domain_eval.returncode != 0:
    raise SystemExit(domain_eval.returncode)

asset_manifest_check = subprocess.run([sys.executable, "scripts/check_asset_manifest.py"], cwd=ROOT)
if asset_manifest_check.returncode != 0:
    raise SystemExit(asset_manifest_check.returncode)

npc_codex_check = subprocess.run([sys.executable, "scripts/check_npc_codex.py"], cwd=ROOT)
if npc_codex_check.returncode != 0:
    raise SystemExit(npc_codex_check.returncode)

life_action_target_check = subprocess.run([sys.executable, "scripts/check_life_action_targets.py"], cwd=ROOT)
if life_action_target_check.returncode != 0:
    raise SystemExit(life_action_target_check.returncode)

godot_check = subprocess.run([sys.executable, "scripts/check_godot_project.py"], cwd=ROOT)
if godot_check.returncode != 0:
    raise SystemExit(godot_check.returncode)
