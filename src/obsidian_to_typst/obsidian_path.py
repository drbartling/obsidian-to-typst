import os
from pathlib import Path

VAULT_ROOT: Path | None = None
TEMP_FOLDER: Path | None = None


def format_path(path: Path) -> str:
    return str(path).replace(os.path.sep, "/")


def find_file(file_name: str) -> Path:  # pragma: no cover
    for root, _dirs, files in os.walk(VAULT_ROOT):
        if file_name in files:
            full_path: Path = Path(root) / file_name
            return full_path
    msg = f"Unable to locate `{file_name}` under `{VAULT_ROOT}`"
    raise FileNotFoundError(msg)


def rel_path(path: Path) -> Path:
    return Path(os.path.relpath(path, TEMP_FOLDER))


def root_path(path: Path) -> str:
    path = path.resolve()
    return os.path.sep + os.path.relpath(path, VAULT_ROOT)
