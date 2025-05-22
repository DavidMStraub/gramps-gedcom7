"""Process GEDCOM structures and import them into the Gramps database."""

from gramps.gen.db import DbWriteBase
from gedcom7 import types as g7types, const as g7const

from .family import handle_family
from .header import handle_header
from .individual import handle_individual
from .multimedia import handle_multimedia
from .repository import handle_repository
from .shared_note import handle_shared_note
from .source import handle_source
from .submitter import handle_submitter


def process_gedcom_structures(
    gedcom_structures: list[g7types.GedcomStructure], db: DbWriteBase
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
    last_structure = gedcom_structures[-1]
    if last_structure.tag != g7const.TRLR:
        raise ValueError(
            f"Last structure must be a TRLR structure, but got {last_structure.tag}"
        )

    handle_header(first_structure, db)

    # Handle the remaining structures (excluding header and trailer)
    objects = []
    for structure in gedcom_structures[1:-1]:
        objects += handle_structure(structure)

    # add_objects_to_databse(objects, db)


def handle_structure(structure: g7types.GedcomStructure):
    """Handle a single GEDCOM structure and import it into the Gramps database.

    Args:
        structure: The GEDCOM structure to handle.
        db: The Gramps database to import the GEDCOM structure into.
    """
    if structure.tag == g7const.FAM:
        return handle_family(structure)
    elif structure.tag == g7const.INDI:
        return handle_individual(structure)
    elif structure.tag == g7const.OBJE:
        return handle_multimedia(structure)
    elif structure.tag == g7const.REPO:
        return handle_repository(structure)
    elif structure.tag == g7const.SNOTE:
        return handle_shared_note(structure)
    elif structure.tag == g7const.SOUR:
        return handle_source(structure)
    elif structure.tag == g7const.SUBM:
        return handle_submitter(structure)


def add_objects_to_database(objects, db):
    for obj in objects:
        if obj.__class__.__name__ == "Person":
            db.add_person(obj, obj.gramps_id)
        elif obj.__class__.__name__ == "Family":
            db.add_family(obj, obj.gramps_id)
        elif obj.__class__.__name__ == "Citation":
            db.add_citation(obj, obj.gramps_id)
        elif obj.__class__.__name__ == "Source":
            db.add_source(obj, obj.gramps_id)
        elif obj.__class__.__name__ == "Note":
            db.add_note(obj, obj.gramps_id)
        elif obj.__class__.__name__ == "Media":
            db.add_media(obj, obj.gramps_id)
        elif obj.__class__.__name__ == "Place":
            db.add_place(obj, obj.gramps_id)
        elif obj.__class__.__name__ == "Repository":
            db.add_repository(obj, obj.gramps_id)
        elif obj.__class__.__name__ == "Tag":
            db.add_tag(obj, obj.gramps_id)
