"""Process GEDCOM 7 event data."""

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import Attribute, AttributeType, Event, EventType, Place, PlaceName
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation
from .settings import ImportSettings


def handle_event(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    event_type_map: dict[str, int],
    settings: ImportSettings,
) -> tuple[Event, list[BasicPrimaryObject]]:
    """Convert a GEDCOM event structure to a Gramps Event object.

    Args:
        structure: The GEDCOM structure containing the event data.
        xref_handle_map: A map of XREFs to Gramps handles.
        event_type_map: A mapping of GEDCOM event tags to Gramps EventType values.

    Returns:
        A tuple containing the Gramps Event object and a list of additional objects created.
    """
    event = Event()
    event.set_type(event_type_map.get(structure.tag, EventType.CUSTOM))
    event.handle = util.make_handle()
    objects = []
    for child in structure.children:
        if child.tag == g7const.TYPE:
            if event.get_type() == EventType.CUSTOM:
                # If the event type is custom, set it to the value from the TYPE tag
                assert isinstance(
                    child.value, str
                ), "Expected TYPE value to be a string"
                event.set_type(EventType(child.value))
        elif child.tag == g7const.RESN:
            util.set_privacy_on_object(resn_structure=child, obj=event)
        elif child.tag == g7const.PHON:
            assert isinstance(child.value, str), "Expected value to be a string"
            attr = Attribute()
            attr.set_type(AttributeType.CUSTOM)
            attr.get_type().string = "Phone"
            attr.set_value(child.value)
            event.add_attribute(attr)
        elif child.tag == g7const.EMAIL:
            assert isinstance(child.value, str), "Expected value to be a string"
            attr = Attribute()
            attr.set_type(AttributeType.CUSTOM)
            attr.get_type().string = "Email"
            attr.set_value(child.value)
            event.add_attribute(attr)
        elif child.tag == g7const.FAX:
            assert isinstance(child.value, str), "Expected value to be a string"
            attr = Attribute()
            attr.set_type(AttributeType.CUSTOM)
            attr.get_type().string = "Fax"
            attr.set_value(child.value)
            event.add_attribute(attr)
        elif child.tag == g7const.WWW:
            assert isinstance(child.value, str), "Expected value to be a string"
            attr = Attribute()
            attr.set_type(AttributeType.CUSTOM)
            attr.get_type().string = "Website"
            attr.set_value(child.value)
            event.add_attribute(attr)
        # TODO handle association
        # TODO handle address
        # TODO handle AGNC, RELI, CAUS
        elif child.tag == g7const.SNOTE and child.pointer != g7grammar.voidptr:
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            event.add_note(note_handle)
        elif child.tag == g7const.NOTE:
            event, note = util.add_note_to_object(child, event)
            objects.append(note)
        # TODO handle media
        elif child.tag == g7const.SOUR:
            citation, other_objects = handle_citation(
                child,
                xref_handle_map=xref_handle_map,
                settings=settings,
            )
            objects.extend(other_objects)
            event.add_citation(citation.handle)
            objects.append(citation)
        elif child.tag == g7const.PLAC:
            place, other_objects = handle_place(child, xref_handle_map)
            event.set_place_handle(place.handle)
            objects.append(place)
            objects.extend(other_objects)
        elif child.tag == g7const.DATE:
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
            # TODO handle date PHRASE, time
        elif child.tag == g7const.OBJE:
            event = util.add_media_ref_to_object(child, event, xref_handle_map)
        elif child.tag == g7const.UID:
            util.add_uid_to_object(child, event)
    return event, objects


def handle_place(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
) -> tuple[Place, list[BasicPrimaryObject]]:
    """Convert a GEDCOM place structure to a Gramps Place object.

    Args:
        structure: The GEDCOM structure containing the place data.
        xref_handle_map: A map of XREFs to Gramps handles.

    Returns:
        A Gramps Place object created from the GEDCOM structure.
    """
    place = Place()
    objects = []
    place.handle = util.make_handle()
    if structure.value:
        name = PlaceName()
        assert isinstance(
            structure.value, list
        ), "Expected place name value to be a list"
        assert (
            len(structure.value) >= 1
        ), "Expected place name value list to be non-empty"
        # The first element is the main place name
        name.set_value(structure.value[0])
        place.set_name(name)
    # TODO handle FORM
    # TODO handle entire place list
    for child in structure.children:
        if child.tag == g7const.MAP:
            lat = g7util.get_first_child_with_tag(child, g7const.LATI)
            lon = g7util.get_first_child_with_tag(child, g7const.LONG)
            if lat is not None and lon is not None:
                if not isinstance(lat.value, str) or not isinstance(lon.value, str):
                    raise ValueError("Latitude and longitude must be strings")
                place.set_latitude(lat.value)
                place.set_longitude(lon.value)
        elif child.tag == g7const.LANG and child.value:
            place.name.set_language(child.value)
        elif child.tag == g7const.TRAN:
            assert isinstance(
                child.value, list
            ), "Expected place name value to be a list"
            assert (
                len(child.value) >= 1
            ), "Expected place name value list to be non-empty"
            alt_name = PlaceName()
            alt_name.set_value(child.value[0])
            # TODO handle entire place list
            if lang := g7util.get_first_child_with_tag(child, g7const.LANG):
                alt_name.set_language(lang.value)
            place.add_alternative_name(alt_name)
        elif child.tag == g7const.SNOTE and child.pointer != g7grammar.voidptr:
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            place.add_note(note_handle)
        elif child.tag == g7const.NOTE:
            place, note = util.add_note_to_object(child, place)
            # Add the note to the list of objects to be returned
            objects.append(note)
        # TODO handle EXID
    return place, objects
