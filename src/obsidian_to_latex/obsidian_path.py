import os
from pathlib import Path

VAULT_ROOT = None


def format_path(path: Path) -> str:
    return str(path).replace(os.path.sep, "/")


def find_file(file_name: str) -> Path:  # pragma: no cover
    for root, _dirs, files in os.walk(VAULT_ROOT):
        if file_name in files:
            return Path(os.path.join(root, file_name))
    raise FileNotFoundError(
        f"Unable to locate `{file_name}` under `{VAULT_ROOT}`"
    )
