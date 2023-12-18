# pylint: disable=protected-access
import inspect
from pathlib import Path
from unittest import mock

import devtools
import pydantic
import pytest

from obsidian_to_latex import obsidian_path, process_markdown


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
        f"{file_line()} Sections: Use highest section for document title",
        (
            "# User Guide\n"
            "This is a summary of the user guide.\n"
            "## Getting Started\n"
            "Start by installing.  Then run the program."
        ),
        (
            "\n"
            "This is a summary of the user guide.\n"
            R"\section{Getting Started}"
            "\n"
            "Start by installing.  Then run the program."
        ),
    ),
    (
        f"{file_line()} Code Block: Use minted to stylize code blocks",
        (
            "# User Guide\n"
            "Here's how to add a section header:\n"
            "```markdown\n"
            "## A Section Header\n"
            "```\n"
            "That looks like this:\n"
            "## A Section Header\n"
        ),
        (
            "\n"
            "Here's how to add a section header:\n\n"
            R"\begin{minipage}{\columnwidth}"
            "\n"
            R"\begin{minted}[bgcolor=bg]{markdown}"
            "\n"
            R"## A Section Header"
            "\n"
            R"\end{minted}"
            "\n"
            R"\end{minipage}"
            "\n"
            "That looks like this:\n"
            R"\section{A Section Header}"
        ),
    ),
    (
        f"{file_line()} Code Block: Obsidian accepts leading spaces before the back ticks",
        (
            "# User Guide\n"
            "Here's how to add a section header:\n"
            "```markdown\n"
            "## A Section Header\n"
            " ```\n"
            "That looks like this:\n"
            "## A Section Header\n"
        ),
        (
            "\n"
            "Here's how to add a section header:\n\n"
            R"\begin{minipage}{\columnwidth}"
            "\n"
            R"\begin{minted}[bgcolor=bg]{markdown}"
            "\n"
            R"## A Section Header"
            "\n"
            R"\end{minted}"
            "\n"
            R"\end{minipage}"
            "\n"
            "That looks like this:\n"
            R"\section{A Section Header}"
        ),
    ),
    (
        f"{file_line()} Code Block: Mermaid code blocks are replaced by images",
        (
            "# User Guide\n"
            "We can use mermaid to create nice graphics:\n"
            "```mermaid\n"
            "Graph LR\n"
            "    left --> right\n"
            "```\n"
            "That looks like this:\n"
            "## A Section Header\n"
        ),
        (
            "\n"
            "We can use mermaid to create nice graphics:\n\n"
            R"\begin{minipage}{\columnwidth}"
            "\n"
            R"\includegraphics[width=\columnwidth,keepaspectratio]"
            R"{test_file_3}"
            "\n"
            R"\end{minipage}"
            "\n"
            "That looks like this:\n"
            R"\section{A Section Header}"
        ),
    ),
    (
        f"{file_line()} List: Begin and end numbered lists with `legal`",
        ("1. Here's a list\n2. With a second item\n"),
        (
            R"\begin{legal}"
            "\n"
            R"\item Here's a list"
            "\n"
            R"\item With a second item"
            "\n"
            R"\end{legal}"
        ),
    ),
    (
        f"{file_line()} List: Begin and end bullet lists with `itemize`",
        ("- Here's a list\n- With a second item\n"),
        (
            R"\begin{itemize}"
            "\n"
            R"\item Here's a list"
            "\n"
            R"\item With a second item"
            "\n"
            R"\end{itemize}"
        ),
    ),
    (
        f"{file_line()} List: Terminate list after last element in list",
        (
            "We're about to have a list:\n"
            "- Here's a list\n"
            "- With a second item\n"
            "See list above.\n"
        ),
        (
            "We're about to have a list:\n"
            R"\begin{itemize}"
            "\n"
            R"\item Here's a list"
            "\n"
            R"\item With a second item"
            "\n"
            R"\end{itemize}"
            "\n"
            "See list above."
        ),
    ),
    (
        f"{file_line()} List: Prefix underscores with \\ in lists",
        ("We're about to have a list:\n- Here's a list with_underscores\n"),
        (
            "We're about to have a list:\n"
            R"\begin{itemize}"
            "\n"
            R"\item Here's a list with\_underscores"
            "\n"
            R"\end{itemize}"
        ),
    ),
    (
        f"{file_line()} List: Prefix underscores with \\ in numbered lists",
        (
            "We're about to have a list:\n"
            "1. Here's a list with_underscores\n"
        ),
        (
            "We're about to have a list:\n"
            R"\begin{legal}"
            "\n"
            R"\item Here's a list with\_underscores"
            "\n"
            R"\end{legal}"
        ),
    ),
    (
        f"{file_line()} List: Prefix underscores with \\ in lists beyond the first item",
        (
            "1. Install the provided license file anywhere on your system\n"
            "2. Set DECATECH_LICENSE_FILE to the location of your license file\n"
        ),
        (
            R"\begin{legal}"
            "\n"
            R"\item Install the provided license file anywhere on your system"
            "\n"
            R"\item Set DECATECH\_LICENSE\_FILE to the location of your license file"
            "\n"
            R"\end{legal}"
        ),
    ),
    (
        f"{file_line()} List: Numbered lists can start with a number other than 1",
        ("2. This list startswith 2\n3. And ends with 3\n"),
        (
            R"\begin{legal}[start=2]"
            "\n"
            R"\item This list startswith 2"
            "\n"
            R"\item And ends with 3"
            "\n"
            R"\end{legal}"
        ),
    ),
    (
        f"{file_line()} List: Lists can go multiple levels deep",
        ("- This list has depth\n  - So deep\n"),
        (
            R"\begin{itemize}"
            "\n"
            R"\item This list has depth"
            "\n"
            R"\begin{itemize}"
            "\n"
            R"\item So deep"
            "\n"
            R"\end{itemize}"
            "\n"
            R"\end{itemize}"
        ),
    ),
    (
        f"{file_line()} List: Denest a list one level",
        ("- This list has depth\n  - So deep\n- And Shallow again"),
        (
            R"\begin{itemize}"
            "\n"
            R"\item This list has depth"
            "\n"
            R"\begin{itemize}"
            "\n"
            R"\item So deep"
            "\n"
            R"\end{itemize}"
            "\n"
            R"\item And Shallow again"
            "\n"
            R"\end{itemize}"
        ),
    ),
    (
        f"{file_line()} List: Denest a numbered list one level",
        (
            "1. This numbered list has depth\n  1. So deep\n2. And Shallow again"
        ),
        (
            "\\begin{legal}\n"
            "\\item This numbered list has depth\n"
            "\\begin{legal}\n"
            "\\item So deep\n"
            "\\end{legal}\n"
            "\\item And Shallow again\n"
            "\\end{legal}"
        ),
    ),
    (
        f"{file_line()} List: Nesting multiple list levels sets the indent correctly",
        (
            "- Start List\n"
            "\t- Go Deeper\n"
            "- And back down\n"
            "\t- Go deeper again\n"
            "\t\t- 2. levels deep\n"
            "\t\t\t- 3. levels deep\n"
            "\t\t- back out\n"
            "\t\t\t- 3 deep again\n"
        ),
        (
            "\\begin{itemize}\n"
            "\\item Start List\n"
            "\\begin{itemize}\n"
            "\\item Go Deeper\n"
            "\\end{itemize}\n"
            "\\item And back down\n"
            "\\begin{itemize}\n"
            "\\item Go deeper again\n"
            "\\begin{itemize}\n"
            "\\item 2. levels deep\n"
            "\\begin{itemize}\n"
            "\\item 3. levels deep\n"
            "\\end{itemize}\n"
            "\\item back out\n"
            "\\begin{itemize}\n"
            "\\item 3 deep again\n"
            "\\end{itemize}\n"
            "\\end{itemize}\n"
            "\\end{itemize}\n"
            "\\end{itemize}"
        ),
    ),
    (
        f"{file_line()} Link: Convert Markdown link to hyperref",
        (
            "You can find the reference you need [here](https://www.google.com/).\n"
        ),
        (
            R"You can find the reference you need \href{https://www.google.com/}{here}."
        ),
    ),
    (
        f"{file_line()} Link: Convert multiple markdown links to hyperref in one line",
        (
            "You can find the reference you need [here](https://www.google.com/) "
            "and [there](https://duckduckgo.com/).\n"
        ),
        (
            R"You can find the reference you need \href{https://www.google.com/}{here} "
            R"and \href{https://duckduckgo.com/}{there}."
        ),
    ),
    (
        f"{file_line()} Inline Code: Do not escape text in inline code snippets",
        "You can run `obsidian_to_latex README.md` to try this out.",
        R"You can run \verb`obsidian_to_latex README.md` to try this out.",
    ),
    (
        f"{file_line()} Formatting: Bold Text",
        "You can make **bold** text **with_underscores**!",
        R"You can make \textbf{bold} text \textbf{with\_underscores}!",
    ),
    (
        f"{file_line()} Formatting: Italic Text",
        "You can make *italic* text *with_underscores*!",
        R"You can make \textit{italic} text \textit{with\_underscores}!",
    ),
    (
        f"{file_line()} Formatting: Bold italic Text",
        "You can make ***bold and italic*** text ***with_underscores***!",
        R"You can make \textbf{\textit{bold and italic}} text \textbf{\textit{with\_underscores}}!",
    ),
]


