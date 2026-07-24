set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

loop:
    @watchexec \
        --clear=clear \
        --restart  \
        --debounce 500 \
        --exts py,md,yml,toml,ini \
        just test

# install the uv package manager
[linux]
[macos]
install-uv:
    @curl -LsSf https://astral.sh/uv/install.sh | sh

# install the uv package manager
[windows]
install-uv:
    @powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Installs typst cli to render PDFs
install-typst:
    @cargo install typst-cli

test: check
    @uv run pytest
    @uv run obsidian-to-typst ./examples/feature_guide/Widget.md

check: format
    @uv run ruff check

fix: format
    @uv run ruff check --fix

format:
    @uv run ruff format
