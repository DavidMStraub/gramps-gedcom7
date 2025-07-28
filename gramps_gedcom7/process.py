"""Process GEDCOM structures and import them into the Gramps database."""

from __future__ import annotations

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db import DbTxn, DbWriteBase

from .family import handle_family
from .header import handle_header
from .individual import handle_individual
from .multimedia import handle_multimedia
from .note import handle_shared_note
from .repository import handle_repository
from .settings import ImportSettings
from .source import handle_source
from .submitter import handle_submitter
from .util import make_handle


def process_gedcom_structures(
    gedcom_structures: list[g7types.GedcomStructure],
    db: DbWriteBase,
    settings: ImportSettings,
):
    """Process GEDCOM structures and import them into the Gramps database.

    Args:
        gedcom_structures: The GEDCOM structures to process.
        db: The Gramps database to import the GEDCOM structures into.
    """
    if len(gedcom_structures) < 2:
        raise ValueError("No GEDCOM structures to process.")
    first_structure = gedcom_structures[0]
    if first_structure.tag != g7const.HEAD:
        raise ValueError(
            f"First structure must be a HEAD structure, but got {first_structure.tag}"
        )
    # Note: gedcom7 library v0.4.0 doesn't include TRLR in the structures
    # So we skip this check for now
    # last_structure = gedcom_structures[-1]
    # if last_structure.tag != g7const.TRLR:
    #     raise ValueError(
    #         f"Last structure must be a TRLR structure, but got {last_structure.tag}"
    #     )

    handle_header(first_structure, db, settings=settings)

    # Create a map of handles to XREFs
    xref_handle_map = {}
    for structure in gedcom_structures:
        if structure.xref and structure.xref not in xref_handle_map:
            xref_handle_map[structure.xref] = make_handle()

    # Handle the remaining structures (excluding header and trailer)
    objects = []
    for structure in gedcom_structures[1:-1]:
        objects += (
            handle_structure(
                structure, xref_handle_map=xref_handle_map, settings=settings
            )
            or []
        )

    add_objects_to_database(objects, db)


def handle_structure(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> list | None:
    """Handle a single GEDCOM structure and import it into the Gramps database.

    Args:
        structure: The GEDCOM structure to handle.
        db: The Gramps database to import the GEDCOM structure into.
    """
    if structure.tag == g7const.FAM:
        return handle_family(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.INDI:
        return handle_individual(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.OBJE:
        return handle_multimedia(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.REPO:
        return handle_repository(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.SNOTE:
        return handle_shared_note(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.SOUR:
        return handle_source(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.SUBM:
        return handle_submitter(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    return None


def add_objects_to_database(objects, db):
    with DbTxn("Add child to family", db) as transaction:
        for obj in objects:
            if obj.__class__.__name__ == "Person":
                db.add_person(obj, transaction)
            elif obj.__class__.__name__ == "Family":
                db.add_family(obj, transaction)
            elif obj.__class__.__name__ == "Event":
                db.add_event(obj, transaction)
            elif obj.__class__.__name__ == "Citation":
                db.add_citation(obj, transaction)
            elif obj.__class__.__name__ == "Source":
                db.add_source(obj, transaction)
            elif obj.__class__.__name__ == "Note":
                db.add_note(obj, transaction)
            elif obj.__class__.__name__ == "Media":
                db.add_media(obj, transaction)
            elif obj.__class__.__name__ == "Place":
                db.add_place(obj, transaction)
            elif obj.__class__.__name__ == "Repository":
                db.add_repository(obj, transaction)
            elif obj.__class__.__name__ == "Tag":
                db.add_tag(obj, transaction)
