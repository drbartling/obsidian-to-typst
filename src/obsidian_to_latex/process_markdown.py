import logging
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import pydantic
from pydantic.dataclasses import dataclass

from obsidian_to_latex import obsidian_path


@dataclass
class Indent:
    list_type: str
    depth: str


@dataclass
class State:
    depth: int
    code_block: Optional[int]
    code_buffer: str
    mermaid_block: Optional[int]
    list_depth: List[Indent]
    file: List[Path]
    temp_dir: Optional[Path]

    @classmethod
    def new(cls):
        return cls(
            depth=1,
            code_block=None,
            code_buffer="",
            mermaid_block=None,
            list_depth=[],
            file=[],
            temp_dir=None,
        )


STATE: State = State.new()


@pydantic.validate_arguments
def obsidian_to_tex(input_text: str) -> str:
    lines = input_text.splitlines()
    lines = [_line_to_tex(i + 1, line) for i, line in enumerate(lines)]
    lines = [line for line in lines if line is not None]
    text = "\n".join(lines)
    text = text + cleanup()
    return text


@pydantic.validate_arguments
def _line_to_tex(
    lineno: int,
    line: str,
) -> str:
    try:
        return line_to_tex(lineno, line)
    except Exception:  # pragma: no cover
        logging.getLogger(__name__).error(
            "Failed to parse `%s:%s`", STATE.file[-1], lineno
        )
        raise


@pydantic.validate_arguments
def line_to_tex(
    lineno: int,
    line: str,
) -> Optional[str]:
    # pylint: disable=too-many-return-statements
    if is_end_of_list(line):
        lines = end_lists()
        lines.append(line_to_tex(lineno, line))
        line = "\n".join(lines)
        return line

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
    if is_numbered_list_item(line):
        return numbered_list_item(line)
    if is_bullet_list_item(line):
        return bullet_list_item(line)
    line = string_to_tex(line)
    return line


@pydantic.validate_arguments
def line_to_section(line: str) -> str:
    assert line.startswith("#"), line
    section_lookup = {
        2: "section",
        3: "subsection",
        4: "subsubsection",
        5: "paragraph",
        6: "subparagraph",
    }
    s, line = re.match(r"(#*)\s*(.*)", line).groups()
    STATE.depth = len(s)

    if STATE.depth not in section_lookup:
        return ""
    section_text = section_lookup[STATE.depth]

    line = string_to_tex(line)
    return f"\\{section_text}{{{line}}}"


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
    m = re.match(r"!\[\[(.*)\]\]", line)
    file_name = m.group(1)
    return Path(file_name).suffix == ""


@pydantic.validate_arguments
def embed_markdown(embed_line: str) -> str:
    m = re.match(r"!\[\[(.*)\]\]", embed_line)
    file_name = m.group(1)
    assert is_markdown(embed_line), embed_line

    file_name = file_name + ".md"
    file = obsidian_path.find_file(file_name)

    with open(file, "r", encoding="UTF-8") as f:
        text = f.read()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#"):
            lines[i] = "#" * (STATE.depth - 1) + line
    text = "\n".join(lines)

    STATE.file.append(file)
    current_depth = STATE.depth
    try:
        result = obsidian_to_tex(text)
    finally:
        STATE.file.pop()
        STATE.depth = current_depth

    return file_label(file) + result


@pydantic.validate_arguments
def is_image(line: str) -> bool:
    m = re.match(r"!\[\[([\s_a-zA-Z0-9.]*)(\|)?([0-9x]+)?\]\]", line)
    if not m:
        return False
    file_name = m.group(1)
    return Path(file_name).suffix.lower() in [".png", ".bmp"]


@pydantic.validate_arguments
def embed_image(line: str) -> str:
    assert is_image(line), line
    m = re.match(
        r"!\[\[([\s_a-zA-Z0-9.]*)(?:\|)?([0-9]+)?(?:x)?([0-9]+)?\]\]", line
    )
    if not m:  # pragma: no cover
        raise Exception(line)
    file_name, width, height = m.groups()
    return include_image(obsidian_path.find_file(file_name), width, height)


