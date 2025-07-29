"""Process GEDCOM 7 occurrence extension data.

This module handles the gedcom-occurrences extension that allows events to be
recorded as independent, reusable records that multiple individuals can
participate in, matching GRAMPS' native event model.

Extension URI: https://github.com/glamberson/gedcom-occurrences
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import types as g7types
from gramps.gen.lib import Event, EventRef, EventRoleType, EventType
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation
from .event import handle_place
from .settings import ImportSettings

if TYPE_CHECKING:
    from gedcom7.types import GedcomStructure

# Extension tags
TAG_OCUR = "_OCUR"
TAG_OCREF = "_OCREF"
TAG_PART = "_PART"
TAG_PRESENCE = "_PRESENCE"
TAG_ATTR = "_ATTR"

# Extension URI
OCCURRENCE_EXTENSION_URI = "https://github.com/glamberson/gedcom-occurrences"


def handle_occurrence(
    structure: GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> tuple[Event, list[BasicPrimaryObject]]:
    """Convert a _OCUR occurrence structure to a GRAMPS Event object.

    Args:
        structure: The GEDCOM structure containing the occurrence data.
        xref_handle_map: A map of XREFs to GRAMPS handles.
        settings: Import settings.

    Returns:
        A tuple containing the GRAMPS Event object and a list of additional
        objects created during processing.
    """
    if not structure.xref:
        raise ValueError("_OCUR structure must have an XREF")

    event = Event()
    event.handle = xref_handle_map.get(structure.xref, util.make_handle())
    objects = []

    # Track participants for later processing
    participants = []

    for child in structure.children:
        if child.tag == "TYPE":
            # Map occurrence type to GRAMPS EventType
            assert isinstance(child.value, str), "Expected TYPE value to be a string"
            event_type = _map_occurrence_type_to_event_type(child.value)
            event.set_type(event_type)
            if child.children:
                # Handle TYPE.PHRASE for custom types
                for subchild in child.children:
                    if subchild.tag == "PHRASE" and isinstance(subchild.value, str):
                        event.set_description(subchild.value)
        
        elif child.tag == "DATE":
            # Handle date information
            assert isinstance(
                child.value,
                (
                    g7types.Date,
                    g7types.DatePeriod,
                    g7types.DateApprox,
                    g7types.DateRange,
                ),
            ), "Expected value to be a date-related object"
            date = util.gedcom_date_value_to_gramps_date(child.value)
            event.set_date_object(date)
        
        elif child.tag == "PLAC":
            # Handle place information
            place, other_objects = handle_place(child, xref_handle_map)
            event.set_place_handle(place.handle)
            objects.append(place)
            objects.extend(other_objects)
        
        elif child.tag == TAG_PART:
            # Store participant information for later processing
            if child.pointer:
                participants.append({
                    "xref": child.pointer,
                    "children": child.children
                })
        
        elif child.tag == "SOUR":
            # Handle source citations
            citation, other_objects = handle_citation(
                child,
                xref_handle_map=xref_handle_map,
                settings=settings,
            )
            objects.extend(other_objects)
            event.add_citation(citation.handle)
            objects.append(citation)
        
        elif child.tag == "NOTE":
            # Handle inline notes
            event, note = util.add_note_to_object(child, event)
            objects.append(note)
        
        elif child.tag == "SNOTE" and child.pointer:
            # Handle shared notes
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            event.add_note(note_handle)
        
        elif child.tag == "OBJE":
            # Handle media objects
            event = util.add_media_ref_to_object(child, event, xref_handle_map)
        
        elif child.tag == "RESN":
            # Handle privacy/restriction
            util.set_privacy_on_object(resn_structure=child, obj=event)
        
        elif child.tag == "UID":
            # Handle unique identifier
            util.add_uid_to_object(child, event)
        
        elif child.tag == TAG_ATTR:
            # Handle custom attributes
            for attr_child in child.children:
                if attr_child.tag == "TYPE" and attr_child.value:
                    # Add as event attribute
                    event.add_attribute((str(attr_child.value), ""))

    # Store participant info in event for later processing
    if participants:
        # We'll process these when handling individuals
        event.set_tag(f"_participants:{str(participants)}")

    return event, objects


def handle_occurrence_reference(
    structure: GedcomStructure,
    person,  # gramps.gen.lib.Person
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> None:
    """Handle an _OCREF occurrence reference and add it to a person.

    Args:
        structure: The GEDCOM structure containing the _OCREF data.
        person: The GRAMPS Person object to add the event reference to.
        xref_handle_map: A map of XREFs to GRAMPS handles.
        settings: Import settings.
    """
    if not structure.pointer:
        raise ValueError("_OCREF must have a pointer to an occurrence")

    try:
        event_handle = xref_handle_map[structure.pointer]
    except KeyError:
        raise ValueError(f"Occurrence {structure.pointer} not found")

    # Create EventRef
    event_ref = EventRef()
    event_ref.set_reference_handle(event_handle)

    # Process _OCREF children for role and other data
    for child in structure.children:
        if child.tag == "ROLE":
            # Set the role in the event
            assert isinstance(child.value, str), "Expected ROLE value to be a string"
            role = _map_occurrence_role_to_event_role(child.value)
            event_ref.set_role(role)
        
        elif child.tag == "NOTE":
            # Add note specific to this person's participation
            _, note = util.add_note_to_object(child, None)
            if note and hasattr(event_ref, 'add_note'):
                event_ref.add_note(note.handle)
        
        elif child.tag == TAG_PRESENCE:
            # Handle presence information
            if child.value == "Absent":
                # Mark as absent in some way
                if hasattr(event_ref, 'set_absent'):
                    event_ref.set_absent(True)

    # Add the event reference to the person
    person.add_event_ref(event_ref)


def _map_occurrence_type_to_event_type(occurrence_type: str) -> EventType:
    """Map occurrence TYPE values to GRAMPS EventType.

    Args:
        occurrence_type: The occurrence type string.

    Returns:
        The corresponding GRAMPS EventType.
    """
    # Map common types
    type_mapping = {
        "Census": EventType.CENSUS,
        "Burial": EventType.BURIAL,
        "Marriage": EventType.MARRIAGE,
        "Divorce": EventType.DIVORCE,
        "Birth": EventType.BIRTH,
        "Death": EventType.DEATH,
        "Baptism": EventType.BAPTISM,
        "Christening": EventType.CHRISTENING,
        "Adoption": EventType.ADOPTION,
        "Confirmation": EventType.CONFIRMATION,
        "Cremation": EventType.CREMATION,
        "Emigration": EventType.EMIGRATION,
        "Immigration": EventType.IMMIGRATION,
        "Naturalization": EventType.NATURALIZATION,
        "Probate": EventType.PROBATE,
        "Will": EventType.WILL,
        "Graduation": EventType.GRADUATION,
        "Retirement": EventType.RETIREMENT,
        "Occupation": EventType.OCCUPATION,
        "Education": EventType.EDUCATION,
        "Residence": EventType.RESIDENCE,
        "Religion": EventType.RELIGION,
        "Military": EventType.MILITARY_SERVICE,
    }

    # Return mapped type or CUSTOM
    event_type = type_mapping.get(occurrence_type)
    if event_type is None:
        event_type = EventType.CUSTOM
        event_type.set_string(occurrence_type)
    
    return event_type


def _map_occurrence_role_to_event_role(role: str) -> EventRoleType:
    """Map occurrence ROLE values to GRAMPS EventRoleType.

    Args:
        role: The role string.

    Returns:
        The corresponding GRAMPS EventRoleType.
    """
    # Map common roles
    role_mapping = {
        "Principal": EventRoleType.PRIMARY,
        "Witness": EventRoleType.WITNESS,
        "Officiant": EventRoleType.CLERGY,
        "Informant": EventRoleType.INFORMANT,
        "Head": EventRoleType.FAMILY,
        "Member": EventRoleType.FAMILY,
        "Groom": EventRoleType.GROOM,
        "Bride": EventRoleType.BRIDE,
        "Guest": EventRoleType.WITNESS,
    }

    # Return mapped role or CUSTOM
    event_role = role_mapping.get(role)
    if event_role is None:
        event_role = EventRoleType.CUSTOM
        event_role.set_string(role)
    
    return event_role