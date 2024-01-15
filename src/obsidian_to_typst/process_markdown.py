import logging
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


@dataclass
class Indent:
    list_type: str
    depth: str


@dataclass
class State:
    heading_depth: int
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
            code_block=None,
            code_buffer="",
            mermaid_block=None,
            file=[],
            temp_dir=None,
            typst_block=None,
        )

    def init(self, temp_dir: Path, file: Path):
        self.heading_depth = 0
        self.code_block = None
        self.code_buffer = ""
        self.mermaid_block = None
        self.file = [file]
        self.temp_dir = temp_dir
        self.typst_block = None


STATE: State = State.new()


@pydantic.validate_arguments
def init_state(temp_dir: Path, file: Path) -> None:
    STATE.init(temp_dir, file)


@pydantic.validate_arguments
def obsidian_to_typst(input_text: str) -> str:
    lines = input_text.splitlines()
    lines = [_line_to_typst(i + 1, line) for i, line in enumerate(lines)]
    lines = [line for line in lines if line is not None]
    lines.append("")
    text = "\n".join(lines)
    text = text + cleanup()
    return text


@pydantic.validate_arguments
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


@pydantic.validate_arguments
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


@pydantic.validate_arguments
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
    STATE.heading_depth = len(s)

    if STATE.heading_depth not in section_lookup:
        return line + "\n\n"

    line = string_to_typst(line)
    section_text = f"#heading(level:{STATE.heading_depth - 1})[{line}]"

    return section_text


@pydantic.validate_arguments
def is_embedded(line: str) -> bool:
    return line.startswith("![[") and line.endswith("]]")


@pydantic.validate_arguments
def embed_file(line: str) -> str:
    if is_markdown(line):
        return embed_markdown(line)
    if is_image(line):
        return embed_image(line)
    raise Exception(f"Unable to embed {line}")  # pragma: no cover


@pydantic.validate_arguments
def is_markdown(line: str) -> bool:
    m = re.match(r"!\[\[(.*)]]", line)
    file_name = m.group(1)
    return Path(file_name).suffix == ""


@pydantic.validate_arguments
def embed_markdown(embed_line: str) -> str:
    m = re.match(r"!\[\[(.*)]]", embed_line)
    file_name = m.group(1)
    assert is_markdown(embed_line), embed_line

    file_name = file_name + ".md"
    file = obsidian_path.find_file(file_name)

    with open(file, "r", encoding="UTF-8") as f:
        text = f.read()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#"):
            lines[i] = "#" * (STATE.heading_depth - 1) + line
    text = "\n".join(lines)

    STATE.file.append(file)
    current_depth = STATE.heading_depth
    try:
        result = obsidian_to_typst(text)
    finally:
        STATE.file.pop()
        STATE.heading_depth = current_depth

    ref_label = file_ref_label(file)
    docs_embedded.add(ref_label)
    return file_label(file) + result


@pydantic.validate_arguments
def is_image(line: str) -> bool:
    m = re.match(r"!\[\[([\s_a-zA-Z0-9.]*)(\|)?([0-9x]+)?]]", line)
    if not m:
        return False
    file_name = m.group(1)
    return Path(file_name).suffix.lower() in [".png", ".bmp", ".svg"]


@pydantic.validate_arguments
def embed_image(line: str) -> str:
    assert is_image(line), line
    m = re.match(r"!\[\[([\s_a-zA-Z0-9.]*)\|?([0-9]+)?x?([0-9]+)?]]", line)
    if not m:  # pragma: no cover
        raise Exception(line)
    file_name, width, height = m.groups()
    return include_image(obsidian_path.find_file(file_name), width, height)


@pydantic.validate_arguments
def include_image(
    image_path: Path, width: Optional[int], height: Optional[int]
) -> str:
    width_text = R"80%" if width is None else f"{int(width/2)}pt"
    height_text = "" if height is None else f"height:{int(height/2)}pt,"

    image_path = obsidian_path.rel_path(image_path)
    return f'#image("{image_path}",width:{width_text},{height_text})'


@pydantic.validate_arguments
def is_code_block_toggle(line: str) -> bool:
    return re.match(r"\s*```", line) is not None


@pydantic.validate_arguments
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
                f'"{STATE.file[-1].stem}_{STATE.mermaid_block}.svg",',
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


