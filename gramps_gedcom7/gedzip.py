"""Move media files in and out of GEDZIP archives, wherever they are stored."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import IO

from gedcom7 import gedzip as g7gedzip
from gedcom7 import types as g7types
from gramps.gen.lib import Media

from . import report
from .util import structure_path

StoreMedia = Callable[[Media, str, IO[bytes]], str]
"""Store a file from an archive, given its media object, its name in the archive
and its content, and return the path to give the media object."""

MediaFile = Callable[[Media], "g7gedzip.FileSource | None"]
"""Give a media object's file as bytes, a path, or a function opening it, or
None if it is unavailable."""

AttachFile = Callable[[Media, g7types.GedcomStructure], None]

# Prefixes of a Gramps media path that point at a file on the web.
WEB_SCHEMES = ("http://", "https://", "ftp://")


def attach_from(
    archive: g7gedzip.GedzipReader, store_media: StoreMedia | None
) -> AttachFile:
    """Point media at the files an archive holds, storing them if asked to."""

    def attach(media: Media, file_structure: g7types.GedcomStructure) -> None:
        path = file_structure.text
        if not g7gedzip.is_local_file(path):
            return
        name = g7gedzip.entry_name(path)
        media.set_path(name)
        if not archive.has(path):
            report.note(structure_path(file_structure), "file missing from archive")
            return
        if store_media is not None:
            with archive.open(path) as file:
                media.set_path(store_media(media, name, file))

    return attach


def extract_to(directory: str | os.PathLike[str]) -> StoreMedia:
    """Store files under a directory, keeping any file already there.

    The media object gets the absolute path and the file's checksum.
    """
    root = Path(directory)

    def store(media: Media, name: str, file: IO[bytes]) -> str:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_name(target.name + ".part")
        md5 = hashlib.md5()
        with open(part, "wb") as out:
            while chunk := file.read(65536):
                md5.update(chunk)
                out.write(chunk)
        checksum = md5.hexdigest()
        stem, suffix, number = target.stem, target.suffix, 1
        while target.exists():
            if _md5(target) == checksum:
                part.unlink()
                break
            number += 1
            target = target.with_name(f"{stem}-{number}{suffix}")
        else:
            part.rename(target)
        media.set_checksum(checksum)
        return str(target)

    return store


def _md5(path: Path) -> str:
    md5 = hashlib.md5()
    with open(path, "rb") as file:
        while chunk := file.read(65536):
            md5.update(chunk)
    return md5.hexdigest()


def files_under(base_path: str | os.PathLike[str]) -> MediaFile:
    """Find media files on disk, a relative path being relative to a base."""
    base = Path(base_path).expanduser()

    def media_file(media: Media) -> str | None:
        path = base / Path(media.get_path()).expanduser()
        return str(path) if path.is_file() else None

    return media_file


class ArchiveNames:
    """Name the archive entry each media file is written as, each name once."""

    def __init__(self) -> None:
        """Start with no names taken."""
        self.by_path: dict[str, str] = {}
        self.taken: set[str] = set()

    def name(self, path: str) -> str:
        """Name the entry for a media path; the same path gets the same name."""
        if path in self.by_path:
            return self.by_path[path]
        wanted = "media/" + _relative(path)
        name, number = wanted, 1
        while name in self.taken:
            number += 1
            stem = PurePosixPath(wanted)
            name = str(stem.with_name(f"{stem.stem}-{number}{stem.suffix}"))
        self.taken.add(name)
        self.by_path[path] = name
        return name


def _relative(path: str) -> str:
    """Keep a relative path as it is, but only the file name of any other."""
    posix = PurePosixPath(path.replace("\\", "/"))
    parts = [part for part in posix.parts if part not in ("", ".")]
    if posix.is_absolute() or ".." in parts or (parts and ":" in parts[0]):
        parts = parts[-1:]
    return "/".join(parts) or "file"
