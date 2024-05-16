import logging
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import pydantic
from pydantic.dataclasses import dataclass

from obsidian_to_typst import obsidian_path

_logger = logging.getLogger(__name__)

referenced_docs = set()
docs_embedded = set()

EMBEDDED_IMAGE_REGEX = r"!\[\[([\s_a-zA-Z0-9.]*)\|?([0-9]+)?x?([0-9]+)?]]"


@dataclass
class Indent:
    list_type: str
    depth: str


@dataclass
class State:
    # pylint: disable=too-many-instance-attributes
    heading_depth: int
    parent_heading_depth: int
    code_block: Optional[int]
    code_buffer: str
    mermaid_block: Optional[int]
    file: List[Path]
    temp_dir: Optional[Path]
    typst_block: Optional[int]

    @classmethod
    def new(cls):
        return cls(
            heading_depth=0,
            parent_heading_depth=0,
            code_block=None,
            code_buffer="",
            mermaid_block=None,
            file=[],
            temp_dir=None,
            typst_block=None,
        )

    def init(self, temp_dir: Path, file: Path):
        self.heading_depth = 0
        self.parent_heading_depth = 0
        self.code_block = None
        self.code_buffer = ""
        self.mermaid_block = None
        self.file = [file]
        self.temp_dir = temp_dir
        self.typst_block = None


STATE: State = State.new()


@pydantic.validate_call
def init_state(temp_dir: Path, file: Path) -> None:
    STATE.init(temp_dir, file)


@pydantic.validate_call
def obsidian_to_typst(input_text: str) -> str:
    lines = input_text.splitlines()
    lines = [_line_to_typst(i + 1, line) for i, line in enumerate(lines)]
    lines = [line for line in lines if line is not None]
    lines.append("")
    text = "\n".join(lines)
    text = text + cleanup()
    return text


@pydantic.validate_call
def _line_to_typst(
    lineno: int,
    line: str,
) -> str:
    try:
        return line_to_typst(lineno, line)
    except Exception:  # pragma: no cover
        logging.getLogger(__name__).error(
            "Failed to parse `%s:%s`", STATE.file[-1], lineno
        )
        raise


@pydantic.validate_call
def line_to_typst(
    lineno: int,
    line: str,
) -> Optional[str]:
    # pylint: disable=too-many-return-statements

    if is_code_block_toggle(line):
        return toggle_code_block(lineno, line)
    if STATE.code_block:
        return line
    if STATE.mermaid_block:
        STATE.code_buffer += line + "\n"
        return None
    if is_embedded(line):
        return embed_file(line)
    if line.startswith("#"):
        return line_to_section(line)
    line = string_to_typst(line)
    return line


@pydantic.validate_call
def line_to_section(line: str) -> str:
    assert line.startswith("#"), line
    section_lookup = {
        2: "=",
        3: "==",
        4: "===",
        5: "====",
        6: "=====",
    }
    s, line = re.match(r"(#*)\s*(.*)", line).groups()
    STATE.heading_depth = len(s) + STATE.parent_heading_depth

    if STATE.heading_depth not in section_lookup:
        return line + "\n\n"

    line = string_to_typst(line)
    section_text = f"#heading(level:{STATE.heading_depth - 1})[{line}]"

    return section_text