@pydantic.validate_arguments
def process_mermaid_diagram():  # pragma: no cover
    assert STATE.temp_dir, STATE.temp_dir
    assert STATE.mermaid_block, STATE.mermaid_block
    assert STATE.file, STATE.file
    mmd_file: Path = (
        STATE.temp_dir / f"{STATE.file[-1].stem}_{STATE.mermaid_block}.mmd"
    )
    pdf_file = mmd_file.with_suffix(".pdf")
    img_file = mmd_file.with_suffix(".svg")
    with open(mmd_file, "w", encoding="UTF-8") as f:
        f.write(STATE.code_buffer)
    cmd = [
        "mmdc",
        "--input",
        mmd_file,
        "--output",
        pdf_file,
        "--pdfFit",
    ]
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        _logger.error(
            "Failed to generate MMD diagram for `%s` with command `%s`.",
            STATE.file[-1],
            " ".join(
                [f'"{c}"' if isinstance(c, Path) else str(c) for c in cmd]
            ),
        )
        raise
    cmd = [
        "mutool",
        "draw",
        "-o",
        img_file,
        pdf_file,
    ]
    _logger.info(
        "Calling `%s`",
        " ".join([f'"{c}"' if isinstance(c, Path) else str(c) for c in cmd]),
    )
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        _logger.error(
            "Failed to generate svg file from pdf with command `%s`",
            " ".join([str(c) for c in cmd]),
        )
        raise
    temp_img_file = img_file.with_name(img_file.stem + "1" + ".svg")
    temp_img_file.replace(img_file)


@pydantic.validate_arguments
def sanitize_special_characters(line: str) -> str:
    return re.sub(r"([&$#%{}])(?!.*`)", r"\\\1", line)


@pydantic.validate_arguments
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


@pydantic.validate_arguments
def string_to_typst(unprocessed_text: str) -> str:
    logging.getLogger(__name__).debug("unprocessed_text %s", unprocessed_text)
    processed_text = ""

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
        else:
            processed_text += sanitize_special_characters(char)

    return processed_text


@pydantic.validate_arguments
def split_verbatim(text: str) -> Tuple[str, str]:
    processed_text = R"`"
    verb_text, unprocessed_text = re.match(r"(.*?`)(.*)", text).groups()
    processed_text += verb_text
    return processed_text, unprocessed_text


@pydantic.validate_arguments
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


@pydantic.validate_arguments
def split_link(text: str) -> Tuple[str, str]:
    return (
        split_markdown_link(text)
        or split_document_link(text)
        or split_paragraph_link(text)
        or (R"\[", text)
    )


@pydantic.validate_arguments
def split_markdown_link(text: str) -> Optional[Tuple[str, str]]:
    m = re.match(r"(.*?)]\((.*?)\)(.*)", text)
    if not m:
        return None
    disp_text, link, unprocessed_text = m.groups()
    disp_text = sanitize_special_characters(disp_text)
    processed_text = f"\\href{{{link}}}{{{disp_text}}}"
    return processed_text, unprocessed_text


@pydantic.validate_arguments
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


@pydantic.validate_arguments
def split_paragraph_link(text: str) -> Optional[Tuple[str, str]]:
    m = re.match(r"\[#\^([a-zA-Z0-9-]+)\|?(.+)]](.*)", text)
    if not m:
        return None
    link, disp_text, unprocessed_text = m.groups()
    disp_text = sanitize_special_characters(disp_text)
    processed_text = f"#link(<{link}>)[{disp_text}]"
    return processed_text, unprocessed_text


@pydantic.validate_arguments
def split_reference(text: str) -> Tuple[str, str]:
    m = re.match(r"([a-zA-Z0-9-]+)$", text)
    if not m:
        return R"^", text
    ref_text = m.groups()[0]
    return f"<{ref_text}>", ""


@pydantic.validate_arguments
def split_escaped_text(text: str) -> Tuple[str, str]:
    escaped_text = "\\" + text[0]
    unprocessed_text = text[1:]
    return escaped_text, unprocessed_text


@pydantic.validate_arguments
def file_label(file_path: Path) -> str:
    return f"<{file_ref_label(file_path)}>"


@pydantic.validate_arguments
def file_ref_label(file_path: Path) -> str:
    return "file_" + file_path.name.lower().replace(".", "_").replace(" ", "_")
