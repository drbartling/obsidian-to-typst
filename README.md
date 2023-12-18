# Obsidian to Latex

This utility attempts to make it easy to convert markdown documents written using obsidian into PDFs.

## Requirements

- latex
- mermaid

## Getting Started

This project uses python [poetry](https://python-poetry.org/).  Follow the [intallation instructions](https://python-poetry.org/docs/#installation) for poetry.

I'm using miktex for latex support.  On windows, you can run `winget install miktex`

Run `poetry install` and `poetry shell` to install and and activate the python virtual environment.

Than, run `obsidian_to_latex .\examples\feature_guide\Widget.md` to convert the example document to a PDF.  The PDF will be placed in `.\examples\feature_guide\output\Widget.pdf`.

```powershell
watchexec.exe -crd500 -e py "isort . && black . && pytest && obsidian_to_latex.cmd .\examples\feature_guide\Widget.md"
```