@pytest.mark.parametrize(
    "test_name, input_text, expected", obsidian_to_tex_params
)
def test_obsidian_to_tex(test_name, input_text, expected):
    with mock.patch(
        "obsidian_to_latex.process_markdown.process_mermaid_diagram"
    ):
        result = process_markdown.obsidian_to_tex(input_text)

    devtools.debug(test_name)
    devtools.debug(result)
    devtools.debug(expected)
    assert result == expected, result


line_to_latex_params = [
    ("A Normal Line", "A Normal Line"),
    ("# A Title", R""),  # Title at top of markdown becomes document title
    ("## A section Header", R"\section{A section Header}"),
    (
        "### A sub section Header",
        R"\subsection{A sub section Header}",
    ),
    (
        "#### A sub sub section",
        R"\subsubsection{A sub sub section}",
    ),
    (
        "##### A 'paragraph'",
        R"\paragraph{A 'paragraph'}",
    ),
    (
        "###### A 'sub paragraph'",
        R"\subparagraph{A 'sub paragraph'}",
    ),
    (
        "## This section is #1",
        R"\section{This section is \#1}",
    ),
    (
        "Normal text is almost #1, it's #2",
        R"Normal text is almost \#1, it's \#2",
    ),
    (
        "Normal text is almost #1, it's #2",
        R"Normal text is almost \#1, it's \#2",
    ),
]