@pydantic.validate_call
def is_embedded(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("![[") and stripped.endswith("]]")


@pydantic.validate_call
def embed_file(line: str) -> str:
    stripped = line.strip()
    if is_markdown(stripped):
        return embed_markdown(stripped)
    if is_image(stripped):
        return embed_image(stripped)
    raise Exception(f"Unable to embed {stripped}")  # pragma: no cover


@pydantic.validate_call
def is_markdown(line: str) -> bool:
    m = re.match(r"!\[\[(.*)]]", line)
    file_name = m.group(1)
    return Path(file_name).suffix == ""


@pydantic.validate_call
def embed_markdown(embed_line: str) -> str:
    m = re.match(r"!\[\[(.*)]]", embed_line)
    file_name = m.group(1)
    assert is_markdown(embed_line), embed_line

    file_name = file_name + ".md"
    file = obsidian_path.find_file(file_name)

    with open(file, "r", encoding="UTF-8") as f:
        text = f.read()

    STATE.file.append(file)
    current_parent_depth = STATE.parent_heading_depth
    STATE.parent_heading_depth = STATE.heading_depth - 1
    try:
        result = obsidian_to_typst(text)
    finally:
        STATE.file.pop()
        STATE.heading_depth = STATE.parent_heading_depth + 1
        STATE.parent_heading_depth = current_parent_depth

    ref_label = file_ref_label(file)
    docs_embedded.add(ref_label)
    return file_label(file) + result


@pydantic.validate_call
def is_image(line: str) -> bool:
    m = re.match(EMBEDDED_IMAGE_REGEX, line)
    if not m:
        return False
    file_name = m.group(1)
    return Path(file_name).suffix.lower() in [".jpg", ".png", ".bmp", ".svg"]


@pydantic.validate_call
def embed_image(line: str) -> str:
    assert is_image(line), line
    m = re.match(EMBEDDED_IMAGE_REGEX, line)
    if not m:  # pragma: no cover
        raise Exception(line)
    file_name, width, height = m.groups()
    return include_image(
        obsidian_path.find_file(file_name),
        width,
        height,
    )


@pydantic.validate_call
def include_image(
    image_path: Path, width: Optional[int], height: Optional[int]
) -> str:
    width_text = R"80%" if width is None else f"{int(width / 2)}pt"
    height_text = "" if height is None else f"height:{int(height / 2)}pt,"

    image_path = obsidian_path.root_path(image_path)
    return f'#image("{image_path}",width:{width_text},{height_text})'


@pydantic.validate_call
def is_code_block_toggle(line: str) -> bool:
    return re.match(r"\s*```", line) is not None


@pydantic.validate_call
def toggle_code_block(
    lineno: int,
    line: str,
) -> str:
    # pylint: disable=global-statement
    if not (STATE.code_block or STATE.mermaid_block):
        STATE.code_buffer = ""
        lang = line[3:]
        if "mermaid" == lang:
            STATE.mermaid_block = lineno
            lines = [
                R"",
                R"#image(",
                f'"{STATE.file[-1].stem}_{STATE.mermaid_block}.png",',
                R"width: 80%)",
            ]
            return "\n".join(lines)

        if "typst" == lang:
            STATE.code_block = lineno
            STATE.typst_block = lineno
            lines = ["#fit(["]
            return "\n".join(lines)

        STATE.code_block = lineno
        lines = [
            R"",
            R"#block(",
            "fill: luma(230),",
            "inset: 8pt,",
            "radius: 2pt,",
            "stroke: black,",
            line,
        ]
        return "\n".join(lines)

    lines = []
    if STATE.typst_block:
        STATE.code_block = None
        STATE.typst_block = None
        lines = ["])"]

    if STATE.code_block:
        STATE.code_block = None
        lines = [
            line,
            ")",
        ]
    if STATE.mermaid_block:
        assert STATE.temp_dir, STATE.temp_dir
        process_mermaid_diagram()
        STATE.mermaid_block = None
        lines = []
    return "\n".join(lines)


@pydantic.validate_call
def process_mermaid_diagram():  # pragma: no cover
    assert STATE.temp_dir, STATE.temp_dir
    assert STATE.mermaid_block, STATE.mermaid_block
    assert STATE.file, STATE.file
    mmd_file: Path = (
        STATE.temp_dir / f"{STATE.file[-1].stem}_{STATE.mermaid_block}.mmd"
    )
    img_file = mmd_file.with_suffix(".png")
    with open(mmd_file, "w", encoding="UTF-8") as f:
        f.write(STATE.code_buffer)
    cmd_str = (
        "mmdc "
        f"--input '{mmd_file}' "
        f"--output '{img_file}' "
        "--backgroundColor transparent "
        "--scale 4 "
    )
    cmd_str += root_check()
    try:
        subprocess.run(cmd_str, shell=True, check=True)
    except subprocess.CalledProcessError:
        _logger.error(
            "Failed to generate MMD diagram for `%s` with command `%s`.",
            STATE.file[-1],
            cmd_str,
        )
        raise


def root_check():
    if os.geteuid() == 0:
        config_file = obsidian_path.TEMP_FOLDER / "pup.json"
        with open(config_file, "w", encoding="UTF-8") as f:
            f.write('{"args": ["--no-sandbox"]}')
        return f' --puppeteerConfigFile "{config_file}" '
    return ""


@pydantic.validate_call
def sanitize_special_characters(line: str) -> str:
    return re.sub(r"([&$#%{}])(?!.*`)", r"\\\1", line)


@pydantic.validate_call
def cleanup():
    assert (
        not STATE.code_block
    ), f"Reached end of file without closing code block from line {STATE.code_block}"
    lines = [""]
    if len(STATE.file) == 1:
        undefined_refs = [
            ref for ref in referenced_docs if ref not in docs_embedded
        ]
        for ref in undefined_refs:
            lines.append(f"<{ref}>")
            _logger.warning("Undefined ref %s", ref)
    return "\n\n.".join(lines)


@pydantic.validate_call
def string_to_typst(unprocessed_text: str) -> str:
    logging.getLogger(__name__).debug("unprocessed_text %s", unprocessed_text)
    processed_text = ""

    try:
        while unprocessed_text:
            char = unprocessed_text[0]
            unprocessed_text = unprocessed_text[1:]
            if char == "`":
                pt, unprocessed_text = split_verbatim(unprocessed_text)
                processed_text += pt
            elif char == "*":
                pt, unprocessed_text = split_formatted(unprocessed_text)
                processed_text += pt
            elif char == "[":
                pt, unprocessed_text = split_link(unprocessed_text)
                processed_text += pt
            elif char == "^":
                pt, unprocessed_text = split_reference(unprocessed_text)
                processed_text += pt
            elif char == "\\":
                pt, unprocessed_text = split_escaped_text(unprocessed_text)
                processed_text += pt
            elif char == "!":
                pt, unprocessed_text = split_embedded_doc(
                    char + unprocessed_text
                )
                processed_text += pt
            else:
                processed_text += sanitize_special_characters(char)
    except Exception:
        logging.getLogger(__name__).error(
            "Failed to parse `%s`", unprocessed_text
        )
        raise

    return processed_text


@pydantic.validate_call
def split_verbatim(text: str) -> Tuple[str, str]:
    processed_text = R"`"
    verb_text, unprocessed_text = re.match(r"(.*?`)(.*)", text).groups()
    processed_text += verb_text
    return processed_text, unprocessed_text


@pydantic.validate_call
def split_formatted(text: str) -> Tuple[str, str]:
    if text.startswith("*"):
        return split_bold(text)
    return split_italics(text)


def split_bold(text: str) -> Tuple[str, str]:
    processed_text = R"*"
    bold_text, unprocessed_text = re.match(
        r"\*(.*?\**)\*\*(.*)", text
    ).groups()

    bold_text = string_to_typst(bold_text)
    processed_text += bold_text
    processed_text += R"*"
    return processed_text, unprocessed_text


def split_italics(text: str) -> Tuple[str, str]:
    processed_text = R"_"
    italic_text, unprocessed_text = re.match(r"(.*?)\*(.*)", text).groups()

    italic_text = string_to_typst(italic_text)
    processed_text += italic_text
    processed_text += R"_"
    return processed_text, unprocessed_text


@pydantic.validate_call
def split_link(text: str) -> Tuple[str, str]:
    return (
        split_markdown_link(text)
        or split_document_link(text)
        or split_paragraph_link(text)
        or (R"\[", text)
    )


@pydantic.validate_call
def split_markdown_link(text: str) -> Optional[Tuple[str, str]]:
    m = re.match(r"(.*?)]\((.*?)\)(.*)", text)
    if not m:
        return None
    disp_text, link, unprocessed_text = m.groups()
    disp_text = sanitize_special_characters(disp_text)
    processed_text = f"\\href{{{link}}}{{{disp_text}}}"
    return processed_text, unprocessed_text


@pydantic.validate_call
def split_document_link(text: str) -> Optional[Tuple[str, str]]:
    m = re.match(r"\[(.+?)]](.*)", text)
    if not m:
        return None
    link_text, unprocessed_text = m.groups()

    m = re.match(r"([a-zA-Z0-9-_\s]+)\|?(.+?)?", link_text)
    if not m:
        return None
    doc_name, disp_text = m.groups()

    doc_ref = file_ref_label(obsidian_path.find_file(doc_name + ".md"))
    referenced_docs.add(doc_ref)
    disp_text = (
        sanitize_special_characters(disp_text) if disp_text else doc_name
    )
    processed_text = f"#link(<{doc_ref}>)[{disp_text}]"
    return processed_text, unprocessed_text


@pydantic.validate_call
def split_paragraph_link(text: str) -> Optional[Tuple[str, str]]:
    m = re.match(r"\[#\^([a-zA-Z0-9-]+)\|?(.+)]](.*)", text)
    if not m:
        return None
    link, disp_text, unprocessed_text = m.groups()
    disp_text = sanitize_special_characters(disp_text)
    processed_text = f"#link(<{link}>)[{disp_text}]"
    return processed_text, unprocessed_text


@pydantic.validate_call
def split_reference(text: str) -> Tuple[str, str]:
    m = re.match(r"([a-zA-Z0-9-]+)$", text)
    if not m:
        return R"^", text
    ref_text = m.groups()[0]
    return f"<{ref_text}>", ""


@pydantic.validate_call
def split_escaped_text(text: str) -> Tuple[str, str]:
    escaped_text = "\\" + text[0]
    unprocessed_text = text[1:]
    return escaped_text, unprocessed_text


@pydantic.validate_call
def split_embedded_doc(text: str) -> tuple((str, str)):
    if is_image(text):
        image_splitter = EMBEDDED_IMAGE_REGEX + r"(.*)"
        m = re.match(image_splitter, text)
        unprocessed_text = m.groups()[-1]
        return embed_image(text), unprocessed_text
    return "!", ""


@pydantic.validate_call
def file_label(file_path: Path) -> str:
    return f"<{file_ref_label(file_path)}>"


@pydantic.validate_call
def file_ref_label(file_path: Path) -> str:
    return "file_" + file_path.name.lower().replace(".", "_").replace(" ", "_")
