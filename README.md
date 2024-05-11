# Obsidian to Typst

This utility attempts to make it easy to convert markdown documents written using obsidian into PDFs.

## Requirements

- typst
- mermaid
- mutool

## Getting Started

This project uses python [poetry](https://python-poetry.org/).  Follow the [intallation instructions](https://python-poetry.org/docs/#installation) for poetry.

Install typst using a package manager or `cargo install`

Run `poetry install` and `poetry shell` to install and and activate the python virtual environment.

Than, run `obsidian_to_typst .\examples\feature_guide\Widget.md` to convert the example document to a PDF.  The PDF will be placed in `.\examples\feature_guide\output\Widget.pdf`.

```powershell
watchexec --clear --restart --debounce 500 --exts py "isort . && black . && pytest && obsidian-to-typst ./examples/feature_guide/Widget.md"
```
