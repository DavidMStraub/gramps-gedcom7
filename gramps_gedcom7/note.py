"""Handle GEDCOM shared note records and import them into the Gramps database."""

from typing import List
from gramps.gen.lib.primaryobj import BasicPrimaryObject
from gedcom7 import types as g7types
from . import util


def handle_shared_note(
    structure: g7types.GedcomStructure, xref_handle_map: dict[str, str]
) -> List[BasicPrimaryObject]:
    """Handle a shared note record and convert it to Gramps objects.

    Args:
        structure: The GEDCOM note structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.

    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    note = util.structure_to_note(structure)
    # set note handle and Gramps ID
    note = util.add_ids(note, structure=structure, xref_handle_map=xref_handle_map)
    # set last change timestamp
    util.set_change_date(structure=structure, obj=note)
    return [note]
