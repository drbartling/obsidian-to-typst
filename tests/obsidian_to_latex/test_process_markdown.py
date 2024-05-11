import inspect
from pathlib import Path
from unittest import mock

import devtools
import pytest

from obsidian_to_typst import process_markdown


def file_line() -> str:
    return f"{__file__}:{inspect.currentframe().f_back.f_lineno}"


@pytest.fixture(autouse=True)
def setup_teardown():
    process_markdown.STATE = process_markdown.State.new()
    test_file = Path.cwd() / "temp/test_file.md"
    process_markdown.STATE.file.append(test_file)
    temp_dir = test_file.parent / "temp"
    process_markdown.STATE.temp_dir = temp_dir
    yield
    process_markdown.STATE = process_markdown.State.new()


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
]


@pytest.mark.parametrize(
    "test_name, input_text, expected", obsidian_to_tex_params
)
def test_obsidian_to_tex(test_name, input_text, expected):
    with mock.patch(
        "obsidian_to_typst.process_markdown.process_mermaid_diagram"
    ):
        result = process_markdown.obsidian_to_typst(input_text)

    devtools.debug(test_name)
    devtools.debug(result)
    devtools.debug(expected)
    assert result == expected, result
