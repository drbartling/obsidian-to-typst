import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import click
import colorama
import colored_traceback
import coloredlogs
import pydantic

from obsidian_to_latex import obsidian_path, process_markdown


@click.command
@click.argument(
    "filename",
    type=click.Path(path_type=Path, resolve_path=True),
)
@click.option(
    "-t",
    "--template",
    type=click.Path(path_type=Path, resolve_path=True),
)
@pydantic.validate_arguments
def main(filename: Path, template: Optional[Path]):  # pragma: no cover
    colorama.init()
    colored_traceback.add_hook()
    coloredlogs.install(level="INFO")

    obsidian_path.VAULT_ROOT = get_vault_root(filename)

    # pylint: disable=protected-access
    process_markdown.STATE.file.append(filename)
    with open(filename, "r", encoding="UTF-8") as f:
        text = f.read()
    title = get_title(text)
    temp_dir = filename.parent / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    process_markdown.STATE.temp_dir = temp_dir
    process_markdown.STATE.file.append(filename)
    temp_file = temp_dir / "body.tex"

    latex = process_markdown.obsidian_to_tex(text)
    with open(temp_file, "w", encoding="UTF-8") as f:
        f.write(latex)

    latex_wrapper = (
        template if template else Path(__file__).parent / "document.tex"
    )
    temp_wrapper = temp_dir / latex_wrapper.name

    with open(latex_wrapper, "r", encoding="UTF-8") as f:
        wrapper_text = f.read()
    wrapper_text = wrapper_text.replace("TheTitleOfTheDocument", title)

    with open(temp_wrapper, "w", encoding="UTF-8") as f:
        f.write(wrapper_text)
    subprocess.run(
        [
            "latexmk",
            "-pdf",
            "-g",
            '-latexoption="-shell-escape -file-line-error -halt-on-error"',
            temp_wrapper,
        ],
        check=False,
        capture_output=False,
        cwd=temp_wrapper.parent,
    )
    temp_pdf = temp_wrapper.with_suffix(".pdf")
    out_dir = filename.parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = (out_dir / filename.name).with_suffix(".pdf")
    try:
        shutil.copy(temp_pdf, out_pdf)
    except FileNotFoundError:
        msg = f"Failed to create PDF: `{out_pdf}`"
        logging.getLogger(__name__).error(msg)
        raise FileNotFoundError(msg) from None


def get_vault_root(path: Path) -> Path:  # pragma: no cover
    if (path / ".obsidian").exists():
        return path
    if (path / ".git").exists():
        logging.getLogger(__name__).info("Using .git for locating vault root")
        return path
    if path.parent == path:
        raise FileNotFoundError("Unable to locate `.obsidian` folder")
    return get_vault_root(path.parent)


def get_title(text: str) -> str:  # pragma: no cover
    line = text.splitlines()[0]
    m = re.match(r"(^#*)\s*(.*)", line)
    if not m:
        return None
    title = m.group(2)
    return title
