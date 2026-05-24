# Zotero Intake Workflow

This file defines the lightweight related-work intake loop for Loomstead. The goal is to collect sources early without forcing final novelty claims too soon.

## Current tool status

Checked on 2026-05-24:

- Zotero local API: running at `http://127.0.0.1:23119`.
- Zotero connector endpoint: running.
- Zotero version reported by local API: `9.0.4`.
- Seed searches for `Generative Agents`, `Concordia generative agent`, and `AutoGen multi-agent conversation` returned no local library matches at that time.

## Browser + Zotero route

Use this route for new sources:

1. Open the primary source page with the browser control plugin or normal browser:
   - arXiv abstract page
   - ACM / ACL / ICLR / publisher page
   - author PDF page only when no metadata page exists
2. Save the item through the Zotero connector.
3. Verify the item exists in Zotero:

```powershell
python C:/Users/Administrator/.codex/plugins/cache/openai-curated/zotero/6188456f/skills/zotero/scripts/zotero.py search "<title keyword>" --json
```

4. Record the Zotero item key and planned BibTeX key in `paper/lit_review/reading_queue.md`.
5. Export or sync BibTeX into both bibliography files until a single-source export path is automated:

```powershell
python C:/Users/Administrator/.codex/plugins/cache/openai-curated/zotero/6188456f/skills/zotero/scripts/zotero.py export-bibtex --out paper/references.bib
Copy-Item -LiteralPath paper/references.bib -Destination paper/latex/references.bib
```

Only run the export step when the Zotero library contains the intended paper subset or the export command is scoped to confirmed item keys.

## Intake status labels

| Status | Meaning | Next action |
| --- | --- | --- |
| search-pending | Topic exists, no candidate selected yet. | Search web / Zotero. |
| zotero-saved | Item exists in Zotero with metadata. | Add item key and candidate BibTeX key. |
| skimmed | Abstract / intro / method skim complete. | Write contrast notes. |
| cited-seed | Included in draft citation set. | Keep in BibTeX sync. |
| evidence-anchor | Source directly supports a paper claim. | Link it in claim matrix. |
| rejected | Looked relevant but excluded. | Record reason briefly. |

## Source buckets

Keep notes separated by bucket:

- Believable generative agents and social simulation.
- Drama management and interactive narrative.
- Task-oriented multi-agent orchestration.
- Agent evaluation and trajectory / trace analysis.
- Human believability and narrative evaluation protocols.
- Game AI social memory and relationship systems.

## Conservative use rule

For each source, capture two things before citing it in final prose:

1. What the source actually contributes.
2. The exact contrast point for Loomstead.

If the contrast point is still uncertain, keep the source in `reading_queue.md` and avoid using it as a novelty claim.