@pytest.mark.parametrize("input_text, expected", line_to_latex_params)
def test_line_to_tex(input_text, expected):
    result = process_markdown.line_to_tex(0, input_text)
    assert result == expected


is_embedded_params = [
    ("Hello", False),
    ("![[Hello]]", True),
    ("![[Hello]", False),
]


@pytest.mark.parametrize("markdown_line, expected", is_embedded_params)
def test_is_embedded(markdown_line, expected):
    result = process_markdown.is_embedded(markdown_line)
    assert result == expected


is_image_params = [
    ("", False),
    ("![[Hello]]", False),
    ("![[Hello.png]]", True),
    ("![[Hello.png|123]]", True),
    ("![[Hello.png|123x234]]", True),
    ("![[Hello.png|123X234]]", False),
]


@pytest.mark.parametrize("input_text, expected", is_image_params)
def test_is_image(input_text, expected):
    result = process_markdown.is_image(input_text)
    assert result == expected


embed_markdown_params = [
    (
        f"{file_line()} Embedding the top file removes the title",
        "![[Hello]]",
        ["# Hello\nlorem ipsum\n"],
        "\\label{file_embedded_document_md}\nlorem ipsum",
    ),
    (
        f"{file_line()} Remove the title level header from all embedded docs",
        "![[Hello]]",
        [
            "# Hello\nlorem ipsum\n![[World]]\n",
            "# World\ndolor sit\n",
        ],
        "\\label{file_embedded_document_md}\n"
        "lorem ipsum\n"
        "\\label{file_embedded_document_md}\n"
        "dolor sit",
    ),
    (
        f"{file_line()} First level header match header from higher doc",
        "![[Hello]]",
        [
            "## Hello\nlorem ipsum\n![[World]]\n",
            "# World\ndolor sit\n",
        ],
        "\\label{file_embedded_document_md}\\section{Hello}\n"
        "lorem ipsum\n"
        "\\label{file_embedded_document_md}\\section{World}\n"
        "dolor sit",
    ),
    (
        f"{file_line()} First level header match header from higher doc",
        "![[Hello]]",
        [
            "# Hello\n### lorem ipsum\n![[World]]\n",
            "# World\ndolor sit\n",
        ],
        "\\label{file_embedded_document_md}\n"
        "\\subsection{lorem ipsum}\n"
        "\\label{file_embedded_document_md}\\subsection{World}\n"
        "dolor sit",
    ),
    (
        f"{file_line()} Second level header goes only one header level down from higher doc",
        "![[Hello]]",
        [
            "# Hello\n## lorem ipsum\n![[World]]\n![[Bob]]",
            "## World\ndolor sit\n",
            "## Bob\ndolor sit\n",
        ],
        "\\label{file_embedded_document_md}\n"
        "\\section{lorem ipsum}\n"
        "\\label{file_embedded_document_md}\\subsection{World}\n"
        "dolor sit\n"
        "\\label{file_embedded_document_md}\\subsection{Bob}\n"
        "dolor sit",
    ),
    (
        f"{file_line()} Second level header goes one header level down",
        "![[Hello]]",
        [
            "# Hello\n## lorem ipsum\n![[World]]\n",
            "## World\ndolor sit\n",
        ],
        "\\label{file_embedded_document_md}\n"
        "\\section{lorem ipsum}\n"
        "\\label{file_embedded_document_md}\\subsection{World}\n"
        "dolor sit",
    ),
    (
        f"{file_line()} Embedding images",
        "![[Hello]]",
        [
            "## Hello\nlorem ipsum\n![[World.bmp]]\n",
        ],
        "\\label{file_embedded_document_md}\\section{Hello}\n"
        "lorem ipsum\n"
        R"\includegraphics[width=\columnwidth,keepaspectratio]"
        f"{{{obsidian_path.format_path(Path('embedded_document').absolute())}}}",
    ),
    (
        f"{file_line()} Reference an embedded file",
        "![[Hello]]",
        [
            "lorem ipsum[[embedded_document]]\n",
            "dolar set",
        ],
        "\\label{file_embedded_document_md}lorem ipsum\\hyperref[file_embedded_document_md]{embedded_document}",
    ),
    (
        f"{file_line()} Reference an embedded file again",
        "![[Hello]]",
        [
            "lorem ipsum [[embedded_document]] [[embedded_document]]\n",
            "dolar set",
        ],
        "\\label{file_embedded_document_md}lorem ipsum \\hyperref[file_embedded_document_md]{embedded_document} \\hyperref[file_embedded_document_md]{embedded_document}",
    ),
]


