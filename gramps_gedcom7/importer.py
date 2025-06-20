"""Import a GEDCOM file into a Gramps database."""

from __future__ import annotations

from gramps.gen.db import DbWriteBase
from gramps.gen.user import UserBase
import gedcom7
from pathlib import Path
from typing import TextIO, BinaryIO

from . import process
from .settings import ImportSettings


def import_gedcom(
    input_file: str | Path | TextIO | BinaryIO,
    db: DbWriteBase,
    settings: ImportSettings = ImportSettings(),
) -> None:
    """Import a GEDCOM file into a Gramps database.

    Args:

        input_file: The GEDCOM file to import. This can be a string, Path object, or file-like object.
        db: The Gramps database to import the GEDCOM file into.
    """
    # Check if input_file is a string or Path object
    if isinstance(input_file, (str, Path)):
        with open(input_file, "r", encoding="utf-8") as f:
            gedcom_data: str = f.read()
    elif isinstance(input_file, TextIO):
        gedcom_data = input_file.read()
    elif isinstance(input_file, BinaryIO):
        gedcom_data = input_file.read().decode("utf-8")
    else:
        raise TypeError(
            "input_file must be a string, Path object, or file-like object."
        )

    gedcom_structures = gedcom7.loads(gedcom_data)
    process.process_gedcom_structures(gedcom_structures, db, settings=settings)
