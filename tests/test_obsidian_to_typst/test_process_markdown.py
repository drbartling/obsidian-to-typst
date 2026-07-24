import inspect
import re
from pathlib import Path
from unittest import mock

import devtools
import pypdf
import pytest

from obsidian_to_typst import obsidian_path, process_markdown


def make_pdf(path: Path, page_count: int) -> None:
    writer = pypdf.PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as f:
        writer.write(f)


def file_line() -> str:
    return f"{__file__}:{inspect.currentframe().f_back.f_lineno}"


@pytest.fixture(autouse=True)
def setup_teardown() -> None:
    process_markdown.STATE = process_markdown.State.new()
    test_file = Path.cwd() / "temp/test_file.md"
    process_markdown.STATE.file.append(test_file)
    temp_dir = test_file.parent / "temp"
    process_markdown.STATE.temp_dir = temp_dir
    obsidian_path.VAULT_ROOT = Path.cwd()
    yield
    process_markdown.STATE = process_markdown.State.new()
    obsidian_path.VAULT_ROOT = None


obsidian_to_tex_params = [
    (
        f"{file_line()} Empty File",
        ("\n"),
        ("\n"),
    ),
    (
        f"{file_line()} Document Title",
        ("# My Document\n"),
        ("My Document\n\n\n"),
    ),
    (
        f"{file_line()} Hello world",
        ("Hello, World!\n"),
        ("Hello, World!\n"),
    ),
]


@pytest.mark.parametrize(
    ("test_name", "input_text", "expected"), obsidian_to_tex_params
)
def test_obsidian_to_tex(
    test_name: str, input_text: str, expected: str
) -> None:
    with mock.patch(
        "obsidian_to_typst.process_markdown.process_mermaid_diagram"
    ):
        result = process_markdown.obsidian_to_typst(input_text)

    devtools.debug(test_name)
    devtools.debug(result)
    devtools.debug(expected)
    assert result == expected, result


split_embedded_doc_params = [
    (
        "![[foo.jpg]]",
        (
            '#image("/foo.jpg",width:80%,)',
            "",
        ),
    ),
    (
        "![[foo.jpg]] and more text",
        (
            '#image("/foo.jpg",width:80%,)',
            " and more text",
        ),
    ),
]


@pytest.mark.parametrize(("input_text", "expected"), split_embedded_doc_params)
def test_split_embedded_doc(input_text: str, expected: tuple) -> None:
    file_name = re.match(r"!\[\[(.*?)]]", input_text).group(1)
    with mock.patch(
        "obsidian_to_typst.process_markdown.obsidian_path.find_file"
    ) as p:
        p.return_value = Path(obsidian_path.VAULT_ROOT / file_name)
        result = process_markdown.split_embedded_doc(input_text)
    assert expected == result


is_image_params = [
    ("![[foo.jpg]]", True),
    ("![[foo.png]]", True),
    ("![[foo.bmp]]", True),
    ("![[foo.svg]]", True),
    ("![[foo.pdf]]", True),
    ("![[foo.md]]", False),
    ("![[TASER_10_T19C36177_Log_2026-03-10_1453.pdf]]", True),
]


@pytest.mark.parametrize(("input_text", "expected"), is_image_params)
def test_is_image(input_text: str, expected: bool) -> None:
    assert process_markdown.is_image(input_text) == expected


def test_wikilink_then_markdown_link_on_same_line() -> None:
    input_text = (
        "The [[HVC]] command and response size "
        "([HVC_CMD_SIZE](https://example.com/hvc_commands.h#L19)) "
        "is limited to 23 bytes."
    )
    expected = (
        "The #link(<file_hvc_md>)[HVC] command and response size "
        "(\\href{https://example.com/hvc_commands.h#L19}{HVC_CMD_SIZE}) "
        "is limited to 23 bytes."
    )
    with mock.patch(
        "obsidian_to_typst.process_markdown.obsidian_path.find_file"
    ) as p:
        p.return_value = Path(obsidian_path.VAULT_ROOT / "HVC.md")
        result = process_markdown.string_to_typst(input_text)
    assert result == expected


def test_heading_name_link_resolves_to_heading_label() -> None:
    input_text = (
        "### Design Comparison\n"
        "\n"
        "Some comparison text.\n"
        "\n"
        "See [[#Design Comparison]] below for more.\n"
    )
    result = process_markdown.obsidian_to_typst(input_text)
    assert (
        "#heading(level:2)[Design Comparison] <heading-design-comparison>"
        in result
    )
    assert "#link(<heading-design-comparison>)[Design Comparison]" in result


def test_embed_markdown_attaches_label_to_first_heading(tmp_path: Path) -> None:
    embedded_file = tmp_path / "FIFO.md"
    embedded_file.write_text("## FIFO\n\nSome content.\n", encoding="UTF-8")
    process_markdown.STATE.heading_depth = 4

    with mock.patch(
        "obsidian_to_typst.process_markdown.obsidian_path.find_file"
    ) as p:
        p.return_value = embedded_file
        result = process_markdown.embed_markdown("![[FIFO]]")

    assert "#heading(level:4)[FIFO] <file_fifo_md>" in result
    assert "<heading-fifo>" not in result
    assert not result.startswith("<file_fifo_md>")


def test_embed_markdown_falls_back_to_leading_label_without_heading(
    tmp_path: Path,
) -> None:
    embedded_file = tmp_path / "Widgeting.md"
    embedded_file.write_text(
        "Some content with no heading.\n", encoding="UTF-8"
    )

    with mock.patch(
        "obsidian_to_typst.process_markdown.obsidian_path.find_file"
    ) as p:
        p.return_value = embedded_file
        result = process_markdown.embed_markdown("![[Widgeting]]")

    assert result.startswith("<file_widgeting_md>")


def test_include_image_embeds_all_pdf_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    make_pdf(pdf_path, 3)

    with mock.patch(
        "obsidian_to_typst.process_markdown.obsidian_path.root_path"
    ) as p:
        p.return_value = "/report.pdf"
        result = process_markdown.include_image(pdf_path, None, None)

    assert result == (
        '#image("/report.pdf",width:80%,page:1)\n'
        "#pagebreak()\n"
        '#image("/report.pdf",width:80%,page:2)\n'
        "#pagebreak()\n"
        '#image("/report.pdf",width:80%,page:3)'
    )


def test_include_image_single_page_pdf_has_no_pagebreak(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "single.pdf"
    make_pdf(pdf_path, 1)

    with mock.patch(
        "obsidian_to_typst.process_markdown.obsidian_path.root_path"
    ) as p:
        p.return_value = "/single.pdf"
        result = process_markdown.include_image(pdf_path, None, None)

    assert result == '#image("/single.pdf",width:80%,page:1)'


def test_pdf_page_count(tmp_path: Path) -> None:
    pdf_path = tmp_path / "multi.pdf"
    expected_page_count = 5
    make_pdf(pdf_path, expected_page_count)

    assert process_markdown.pdf_page_count(pdf_path) == expected_page_count
