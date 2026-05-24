# Source Index

This file records the primary source pages used for the first related-work seed pass.

| Topic | Source | Evidence captured | Paper use |
| --- | --- | --- | --- |
| Believable generative agents | https://arxiv.org/abs/2304.03442 | Title, authors, memory / reflection / planning architecture, small-town simulation framing. | Related Work: Generative agents; contrast with goal-conditioned orchestration. |
| Concordia | https://arxiv.org/abs/2312.03664 | Title, authors, Game Master mediator, LLM calls + associative memory, grounded environments. | Related Work: Generative agent-based modeling; compare GM mediation with Director interventions. |
| Drama management | https://www.cs.uky.edu/~sgware/reading/papers/roberts2008survey.pdf | Drama manager as coordinator, authorial control vs player autonomy, qualitative desiderata. | Related Work: interactive narrative / drama management. |
| AutoGen | https://arxiv.org/abs/2308.08155 | Multi-agent conversation framework, customizable conversable agents, tool / human / LLM modes. | Related Work: task-oriented multi-agent orchestration. |
| MetaGPT | https://proceedings.iclr.cc/paper_files/paper/2024/hash/6507b115562bb0a305f1958ccc87355a-Abstract-Conference.html | SOP encoding and assembly-line role decomposition for software tasks. | Related Work: explicit workflow and hard delegation baselines. |
| ChatDev | https://arxiv.org/abs/2307.07924 | Specialized software agents guided by chat chain and communicative dehallucination. | Related Work: software-development agent society baseline. |
| AgentBench | https://arxiv.org/abs/2308.03688 | Interactive environments for evaluating LLM-as-agent reasoning and decision-making. | Related Work: agent evaluation and benchmark framing. |

## Search notes

- `scripts/paper_search.py` was run once under the sandbox and returned zero results because network sockets were denied.
- The command was rerun with network escalation; OpenAlex and Crossref responses were saved under `.run/paper-search-raw/`, which is intentionally ignored by Git through the existing `.run/` rule.
- The long multi-query run timed out while later providers were still pending, so this file prioritizes manually verified primary pages from arXiv, ICLR, ACL, ACM DOI metadata, and the drama-management PDF.