@pytest.mark.parametrize(
    "test_name, input_text, open_reads, expected", embed_markdown_params
)
def test_embed_markdown(test_name, input_text, open_reads, expected):
    with mock.patch("obsidian_to_latex.obsidian_path.find_file") as mock_find:
        mock_find.return_value = Path("embedded_document.md").absolute()
        with mock.patch(
            "builtins.open", get_mock_open(open_reads)
        ) as _open_mock:
            result = process_markdown.embed_markdown(input_text)
    devtools.debug(test_name)
    devtools.debug(result)
    devtools.debug(expected)

    assert result == expected


@pydantic.validate_arguments
def get_mock_open(file_contents: list[str]):
    reads = 0

    def open_mock(*_args, **_kwargs):
        nonlocal reads
        content = file_contents[reads]
        reads += 1
        return mock.mock_open(read_data=content).return_value

    return mock.MagicMock(side_effect=open_mock)


embed_image_params = [
    (
        "![[foo.png]]",
        Path("images/foo.png").absolute(),
        "\\includegraphics[width=\\columnwidth,keepaspectratio]"
        f"{{{obsidian_path.format_path(Path('images/foo').absolute())}}}",
    ),
    (
        "![[bar.bmp]]",
        Path("resources/bar.bmp").absolute(),
        "\\includegraphics[width=\\columnwidth,keepaspectratio]"
        f"{{{obsidian_path.format_path(Path('resources/bar').absolute())}}}",
    ),
    (
        "![[bar.bmp|500]]",
        Path("resources/bar.bmp").absolute(),
        "\\includegraphics[width=250pt,keepaspectratio]"
        f"{{{obsidian_path.format_path(Path('resources/bar').absolute())}}}",
    ),
    (
        "![[bar.bmp|500x100]]",
        Path("resources/bar.bmp").absolute(),
        "\\includegraphics[width=250pt,height=50pt]"
        f"{{{obsidian_path.format_path(Path('resources/bar').absolute())}}}",
    ),
]


