"""Process GEDCOM 7 event data."""

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import Attribute, AttributeType, Event, EventType, Place, PlaceName, Url, UrlType
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation
from .settings import ImportSettings


def handle_event(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    event_type_map: dict[str, int],
    settings: ImportSettings,
    place_cache: dict[tuple[tuple[str, ...], str | None], str],
) -> tuple[Event, list[BasicPrimaryObject]]:
    """Convert a GEDCOM event structure to a Gramps Event object.

    Args:
        structure: The GEDCOM structure containing the event data.
        xref_handle_map: A map of XREFs to Gramps handles.
        event_type_map: A mapping of GEDCOM event tags to Gramps EventType values.
        settings: Import settings.
        place_cache: Cache mapping place jurisdictions to handles for deduplication.

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
            util.add_attribute_to_object(event, "Phone", child.value)
        elif child.tag == g7const.EMAIL:
            assert isinstance(child.value, str), "Expected value to be a string"
            util.add_attribute_to_object(event, "Email", child.value)
        elif child.tag == g7const.FAX:
            assert isinstance(child.value, str), "Expected value to be a string"
            util.add_attribute_to_object(event, "Fax", child.value)
        elif child.tag == g7const.WWW:
            assert isinstance(child.value, str), "Expected value to be a string"
            util.add_attribute_to_object(event, "Website", child.value)
        # TODO handle association
        # TODO handle address
        elif child.tag == g7const.AGNC:
            assert isinstance(child.value, str), "Expected AGNC value to be a string"
            util.add_attribute_to_object(event, AttributeType.AGENCY, child.value)
        elif child.tag == g7const.RELI:
            assert isinstance(child.value, str), "Expected RELI value to be a string"
            util.add_attribute_to_object(event, "Religion", child.value)
        elif child.tag == g7const.CAUS:
            assert isinstance(child.value, str), "Expected CAUS value to be a string"
            util.add_attribute_to_object(event, AttributeType.CAUSE, child.value)
        elif child.tag == g7const.SNOTE and child.pointer != g7grammar.voidptr:
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            event.add_note(note_handle)
        elif child.tag == g7const.NOTE:
            event, note = util.add_note_to_object(child, event)
            objects.append(note)
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
            place_handle, other_objects = handle_place(child, xref_handle_map, place_cache, settings)
            event.set_place_handle(place_handle)
            objects.extend(other_objects)  # other_objects contains place only if it's new
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
            # Handle PHRASE substructure
            phrase_structure = g7util.get_first_child_with_tag(child, g7const.PHRASE)
            if phrase_structure and phrase_structure.value:
                assert isinstance(
                    phrase_structure.value, str
                ), "Expected PHRASE value to be a string"
                date.set_text_value(phrase_structure.value)
            event.set_date_object(date)
            # Handle TIME substructure
            time_structure = g7util.get_first_child_with_tag(child, g7const.TIME)
            if time_structure and time_structure.value:
                assert isinstance(
                    time_structure.value, g7types.Time
                ), "Expected TIME value to be a Time object"
                time_obj = time_structure.value
                # Format time as HH:MM:SS[.fraction][Z]
                # Handle None values by using 0 as default
                hour = time_obj.hour if time_obj.hour is not None else 0
                minute = time_obj.minute if time_obj.minute is not None else 0
                second = time_obj.second if time_obj.second is not None else 0
                time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
                if time_obj.fraction is not None:
                    time_str += f".{time_obj.fraction}"
                if time_obj.tz:
                    time_str += time_obj.tz
                util.add_attribute_to_object(event, "Time", time_str)
        elif child.tag == g7const.OBJE:
            event = util.add_media_ref_to_object(child, event, xref_handle_map)
        elif child.tag == g7const.UID:
            util.add_uid_to_object(child, event)
    return event, objects


def handle_place(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    place_cache: dict[tuple[tuple[str, ...], str | None], str],
    settings: ImportSettings,
) -> tuple[str, list[BasicPrimaryObject]]:
    """Convert a GEDCOM place structure to a Gramps Place object.

    Args:
        structure: The GEDCOM structure containing the place data.
        xref_handle_map: A map of XREFs to Gramps handles.
        place_cache: Cache mapping place jurisdictions to handles for deduplication.
        settings: Import settings.

    Returns:
        A tuple of the place handle and a list of additional objects created.
    """
    # Build cache key from jurisdiction list
    # Use full jurisdiction list for proper deduplication
    jurisdiction_tuple = tuple(structure.value) if structure.value else ()
    parent_handle = None  # Will be used for hierarchy later
    cache_key = (jurisdiction_tuple, parent_handle)
    
    # Check if this place already exists in cache
    if cache_key in place_cache:
        # Reuse existing place - just return the handle
        # The corresponding Place object was already created earlier and scheduled for database insertion
        existing_handle = place_cache[cache_key]
        # Return empty objects list to avoid adding a duplicate Place to the pending objects list
        return existing_handle, []
    
    # Create new place
    place = Place()
    objects = []
    place.handle = util.make_handle()
    
    # Add to cache
    place_cache[cache_key] = place.handle
    
    # Add the new place to objects list so it gets added to database
    objects.append(place)
    
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
        elif child.tag == g7const.EXID:
            assert isinstance(child.value, str), "Expected EXID value to be a string"
            url = Url()
            url.set_type(UrlType.CUSTOM)
            # Check for TYPE substructure
            type_child = next((c for c in child.children if c.tag == g7const.TYPE), None)
            if type_child and type_child.value:
                # If TYPE contains a URL, use it as the path
                if isinstance(type_child.value, str) and type_child.value.startswith("http"):
                    url.set_path(type_child.value)
                    url.set_description(f"External ID: {child.value}")
                else:
                    # TYPE is present but not a URL, store both in description
                    url.set_path(child.value)
                    url.set_description(f"EXID:{child.value} (Type: {type_child.value})")
            else:
                # No TYPE substructure, just store the EXID value
                url.set_path(child.value)
                url.set_description(f"External ID: {child.value}")
            place.add_url(url)
    
    return place.handle, objects
