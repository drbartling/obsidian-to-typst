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

from obsidian_to_typst import obsidian_path, process_markdown

logger = logging.getLogger(__name__)


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
@pydantic.validate_call
def main(filename: Path, template: Optional[Path]):  # pragma: no cover
    colorama.init()
    colored_traceback.add_hook()
    coloredlogs.install(level="INFO")
    try:
        app_main(filename, template)
    except Exception as _e:
        logger.critical("Failed to export document to PDF using typst")
        raise


@pydantic.validate_call
def app_main(filename: Path, template: Optional[Path]):  # pragma: no cover
    # pylint: disable=too-many-locals
    obsidian_path.VAULT_ROOT = get_vault_root(filename)

    # pylint: disable=protected-access
    with filename.open(mode="r", encoding="utf-8") as f:
        text = f.read()

    title = get_title(text)
    temp_dir = filename.parent / "temp"
    obsidian_path.TEMP_FOLDER = temp_dir
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / "body.typ"

    process_markdown.init_state(temp_dir, filename)
    typst = process_markdown.obsidian_to_typst(text)
    with open(temp_file, "w", encoding="UTF-8") as f:
        f.write(typst)

    typst_wrapper = (
        template if template else Path(__file__).parent / "document.typ"
    )
    temp_wrapper = temp_dir / typst_wrapper.name

    with open(typst_wrapper, "r", encoding="UTF-8") as f:
        wrapper_text = f.read()
    wrapper_text = wrapper_text.replace("TheTitleOfTheDocument", title)
    wrapper_text += typst

    with open(temp_wrapper, "w", encoding="UTF-8") as f:
        f.write(wrapper_text)

    args = [
        "typst",
        "compile",
        temp_wrapper,
        "--root",
        obsidian_path.VAULT_ROOT,
    ]
    logging.info("Running `%s`", " ".join([str(a) for a in args]))
    try:
        typst_result = subprocess.run(
            args,
            check=True,
            capture_output=False,
            cwd=temp_wrapper.parent,
        )
    except FileNotFoundError:
        logger.error("Failed to call typst.  Ensure typst is installed")
        raise
    if typst_result.returncode:
        logger.error(
            "Typst failed to complete.  Document may not be setup correctly"
        )
        raise Exception("Subprocess Failed")

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
