"""Handle GEDCOM attributes kept as Gramps attributes."""

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation
from .settings import ImportSettings
from .types import AttributeBase


def handle_attribute(
    structure: g7types.GedcomStructure,
    obj: AttributeBase,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> list[BasicPrimaryObject]:
    """Add an attribute to an object, with its citations, notes and privacy.

    Returns the notes and citations made.
    """
    attribute = util.handle_attribute_structure(structure, obj)
    objects: list[BasicPrimaryObject] = []
    for child in structure.children:
        if child.tag == g7const.RESN:
            util.set_privacy_on_object(resn_structure=child, obj=attribute)
        elif child.tag == g7const.NOTE:
            attribute, note = util.add_note_to_object(child, attribute)
            objects.append(note)
        elif (
            child.tag == g7const.SNOTE
            and child.pointer
            and child.pointer != g7grammar.voidptr
        ):
            attribute.add_note(xref_handle_map[child.pointer])
        elif child.tag == g7const.SOUR:
            citation, other_objects = handle_citation(
                child, xref_handle_map=xref_handle_map, settings=settings
            )
            objects.extend(other_objects)
            attribute.add_citation(citation.handle)
            objects.append(citation)
    return objects
