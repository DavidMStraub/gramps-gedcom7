"""Import a GEDCOM file into a Gramps database."""

from __future__ import annotations

from gramps.gen.db import DbWriteBase
import gedcom7
import io
from pathlib import Path
from typing import TextIO, BinaryIO

from gedcom7 import gedzip as g7gedzip

from . import process
from .gedzip import attach_from
from .report import Progress, Report
from .settings import ImportSettings


def import_gedcom(
    input_file: str | Path | TextIO | BinaryIO,
    db: DbWriteBase,
    settings: ImportSettings | None = None,
    progress: Progress | None = None,
) -> Report:
    """Import a GEDCOM file into a Gramps database.

    Args:

        input_file: The GEDCOM file to import. This can be a string, Path object, or file-like object.
        db: The Gramps database to import the GEDCOM file into.
        settings: Import settings controlling how GEDCOM data is imported.
        progress: Called with how far the import has got, and how far it goes.

    Returns:
        A report of what was not imported.

    Raises:
        BrokenPointersError: Pointers point at records missing from the file.
    """
    settings = settings or ImportSettings()
    # Check if input_file is a string or Path object
    if isinstance(input_file, (str, Path)):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                gedcom_data: str = f.read()
        except UnicodeDecodeError as e:
            raise ValueError(
                f"GEDCOM 7 requires UTF-8 encoding, but '{input_file}' contains invalid UTF-8 bytes: {e}"
            ) from e
    elif isinstance(input_file, io.TextIOBase):
        try:
            gedcom_data = input_file.read()
        except UnicodeDecodeError as e:
            raise ValueError(
                f"GEDCOM 7 requires UTF-8 encoding, but the file contains invalid UTF-8 bytes: {e}"
            ) from e
    elif isinstance(input_file, (io.RawIOBase, io.BufferedIOBase)):
        try:
            gedcom_data = input_file.read().decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(
                f"GEDCOM 7 requires UTF-8 encoding, but the file contains invalid UTF-8 bytes: {e}"
            ) from e
    else:
        raise TypeError(
            "input_file must be a string, Path object, or file-like object."
        )

    try:
        gedcom_structures = gedcom7.loads(gedcom_data)
    except gedcom7.GedcomParseError as e:
        source = f"'{input_file}'" if isinstance(input_file, (str, Path)) else "input"
        raise ValueError(f"{source} is not a valid GEDCOM 7 file: {e}") from e
    return process.process_gedcom_structures(
        gedcom_structures, db, settings=settings, progress=progress
    )


def import_gedzip(
    input_file: str | Path | BinaryIO,
    db: DbWriteBase,
    settings: ImportSettings | None = None,
    progress: Progress | None = None,
) -> Report:
    """Import a GEDZIP archive into a Gramps database.

    Media objects get the names of their files in the archive as paths; the
    files themselves are not stored.

    Args:
        input_file: The archive, as a path or a file opened in binary mode.
        db: The Gramps database to import into.
        settings: Import settings controlling how GEDCOM data is imported.
        progress: Called with how far the import has got, and how far it goes.

    Returns:
        A report of what was not imported.
    """
    try:
        archive = g7gedzip.GedzipReader(input_file)
    except gedcom7.GedcomParseError as e:
        source = f"'{input_file}'" if isinstance(input_file, (str, Path)) else "input"
        raise ValueError(f"{source} is not a valid GEDZIP file: {e}") from e
    with archive:
        return process.process_gedcom_structures(
            archive.records,
            db,
            settings=settings or ImportSettings(),
            progress=progress,
            attach_file=attach_from(archive),
        )