@pydantic.validate_arguments
def include_image(
    image_path: Path, width: Optional[int], height: Optional[int]
) -> str:
    width_text = R"\columnwidth" if width is None else f"{int(width/2)}pt"
    height_text = (
        R"keepaspectratio" if height is None else f"height={int(height/2)}pt"
    )

    image_path = image_path.with_suffix("")
    image_path = obsidian_path.format_path(image_path)
    return (
        f"\\includegraphics[width={width_text},{height_text}]{{{image_path}}}"
    )


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
                R"\begin{minipage}{\columnwidth}",
                R"\includegraphics[width=\columnwidth,keepaspectratio]"
                f"{{{STATE.file[-1].stem}_{STATE.mermaid_block}}}",
            ]
            return "\n".join(lines)

        STATE.code_block = lineno
        lines = [
            R"",
            R"\begin{minipage}{\columnwidth}",
            R"\begin{minted}[bgcolor=bg]" f"{{{lang}}}",
        ]
        return "\n".join(lines)

    if STATE.code_block:
        STATE.code_block = None
        lines = [
            R"\end{minted}",
            R"\end{minipage}",
        ]
    if STATE.mermaid_block:
        assert STATE.temp_dir, STATE.temp_dir
        process_mermaid_diagram()
        STATE.mermaid_block = None
        lines = [
            R"\end{minipage}",
        ]
    return "\n".join(lines)


@pydantic.validate_arguments
def process_mermaid_diagram():  # pragma: no cover
    mmd_file: Path = (
        STATE.temp_dir / f"{STATE.file[-1].stem}_{STATE.mermaid_block}.mmd"
    )
    img_file = mmd_file.with_suffix(".pdf")
    with open(mmd_file, "w", encoding="UTF-8") as f:
        f.write(STATE.code_buffer)
    cmd = ["mmdc", "-i", mmd_file, "-o", img_file, "--pdfFit"]
    subprocess.run(cmd, shell=True, check=True)


@pydantic.validate_arguments
def sanitize_special_characters(line: str) -> str:
    return re.sub(r"([&$_#%{}])(?!.*`)", r"\\\1", line)


@pydantic.validate_arguments
def is_end_of_list(line: str) -> bool:
    return STATE.list_depth and not is_list(line)


@pydantic.validate_arguments
def is_list(line: str) -> bool:
    return is_numbered_list_item(line) or is_bullet_list_item(line)


@pydantic.validate_arguments
def is_numbered_list_item(line: str) -> bool:
    return re.match(r"\s*[0-9]+\.", line)


@pydantic.validate_arguments
def numbered_list_item(line: str) -> str:
    indent, number, text = re.match(r"(\s*)([0-9])+\.\s+(.*)", line).groups()
    sanitized_text = string_to_tex(text)
    list_line = R"\item " + sanitized_text
    if line_depth(indent) > total_depth():
        new_indent = indent.replace(total_indent(), "", 1)
        STATE.list_depth.append(Indent("legal", new_indent))
        start_num = int(number)
        start_text = "" if start_num == 1 else f"[start={start_num}]"
        lines = [R"\begin{legal}" + start_text, list_line]
        list_line = "\n".join(lines)
    if line_depth(indent) < total_depth():
        indent = STATE.list_depth.pop()
        lines = [f"\\end{{{indent.list_type}}}", list_line]
        list_line = "\n".join(lines)

    assert STATE.list_depth, STATE.list_depth
    return list_line


@pydantic.validate_arguments
def is_bullet_list_item(line: str) -> bool:
    return re.match(r"\s*-", line)


@pydantic.validate_arguments
def bullet_list_item(line: str) -> str:
    indent, text = re.match(r"(\s*)-\s+(.*)", line).groups()
    sanitized_text = string_to_tex(text)
    list_line = R"\item " + sanitized_text
    if line_depth(indent) > total_depth():
        new_indent = indent.replace(total_indent(), "", 1)
        STATE.list_depth.append(Indent("itemize", new_indent))
        lines = [R"\begin{itemize}", list_line]
        list_line = "\n".join(lines)
    if line_depth(indent) < total_depth():
        indent = STATE.list_depth.pop()
        lines = [f"\\end{{{indent.list_type}}}", list_line]
        list_line = "\n".join(lines)

    assert STATE.list_depth, STATE.list_depth
    return list_line


@pydantic.validate_arguments
def line_depth(indent: str) -> int:
    return len(indent)


@pydantic.validate_arguments
def total_depth() -> int:
    if not STATE.list_depth:
        return -1
    return sum(line_depth(i.depth) for i in STATE.list_depth)


