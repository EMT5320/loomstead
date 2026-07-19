"""Portfolio evidence snippets 生成稳定性回归测试。"""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import build_portfolio_evidence_snippets as snippets  # noqa: E402


def test_generated_snippets_use_evidence_snapshot_date() -> None:
    """生成结果应绑定已复核证据快照，不能随 CI 运行日期漂移。"""

    markdown = snippets.build_markdown()

    assert "last_verified: 2026-07-17" in markdown
