"""Handle GEDCOM header records and import them into the Gramps database."""

from gramps.gen.db import DbWriteBase
from gedcom7 import types as g7types
from .settings import ImportSettings


def handle_header(
    structure: g7types.GedcomStructure, db: DbWriteBase, settings: ImportSettings
):
    """Handle a header record and import it into the Gramps database.

    Args:
        structure: The GEDCOM header structure to handle.
        db: The Gramps database to import into.
    """
    # TODO: Implement header import
    pass
