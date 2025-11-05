# BA-Agent Nutzung

## Installation

```bash
git clone https://github.com/Future-House/paper-qa
cd paper-qa
git checkout -b feat/ba-agent-ieee
pip install -e .[dev]
pip install pymupdf sentence-transformers faiss-cpu typer streamlit pydantic citeproc-py python-dotenv pytest ruff mypy
```

## Verzeichnisstruktur

```
ba_agent/
  ingest.py      # Quellen einlesen
  index.py       # Chunking und Embeddings
  query.py       # RAG-Pipeline
  review.py      # Reviewer-Agent
  export.py      # Pandoc-Export
  cli.py         # Typer-CLI
  ui.py          # Streamlit-Frontend
```

## CLI-Befehle

```bash
ba-agent ingest --src ./quellen
ba-agent index
ba-agent ask --q "Wie beeinflusst KI die Hochschullehre?"
ba-agent chapter --title Einführung --topic "KI in der Hochschullehre"
ba-agent review --in draft.md
ba-agent export draft.md draft.docx
```

## IEEE-Zitationsformat

Jede Aussage benötigt mindestens eine Referenz im Format `[n]` oder `[n, p. x]`.

Beispieltext:

> Die Ergebnisse in [1] zeigen eine starke Korrelation, wohingegen [2, p. 45] eine gegenteilige Beobachtung beschreibt.

Beispielbibliographie:

```
[1] J. Müller and P. Schmidt, “Digitale Lernplattformen an Hochschulen”, Springer, 2021.
[2] A. Klein, “Adoption von E-Learning-Technologien”, IEEE Access, vol. 9, pp. 11045–11060, 2022.
```
