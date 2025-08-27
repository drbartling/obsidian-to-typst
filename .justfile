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
install_uv:
    @curl -LsSf https://astral.sh/uv/install.sh | sh

# install the uv package manager
[windows]
install_uv:
    @powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

test: check
    @uv run pytest
    @uv run obsidian-to-typst ./examples/feature_guide/Widget.md

check: format
    @uv run ruff check

fix: format
    @uv run ruff check --fix

format:
    @uv run ruff format

setup:
    @uv venv --python 3.13.0
    @uv sync
