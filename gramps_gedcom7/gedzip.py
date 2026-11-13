"""Name media files in GEDZIP archives after their paths, as media archives do."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Callable

from gedcom7 import gedzip as g7gedzip
from gedcom7 import types as g7types
from gramps.gen.lib import Media

from . import report
from .util import structure_path

MediaFile = Callable[[Media], "g7gedzip.FileSource | None"]
"""Give a media object's file as bytes, a path, or a function opening it, or
None if it is unavailable."""

AttachFile = Callable[[Media, g7types.GedcomStructure], None]

_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://")


def is_url(path: str) -> bool:
    """Say whether a media path is a URL rather than a file path."""
    return _URL.match(path) is not None


def archive_name(path: str) -> str | None:
    """Name the archive entry for a media path, or None if it cannot be one.

    A relative path is the name; an absolute one, or one leaving its folder,
    cannot be.
    """
    if "\\" in path or ":" in path:
        return None
    name = posixpath.normpath(path)
    if name.startswith(("/", "../")) or name in (".", ".."):
        return None
    return name


def attach_from(archive: g7gedzip.GedzipReader) -> AttachFile:
    """Give media the names of their files in an archive, reporting missing ones."""

    def attach(media: Media, file_structure: g7types.GedcomStructure) -> None:
        path = file_structure.text
        if not g7gedzip.is_local_file(path):
            return
        media.set_path(g7gedzip.entry_name(path))
        if not archive.has(path):
            report.note(structure_path(file_structure), "file missing from archive")

    return attach
