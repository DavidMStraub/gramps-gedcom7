"""Utility functions for unit tests."""

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db.utils import make_database

from gramps_gedcom7 import process
from gramps_gedcom7.settings import ImportSettings


def import_to_memory(gedcom_records: list[g7types.GedcomStructure]):
    db = make_database("sqlite")
    db.load(":memory:")
    header_record = g7types.GedcomStructure(
        tag=g7const.HEAD, pointer="", text="", xref=""
    )
    trailer_record = g7types.GedcomStructure(
        tag=g7const.TRLR, pointer="", text="", xref=""
    )
    gedcom_structures = [header_record] + gedcom_records + [trailer_record]
    settings = ImportSettings()
    process.process_gedcom_structures(
        gedcom_structures=gedcom_structures, db=db, settings=settings
    )
    return db
