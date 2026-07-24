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

# Install cargo binstall
[linux]
[macos]
install-cargo-binstall:
    @curl -L --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.sh | bash

# Install cargo binstall
[windows]
install-cargo-binstall:
    @Set-ExecutionPolicy Unrestricted -Scope Process; iex (iwr "https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.ps1").Content

# install the uv package manager
[windows]
install-uv:
    @powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Installs typst cli to render PDFs
install-typst: install-cargo-binstall
    @cargo binstall typst-cli

test: check
    @uv run pytest
    @uv run obsidian-to-typst ./examples/feature_guide/Widget.md

check: format
    @uv run ruff check

fix: format
    @uv run ruff check --fix

format:
    @uv run ruff format
