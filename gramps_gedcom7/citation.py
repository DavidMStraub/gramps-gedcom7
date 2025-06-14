"""Handle GEDCOM source citation records."""

from typing import List
from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import Citation, MediaRef
from gramps.gen.lib.primaryobj import BasicPrimaryObject
from . import util


CONFIDENCE_MAP = {
    "0": Citation.CONF_VERY_LOW,
    "1": Citation.CONF_LOW,
    "2": Citation.CONF_NORMAL,
    "3": Citation.CONF_HIGH,
}


def handle_citation(
    structure: g7types.GedcomStructure, xref_handle_map: dict[str, str]
) -> tuple[Citation, List[BasicPrimaryObject]]:
    """Handle a citation record and convert it to Gramps objects.

    Args:
        structure: The GEDCOM citation structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.

    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    citation = Citation()
    objects = []

    for child in structure.children:
        if child.tag == g7const.PAGE:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                citation.set_page(child.value)
        elif child.tag == g7const.QUAY:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                citation.set_confidence_level(
                    CONFIDENCE_MAP.get(child.value, Citation.CONF_NORMAL)
                )
        elif child.tag == g7const.SNOTE:
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            citation.add_note(note_handle)
        elif child.tag == g7const.NOTE:
            citation, note = util.add_note_to_object(child, citation)
            objects.append(note)
        elif child.tag == g7const.OBJE:
            citation = util.add_media_ref_to_object(child, citation, xref_handle_map)
        # TODO handle DATA and EVEN
    return citation, objects
