"""Import a GEDCOM file into a Gramps database."""

from gramps.gen.db import DbWriteBase
import gedcom7
from pathlib import Path
from typing import TextIO, BinaryIO

from . import process


def import_gedcom(file_input: str | Path | TextIO | BinaryIO, db: DbWriteBase) -> None:
    """Import a GEDCOM file into a Gramps database.

    Args:

        - file_input: The GEDCOM file to import. This can be a string, Path object, or file-like object.
        - db: The Gramps database to import the GEDCOM file into.
    """
    # Check if file_input is a string or Path object
    if isinstance(file_input, (str, Path)):
        with open(file_input, "r", encoding="utf-8") as f:
            gedcom_data = f.read()
    elif isinstance(file_input, (TextIO, BinaryIO)):
        gedcom_data = file_input.read()
    else:
        raise TypeError(
            "file_input must be a string, Path object, or file-like object."
        )

    gedcom_structures = gedcom7.loads(gedcom_data)
    process.process_gedcom_structures(gedcom_structures, db)
