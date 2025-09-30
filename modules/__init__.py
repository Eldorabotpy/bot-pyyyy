# modules/__init__.py
from . import file_ids
file_id_manager = file_ids  # alias p/ código legado

__all__ = [
    "file_ids",
    "file_id_manager",
]
