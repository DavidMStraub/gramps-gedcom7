"""Enhanced individual handler with GEDCOM 7 extension support.

This module extends the standard individual handler to support occurrence
references (_OCREF) and evidence references (_EVID).
"""

from typing import List

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gramps.gen.lib import (
    EventRef,
    EventRoleType,
    EventType,
    Name,
    NameType,
    Person,
    Surname,
)
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation
from .event import handle_event
from .evidence import handle_evidence_reference
from .occurrence import handle_occurrence_reference
from .settings import ImportSettings

# Import original constants
from .individual import (
    EVENT_TYPE_MAP,
    GENDER_MAP,
    NAME_TYPE_MAP,
    handle_name,
)


def handle_individual_enhanced(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> tuple[Person, list[BasicPrimaryObject]]:
    """Handle an individual record with extension support.

    This enhanced version supports:
    - _OCREF: References to shared occurrence records
    - _EVID: Evidence references and associations

    Args:
        structure: The GEDCOM structure containing the individual data.
        xref_handle_map: A map of XREFs to Gramps handles.
        settings: Import settings.

    Returns:
        A tuple containing the Gramps Person object and a list of additional
        objects created.
    """
    person = Person()
    person.handle = xref_handle_map[structure.xref]
    objects = []

    for child in structure.children:
        if child.tag == g7const.RESN:
            util.set_privacy_on_object(resn_structure=child, obj=person)
        
        elif child.tag == g7const.NAME:
            name, name_objects = handle_name(child, xref_handle_map=xref_handle_map)
            objects.extend(name_objects)
            if name.get_type() == NameType.BIRTH:
                person.set_primary_name(name)
            else:
                person.add_alternate_name(name)
        
        elif child.tag == g7const.SEX:
            assert isinstance(
                child.value, str
            ), "Expected SEX value to be a string"
            person.set_gender(GENDER_MAP.get(child.value, Person.UNKNOWN))
        
        elif child.tag in EVENT_TYPE_MAP:
            event, other_objects = handle_event(
                child,
                xref_handle_map=xref_handle_map,
                event_type_map=EVENT_TYPE_MAP,
                settings=settings,
            )
            objects.extend(other_objects)
            event_ref = EventRef()
            event_ref.set_reference_handle(event.handle)
            event_ref.set_role(EventRoleType.PRIMARY)
            person.add_event_ref(event_ref)
            objects.append(event)
        
        elif child.tag == g7const.FAMC and child.pointer != g7grammar.voidptr:
            family_handle = xref_handle_map.get(child.pointer)
            if not family_handle:
                raise ValueError(f"Family {child.pointer} not found")
            person.add_parent_family_handle(family_handle)
        
        elif child.tag == g7const.FAMS and child.pointer != g7grammar.voidptr:
            family_handle = xref_handle_map.get(child.pointer)
            if not family_handle:
                raise ValueError(f"Family {child.pointer} not found")
            person.add_family_handle(family_handle)
        
        # Extension support
        elif child.tag == "_OCREF":
            # Handle occurrence reference
            handle_occurrence_reference(
                child,
                person,
                xref_handle_map=xref_handle_map,
                settings=settings,
            )
        
        elif child.tag == "_EVID":
            # Handle evidence reference
            handle_evidence_reference(
                child,
                person,
                xref_handle_map=xref_handle_map,
                settings=settings,
            )
        
        elif child.tag == g7const.NOTE:
            person, note = util.add_note_to_object(child, person)
            objects.append(note)
        
        elif child.tag == g7const.SNOTE and child.pointer != g7grammar.voidptr:
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            person.add_note(note_handle)
        
        elif child.tag == g7const.SOUR:
            citation, other_objects = handle_citation(
                child,
                xref_handle_map=xref_handle_map,
                settings=settings,
            )
            objects.extend(other_objects)
            person.add_citation(citation.handle)
            objects.append(citation)
        
        elif child.tag == g7const.OBJE:
            person = util.add_media_ref_to_object(child, person, xref_handle_map)
        
        elif child.tag == g7const.UID:
            util.add_uid_to_object(child, person)
        
        elif child.tag == g7const.EXID:
            # Handle external ID
            for exid_child in child.children:
                if exid_child.tag == g7const.TYPE and isinstance(exid_child.value, str):
                    # Add as attribute
                    from gramps.gen.lib import Attribute, AttributeType
                    attr = Attribute()
                    attr.set_type(f"External ID: {exid_child.value}")
                    if isinstance(child.value, str):
                        attr.set_value(child.value)
                    person.add_attribute(attr)

    return person, objects