@pydantic.validate_arguments
def total_indent() -> str:
    if not STATE.list_depth:
        return ""
    return "".join([i.depth for i in STATE.list_depth])


@pydantic.validate_arguments
def cleanup():
    assert (
        not STATE.code_block
    ), f"Reached end of file without closing code block from line {STATE.code_block}"
    lines = [""]

    lines.extend(end_lists())

    assert not STATE.list_depth, STATE.list_depth
    return "\n".join(lines)


@pydantic.validate_arguments
def end_lists():
    lines = []
    while STATE.list_depth:
        indent = STATE.list_depth.pop()
        lines.append(f"\\end{{{indent.list_type}}}")
    return lines


@pydantic.validate_arguments
def string_to_tex(unprocessed_text: str) -> str:
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
        else:
            processed_text += sanitize_special_characters(char)

    return processed_text


@pydantic.validate_arguments
def split_verbatim(text: str) -> Tuple[str, str]:
    processed_text = R"\verb`"
    verb_text, unprocessed_text = re.match(r"(.*?`)(.*)", text).groups()
    processed_text += verb_text
    return (processed_text, unprocessed_text)


@pydantic.validate_arguments
def split_formatted(text: str) -> Tuple[str, str]:
    if text.startswith("*"):
        return split_bold(text)
    return split_italics(text)


def split_bold(text: str) -> Tuple[str, str]:
    processed_text = R"\textbf{"
    bold_text, unprocessed_text = re.match(
        r"\*(.*?\**)\*\*(.*)", text
    ).groups()

    bold_text = string_to_tex(bold_text)
    processed_text += bold_text
    processed_text += R"}"
    return (processed_text, unprocessed_text)


def split_italics(text: str) -> Tuple[str, str]:
    processed_text = R"\textit{"
    italic_text, unprocessed_text = re.match(r"(.*?)\*(.*)", text).groups()

    italic_text = string_to_tex(italic_text)
    processed_text += italic_text
    processed_text += R"}"
    return (processed_text, unprocessed_text)


@pydantic.validate_arguments
def split_link(text: str) -> Tuple[str, str]:
    return (
        split_markdown_link(text)
        or split_document_link(text)
        or split_paragraph_link(text)
        or (R"\[", text)
    )


@pydantic.validate_arguments
def split_markdown_link(text: str) -> Tuple[str, str]:
    m = re.match(r"(.*?)\]\((.*?)\)(.*)", text)
    if not m:
        return None
    disp_text, link, unprocessed_text = m.groups()
    disp_text = sanitize_special_characters(disp_text)
    processed_text = f"\\href{{{link}}}{{{disp_text}}}"
    return (processed_text, unprocessed_text)


@pydantic.validate_arguments
def split_document_link(text: str) -> Tuple[str, str]:
    m = re.match(r"\[(.+?)\]\](.*)", text)
    if not m:
        return None
    link_text, unprocessed_text = m.groups()

    m = re.match(r"([a-zA-Z0-9-_\s]+)\|?(.+?)?", link_text)
    if not m:
        return None
    doc_name, disp_text = m.groups()

    doc_ref = file_ref_label(obsidian_path.find_file(doc_name + ".md"))
    disp_text = (
        sanitize_special_characters(disp_text) if disp_text else doc_name
    )
    processed_text = f"\\hyperref[{doc_ref}]{{{disp_text}}}"
    return (processed_text, unprocessed_text)


@pydantic.validate_arguments
def split_paragraph_link(text: str) -> Tuple[str, str]:
    m = re.match(r"\[#\^([a-zA-Z0-9-]+)\|?(.+)\]\](.*)", text)
    if not m:
        return None
    link, disp_text, unprocessed_text = m.groups()
    disp_text = sanitize_special_characters(disp_text)
    processed_text = f"\\hyperref[{link}]{{{disp_text}}}"
    return (processed_text, unprocessed_text)


@pydantic.validate_arguments
def split_reference(text: str) -> Tuple[str, str]:
    m = re.match(r"([a-zA-Z0-9-]+)$", text)
    if not m:
        return R"\textasciicircum{}", text
    ref_text = m.groups()[0]
    return f"\\label{{{ref_text}}}", ""


@pydantic.validate_arguments
def file_label(file_path: Path) -> str:
    return f"\\label{{{file_ref_label(file_path)}}}"


@pydantic.validate_arguments
def file_ref_label(file_path: Path) -> str:
    return "file_" + file_path.name.replace(".", "_")
