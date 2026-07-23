from pathlib import Path

import pytest

from obsidian_to_typst import obsidian_path


@pytest.fixture(autouse=True)
def setup_teardown() -> None:
    yield
    obsidian_path.VAULT_ROOT = None


def test_root_path(tmp_path: Path) -> None:
    obsidian_path.VAULT_ROOT = tmp_path
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file_path = sub_dir / "foo.jpg"
    file_path.touch()

    result = obsidian_path.root_path(file_path)

    assert result == "/sub/foo.jpg"
    assert "\\" not in result


def test_root_path_top_level(tmp_path: Path) -> None:
    obsidian_path.VAULT_ROOT = tmp_path
    file_path = tmp_path / "foo.jpg"
    file_path.touch()

    result = obsidian_path.root_path(file_path)

    assert result == "/foo.jpg"
