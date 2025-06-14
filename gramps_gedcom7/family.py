"""Handle GEDCOM family records and import them into the Gramps database."""

from typing import List

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gramps.gen.lib import ChildRef, ChildRefType, Family, MediaRef, EventRef, EventType
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation
from .event import handle_event

EVENT_TYPE_MAP = {
    g7const.ANUL: EventType.ANNULMENT,
    g7const.CENS: EventType.CENSUS,
    g7const.DIV: EventType.DIVORCE,
    g7const.DIVF: EventType.DIV_FILING,
    g7const.ENGA: EventType.ENGAGEMENT,
    g7const.MARB: EventType.MARR_BANNS,
    g7const.MARC: EventType.MARR_CONTR,
    g7const.MARL: EventType.MARR_LIC,
    g7const.MARS: EventType.MARR_SETTL,
    g7const.EVEN: EventType.CUSTOM,
}


def handle_family(
    structure: g7types.GedcomStructure, xref_handle_map: dict[str, str]
) -> List[BasicPrimaryObject]:
    """Handle an family record and convert it to Gramps objects.

    Args:
        structure: The GEDCOM note structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.

    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    family = Family()
    objects = []
    for child in structure.children:
        # TODO handle family attributes
        if child.tag == g7const.RESN:
            util.set_privacy_on_object(resn_structure=child, obj=family)
        elif child.tag == g7const.HUSB and child.pointer != g7grammar.voidptr:
            person_handle = xref_handle_map.get(child.pointer)
            if not person_handle:
                raise ValueError(f"Person {child.pointer} not found")
            family.set_father_handle(person_handle)
            # TODO handle HUSB PHRASE
        elif child.tag == g7const.WIFE and child.pointer != g7grammar.voidptr:
            person_handle = xref_handle_map.get(child.pointer)
            if not person_handle:
                raise ValueError(f"Person {child.pointer} not found")
            family.set_mother_handle(person_handle)
            # TODO handle WIFE PHRASE
        elif child.tag == g7const.CHIL and child.pointer != g7grammar.voidptr:
            person_handle = xref_handle_map.get(child.pointer)
            if not person_handle:
                raise ValueError(f"Child {child.pointer} not found")
            child_ref = ChildRef()
            child_ref.ref = person_handle
            family.add_child_ref(child_ref)
            # TODO handle CHIL PHRASE
        # TODO handle associations
        elif child.tag == g7const.SNOTE and child.pointer != g7grammar.voidptr:
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            family.add_note(note_handle)
        elif child.tag == g7const.NOTE:
            family, note = util.add_note_to_object(child, family)
            objects.append(note)
        elif child.tag == g7const.SOUR:
            citation, other_objects = handle_citation(
                child, xref_handle_map=xref_handle_map
            )
            objects.extend(other_objects)
            family.add_citation(citation.handle)
            objects.append(citation)
        # TODO handle indentifier
        elif child.tag == g7const.OBJE:
            family = util.add_media_ref_to_object(child, family, xref_handle_map)
        elif child.tag in EVENT_TYPE_MAP:
            event, other_objects = handle_event(
                child, xref_handle_map=xref_handle_map, event_type_map=EVENT_TYPE_MAP
            )
            objects.extend(other_objects)
            event_ref = EventRef()
            event_ref.ref = event.handle
            family.add_event_ref(event_ref)
            objects.append(event)
    family = util.add_ids(family, structure=structure, xref_handle_map=xref_handle_map)
    util.set_change_date(structure=structure, obj=family)
    objects.append(family)
    return objects
