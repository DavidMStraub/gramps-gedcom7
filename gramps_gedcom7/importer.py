"""Import a GEDCOM file into a Gramps database."""

from __future__ import annotations

from gramps.gen.db import DbWriteBase
from gramps.gen.user import UserBase
import gedcom7
from pathlib import Path
from typing import TextIO, BinaryIO

from . import process


def import_gedcom(input_file: str | Path | TextIO | BinaryIO, db: DbWriteBase) -> None:
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
    process.process_gedcom_structures(gedcom_structures, db)


def import_gedcom_gramps(database: DbWriteBase, filename: str, user: UserBase) -> None:
    """Import a GEDCOM file into a Gramps database with user context.

    This function has the right signature to be used as a Gramps import plugin.

    Args:
        database: The Gramps database to import the GEDCOM file into.
        filename: The path to the GEDCOM file to import.
        user: The user context for the import operation.
    """
    import_gedcom(filename, database)