@pytest.mark.parametrize(
    "input_text, found_path, expected", embed_image_params
)
def test_embed_image(input_text, found_path, expected):
    with mock.patch("obsidian_to_latex.obsidian_path.find_file") as mock_find:
        process_markdown.VAULT_ROOT = Path.cwd()
        mock_find.return_value = found_path
        result = process_markdown.embed_image(input_text)
    assert result == expected


string_to_tex_params = [
    (
        f"{file_line()} Basic: string to tex",
        "This is simple text with nothing to process",
        "This is simple text with nothing to process",
    ),
    (f"{file_line()} Escaped: Escape special characters", R"#", R"\#"),
    (f"{file_line()} Escaped: Escape special characters", R"$", R"\$"),
    (f"{file_line()} Escaped: Escape special characters", R"%", R"\%"),
    (f"{file_line()} Escaped: Escape special characters", R"&", R"\&"),
    (f"{file_line()} Escaped: Escape special characters", R"_", R"\_"),
    (f"{file_line()} Escaped: Escape special characters", R"{", R"\{"),
    (f"{file_line()} Escaped: Escape special characters", R"}", R"\}"),
    (
        f"{file_line()} Code: code snippet in text",
        R"`This is a code snippet`",
        R"\verb`This is a code snippet`",
    ),
    (
        f"{file_line()} Code: Two code snippets",
        R"This `line` has `two` code snippets",
        R"This \verb`line` has \verb`two` code snippets",
    ),
    (
        f"{file_line()} Code: Ignore speacial characters in code snippets",
        R"The underscore `_` needs to be excaped in latex _",
        R"The underscore \verb`_` needs to be excaped in latex \_",
    ),
    (
        f"{file_line()} Code: Ignore special characters in code snippets",
        R"The underscore `_` needs to be excaped in latex _",
        R"The underscore \verb`_` needs to be excaped in latex \_",
    ),
    (
        f"{file_line()} Code: Special char between two code snippets",
        R"Running `foo` costs $20, but running `bar` costs $5.",
        R"Running \verb`foo` costs \$20, but running \verb`bar` costs \$5.",
    ),
    (
        f"{file_line()} Link: Convert markdown links",
        R"You can find the reference you need [here](https://www.google.com/).",
        R"You can find the reference you need \href{https://www.google.com/}{here}.",
    ),
    (
        f"{file_line()} Link: Convert multiple markdown links to hyperref in one line",
        (
            "You can find the reference you need [here](https://www.google.com/) "
            "and [there](https://duckduckgo.com/)."
        ),
        (
            R"You can find the reference you need \href{https://www.google.com/}{here} "
            R"and \href{https://duckduckgo.com/}{there}."
        ),
    ),
    (
        f"{file_line()} Link: Convert obsidian paragraph link",
        ("See [[#^abc123|this section]] for more information"),
        (R"See \hyperref[abc123]{this section} for more information"),
    ),
    (
        f"{file_line()} Link: Convert obsidian paragraph reference",
        "This is a useful paragraph ^abc123",
        R"This is a useful paragraph \label{abc123}",
    ),
    (
        f"{file_line()} Link: Reference must be at end of line",
        "This is not a useful paragraph ^abc123, since the ref is not at the end",
        R"This is not a useful paragraph \textasciicircum{}abc123, since the ref is not at the end",
    ),
    (
        f"{file_line()} Link: An open square bracket gets escaped",
        "See, [ this is not a link.",
        R"See, \[ this is not a link.",
    ),
]


@pytest.mark.parametrize(
    "_test_name, input_string, expected", string_to_tex_params
)
def test_string_to_tex(_test_name, input_string, expected):
    result = process_markdown.string_to_tex(input_string)
    assert expected == result


file_ref_label_params = [
    (Path("hello.md").resolve(), "file_hello_md"),
]


@pytest.mark.parametrize("path_to_file, expected", file_ref_label_params)
def test_file_ref_label(path_to_file, expected):
    result = process_markdown.file_ref_label(path_to_file)
    assert expected == result
