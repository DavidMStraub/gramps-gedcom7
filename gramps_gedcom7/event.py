"""Process GEDCOM 7 event data."""

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import Event, EventType, Place, PlaceName
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util


def handle_event(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    event_type_map: dict[str, int],
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
        if child.tag == g7const.RESN:
            util.set_privacy_on_object(resn_structure=child, obj=event)
        # TODO handle association
        # TODO handle UID
        # TODO handle address
        # TODO handle PHON, EMAIL, FAX, WWW, AGNC, RELI, CAUS
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
        # TODO handle source citation
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
        name.set_value(structure.value)
        place.set_name(name)
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
            alt_name = PlaceName()
            alt_name.set_value(child.value)
            if lang := g7util.get_first_child_with_tag(child, g7const.LANG):
                alt_name.set_language(lang.value)
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
