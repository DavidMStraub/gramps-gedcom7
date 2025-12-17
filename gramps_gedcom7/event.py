"""Process GEDCOM 7 event data."""

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import Attribute, AttributeType, Event, EventType, Place, PlaceName, PlaceRef, PlaceType, Url, UrlType
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation
from .settings import ImportSettings


def _map_place_type(form_type: str) -> int:
    """Map a GEDCOM FORM type string to a Gramps PlaceType.
    
    Args:
        form_type: The jurisdiction type from PLAC.FORM (e.g., "City", "County", "State")
    
    Returns:
        A Gramps PlaceType constant.
    """
    form_type_upper = form_type.upper()
    
    # Direct mappings
    if form_type_upper in ("CITY", "TOWN"):
        return PlaceType.CITY
    elif form_type_upper in ("COUNTY", "PARISH"):
        return PlaceType.COUNTY
    elif form_type_upper in ("STATE", "PROVINCE"):
        return PlaceType.STATE
    elif form_type_upper == "COUNTRY":
        return PlaceType.COUNTRY
    elif form_type_upper == "LOCALITY":
        return PlaceType.LOCALITY
    elif form_type_upper == "REGION":
        return PlaceType.REGION
    elif form_type_upper == "MUNICIPALITY":
        return PlaceType.MUNICIPALITY
    elif form_type_upper == "DISTRICT":
        return PlaceType.DISTRICT
    elif form_type_upper == "DEPARTMENT":
        return PlaceType.DEPARTMENT
    elif form_type_upper == "BOROUGH":
        return PlaceType.BOROUGH
    elif form_type_upper == "VILLAGE":
        return PlaceType.VILLAGE
    elif form_type_upper == "HAMLET":
        return PlaceType.HAMLET
    elif form_type_upper == "FARM":
        return PlaceType.FARM
    elif form_type_upper == "BUILDING":
        return PlaceType.BUILDING
    elif form_type_upper == "NEIGHBORHOOD":
        return PlaceType.NEIGHBORHOOD
    elif form_type_upper == "STREET":
        return PlaceType.STREET
    elif form_type_upper == "NUMBER":
        return PlaceType.NUMBER
    else:
        return PlaceType.UNKNOWN


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
            place_handle, other_objects = handle_place(child, xref_handle_map, settings, place_cache)
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
    settings: ImportSettings,
    place_cache: dict[tuple[tuple[str, ...], str | None], str],
) -> tuple[str, list[BasicPrimaryObject]]:
    """Convert a GEDCOM place structure to a Gramps Place object with full hierarchy.

    Args:
        structure: The GEDCOM structure containing the place data.
        xref_handle_map: A map of XREFs to Gramps handles.
        settings: Import settings.
        place_cache: Cache mapping (jurisdiction_name, parent_handle) to place_handle for deduplication.

    Returns:
        A tuple of the place handle (for the lowest jurisdiction level) and a list of all Place objects created.
    """
    if not structure.value:
        # No jurisdiction list - create empty place
        jurisdiction_list = []
    else:
        assert isinstance(structure.value, list), "Expected place value to be a list"
        jurisdiction_list = structure.value
    
    # Get the FORM (jurisdiction types) - either from PLAC.FORM or HEAD.PLAC.FORM
    form_list = None
    form_struct = g7util.get_first_child_with_tag(structure, g7const.FORM)
    if form_struct and form_struct.value:
        assert isinstance(form_struct.value, list), "Expected FORM value to be a list"
        form_list = form_struct.value
    elif settings.head_plac_form:
        form_list = settings.head_plac_form
    
    # Build hierarchy from highest (last) to lowest (first) jurisdiction
    # Create parent places first, then link children to parents
    objects = []
    parent_handle = None
    
    # Process from highest level (end of list) to lowest (beginning)
    for i in range(len(jurisdiction_list) - 1, -1, -1):
        jurisdiction_name = jurisdiction_list[i]
        
        # Build cache key: single jurisdiction name + parent handle
        cache_key = ((jurisdiction_name,), parent_handle)
        
        # Check if this place already exists
        if cache_key in place_cache:
            # Reuse existing place
            parent_handle = place_cache[cache_key]
            continue
        
        # Create new place for this jurisdiction level
        place = Place()
        place.handle = util.make_handle()
        place_cache[cache_key] = place.handle
        
        # Set the place name
        if jurisdiction_name:  # Only set name if not empty
            name = PlaceName()
            name.set_value(jurisdiction_name)
            place.set_name(name)
        
        # Set place type from FORM if available
        if form_list and i < len(form_list):
            place_type = _map_place_type(form_list[i])
            place.set_type(PlaceType(place_type))
        
        # Link to parent place if this is not the top level
        if parent_handle is not None:
            placeref = PlaceRef()
            placeref.set_reference_handle(parent_handle)
            place.add_placeref(placeref)
        
        objects.append(place)
        parent_handle = place.handle
    
    # parent_handle now contains the handle of the lowest jurisdiction (the one we return)
    # If jurisdiction_list was empty, parent_handle is None
    if not jurisdiction_list:
        # Create a minimal empty place without caching
        # Empty places are never deduplicated because different events may have
        # place structures with different properties (coordinates, notes, etc.)
        # but no jurisdiction list - these should remain separate places
        place = Place()
        place.handle = util.make_handle()
        objects.append(place)
        lowest_place = place
        lowest_place_handle = place.handle
    else:
        # The last place we created is the lowest jurisdiction
        lowest_place = objects[-1] if objects else None
        lowest_place_handle = parent_handle
    
    # Now apply additional properties only to the lowest-level place
    # (the one that will be referenced by the event)
    if lowest_place:
        for child in structure.children:
            if child.tag == g7const.MAP:
                lat = g7util.get_first_child_with_tag(child, g7const.LATI)
                lon = g7util.get_first_child_with_tag(child, g7const.LONG)
                if lat is not None and lon is not None:
                    if not isinstance(lat.value, str) or not isinstance(lon.value, str):
                        raise ValueError("Latitude and longitude must be strings")
                    lowest_place.set_latitude(lat.value)
                    lowest_place.set_longitude(lon.value)
            elif child.tag == g7const.LANG and child.value:
                lowest_place.name.set_language(child.value)
            elif child.tag == g7const.TRAN:
                assert isinstance(child.value, list), "Expected place name value to be a list"
                assert len(child.value) >= 1, "Expected place name value list to be non-empty"
                alt_name = PlaceName()
                alt_name.set_value(child.value[0])
                if lang := g7util.get_first_child_with_tag(child, g7const.LANG):
                    alt_name.set_language(lang.value)
                lowest_place.add_alternative_name(alt_name)
            elif child.tag == g7const.SNOTE and child.pointer != g7grammar.voidptr:
                try:
                    note_handle = xref_handle_map[child.pointer]
                except KeyError:
                    raise ValueError(f"Shared note {child.pointer} not found")
                lowest_place.add_note(note_handle)
            elif child.tag == g7const.NOTE:
                lowest_place, note = util.add_note_to_object(child, lowest_place)
                objects.append(note)
            elif child.tag == g7const.EXID:
                assert isinstance(child.value, str), "Expected EXID value to be a string"
                url = Url()
                url.set_type(UrlType.CUSTOM)
                type_child = next((c for c in child.children if c.tag == g7const.TYPE), None)
                if type_child and type_child.value:
                    if isinstance(type_child.value, str) and type_child.value.startswith("http"):
                        url.set_path(type_child.value)
                        url.set_description(f"External ID: {child.value}")
                    else:
                        url.set_path(child.value)
                        url.set_description(f"EXID:{child.value} (Type: {type_child.value})")
                else:
                    url.set_path(child.value)
                    url.set_description(f"External ID: {child.value}")
                lowest_place.add_url(url)
            elif child.tag == g7const.FORM:
                # Already processed above
                pass
    
    return lowest_place_handle, objects
