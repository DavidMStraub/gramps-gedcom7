"""Utility functions for handling GEDCOM 7 data in Gramps."""

from __future__ import annotations

import uuid

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import (
    Date,
    Note,
    NoteType,
    MediaRef,
    Attribute,
    SrcAttribute,
    SrcAttributeType,
    AttributeType,
)

from .types import (
    BasicPrimaryObject,
    BasicPrimaryObjectT,
    MediaBaseT,
    NoteBaseT,
    AttributeBase,
    SrcAttributeBase,
)


# Mapping of GEDCOM 7 attribute tags to Gramps AttributeType
# For standard attributes, we use the predefined AttributeType constants
# For attributes not in Gramps (EDUC, PROP, RELI, TITL, NMR), we use CUSTOM with the tag name
GEDCOM_ATTRIBUTE_MAP = {
    g7const.CAST: AttributeType.CASTE,
    g7const.DSCR: AttributeType.DESCRIPTION,
    g7const.IDNO: AttributeType.ID,
    g7const.NATI: AttributeType.NATIONAL,
    g7const.NCHI: AttributeType.NUM_CHILD,
    g7const.SSN: AttributeType.SSN,
    g7const.OCCU: AttributeType.OCCUPATION,
    # These don't have direct Gramps equivalents, use CUSTOM
    g7const.EDUC: (AttributeType.CUSTOM, "Education"),
    g7const.PROP: (AttributeType.CUSTOM, "Property"),
    g7const.RELI: (AttributeType.CUSTOM, "Religion"),
    g7const.TITL: (AttributeType.CUSTOM, "Title"),
    g7const.NMR: (AttributeType.CUSTOM, "Number of Marriages"),
    g7const.RESI: (AttributeType.CUSTOM, "Residence"),
    g7const.FACT: (AttributeType.CUSTOM, "Fact"),
}


def make_handle() -> str:
    """Generate a unique handle for a new object."""
    return uuid.uuid4().hex


def add_ids(
    obj: BasicPrimaryObjectT,
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
) -> BasicPrimaryObjectT:
    """Add a handle and Gramps ID to a new Gramps object."""
    if not structure.xref or len(structure.xref) < 3:
        raise ValueError(f"Invalid xref ID: {structure.xref}")
    if structure.xref not in xref_handle_map:
        raise ValueError(f"Xref ID {structure.xref} not found in xref_handle_map")
    obj.handle = xref_handle_map[structure.xref]
    obj.gramps_id = structure.xref[1:-1]
    return obj


GEDCOM_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

# map from GEDCOM date approx qualifiers to Gramps date quality and modifier
DATE_QUALITY_MODIFIER_MAP = {
    "ABT": (Date.QUAL_NONE, Date.MOD_ABOUT),
    "CAL": (Date.QUAL_CALCULATED, Date.MOD_NONE),
    "EST": (Date.QUAL_ESTIMATED, Date.MOD_NONE),
}


def set_change_date(
    structure: g7types.GedcomStructure,
    obj: BasicPrimaryObjectT,
) -> BasicPrimaryObjectT:
    """Set the change date for a Gramps object."""
    change_structure = g7util.get_first_child_with_tag(structure, g7const.CHAN)
    if not change_structure:
        # take creation date as fallback
        change_structure = g7util.get_first_child_with_tag(structure, g7const.CREA)
    if not change_structure:
        # no date found
        return obj
    date_structure = g7util.get_first_child_with_tag(change_structure, g7const.DATE)
    if not date_structure:
        # no date found
        return obj
    assert isinstance(
        date_structure.value, g7types.DateExact
    ), "Expected date to be a DateExact object"
    time_structure = g7util.get_first_child_with_tag(change_structure, g7const.TIME)
    if time_structure:
        assert isinstance(
            time_structure.value, g7types.Time
        ), "Expected time to be a Time object"
        time = time_structure.value
    else:
        time = None
    datetime_value = g7util.date_exact_and_time_to_python_datetime(
        date=date_structure.value,
        time=time,
    )
    obj.change = int(datetime_value.timestamp())
    return obj


def structure_to_note(structure: g7types.GedcomStructure) -> Note:
    """Create a note from a GEDCOM structure of type NOTE or SNOTE.

    Args:
        structure: The GEDCOM note structure to handle.

    Returns:
        A note object.
    """
    note = Note()
    if structure.value is not None:
        assert isinstance(structure.value, str), "Expected value to be a string"
        note.set(structure.value)
    for child in structure.children:
        # set note type to HTML if MIME type is HTML
        if child.tag == g7const.MIME:
            if child.value == g7const.MIME_HTML:
                note.type = NoteType(NoteType.HTML_CODE)
        elif child.tag == g7const.TRAN:
            # iterate over translations - we just append them
            if child.value is None:
                continue
            assert isinstance(child.value, str), "Expected value to be a string"
            note.append("\n\n" + child.value)
        # TODO handle identifier
        # TODO handle source citation
    return note


def add_note_to_object(
    structure: g7types.GedcomStructure,
    obj: NoteBaseT,
) -> tuple[NoteBaseT, Note]:
    """Add a note to a Gramps object."""
    note = structure_to_note(structure)
    note.type = NoteType(NoteType.SOURCE)
    note.handle = make_handle()
    # set note change date to parent change date
    set_change_date(structure=structure, obj=note)
    obj.add_note(note.handle)
    return obj, note


def get_next_gramps_id(
    xref_handle_map: dict[str, str],
    prefix: str,
) -> str:
    """Get the next available Gramps ID for a given prefix."""
    existing_ids = {handle[1:-1] for handle in xref_handle_map.values()}
    next_id = 1
    while f"{prefix}{next_id:04d}" in existing_ids:
        next_id += 1
    return f"{prefix}{next_id:04d}"


CALENDAR_MAP = {
    "GREGORIAN": Date.CAL_GREGORIAN,
    "JULIAN": Date.CAL_JULIAN,
    "HEBREW": Date.CAL_HEBREW,
    "FRENCH_R": Date.CAL_FRENCH,
}


def gedcom_date_to_numeric_year_month_day(
    date_value: g7types.Date,
) -> dict[str, int]:
    """Convert a GEDCOM date to a numeric year, month, and day."""
    year = date_value.year or 0
    month = GEDCOM_MONTHS.get(date_value.month or "", 0)
    day = date_value.day or 0
    return {"year": year, "month": month, "day": day}


def gedcom_date_value_to_gramps_date(
    date_value: g7types.DateValue,
) -> Date:
    """Convert a GEDCOM date value to a Gramps date."""
    date = Date()
    if isinstance(date_value, g7types.Date):
        date.set_yr_mon_day(**gedcom_date_to_numeric_year_month_day(date_value))
        if date_value.calendar is not None and date_value.calendar in CALENDAR_MAP:
            date.set_calendar(CALENDAR_MAP[date_value.calendar])
    elif isinstance(date_value, g7types.DatePeriod):
        if date_value.from_ and date_value.to:
            date.set_modifier(Date.MOD_SPAN)
            date.set_yr_mon_day(
                **gedcom_date_to_numeric_year_month_day(date_value.from_),
                remove_stop_date=False,
            )
            date.set2_yr_mon_day(**gedcom_date_to_numeric_year_month_day(date_value.to))
            if date_value.from_.calendar and date_value.to.calendar:
                if date_value.from_.calendar == date_value.to.calendar:
                    if date_value.from_.calendar in CALENDAR_MAP:
                        date.set_calendar(CALENDAR_MAP[date_value.from_.calendar])
                else:
                    # TODO handle mixed calendars
                    raise NotImplementedError(
                        "Mixed calendars in date period are not yet implemented"
                    )
        elif date_value.from_:
            date.set_modifier(Date.MOD_FROM)
            date.set_yr_mon_day(
                **gedcom_date_to_numeric_year_month_day(date_value.from_)
            )
            if (
                date_value.from_.calendar is not None
                and date_value.from_.calendar in CALENDAR_MAP
            ):
                date.set_calendar(CALENDAR_MAP[date_value.from_.calendar])
        elif date_value.to:
            date.set_modifier(Date.MOD_TO)
            date.set_yr_mon_day(**gedcom_date_to_numeric_year_month_day(date_value.to))
            if (
                date_value.to.calendar is not None
                and date_value.to.calendar in CALENDAR_MAP
            ):
                date.set_calendar(CALENDAR_MAP[date_value.to.calendar])
    elif isinstance(date_value, g7types.DateApprox):
        date.set_yr_mon_day(**gedcom_date_to_numeric_year_month_day(date_value.date))
        if (
            date_value.date.calendar is not None
            and date_value.date.calendar in CALENDAR_MAP
        ):
            date.set_calendar(CALENDAR_MAP[date_value.date.calendar])
        if date_value.approx is not None:
            quality, modifier = DATE_QUALITY_MODIFIER_MAP.get(
                date_value.approx, (Date.QUAL_NONE, Date.MOD_NONE)
            )
            date.set_quality(quality)
            date.set_modifier(modifier)
    elif isinstance(date_value, g7types.DateRange):
        if date_value.start and date_value.end:
            date.set_modifier(Date.MOD_RANGE)
            date.set_yr_mon_day(
                **gedcom_date_to_numeric_year_month_day(date_value.start),
                remove_stop_date=False,
            )
            date.set2_yr_mon_day(
                **gedcom_date_to_numeric_year_month_day(date_value.end)
            )
            if date_value.start.calendar and date_value.end.calendar:
                if date_value.start.calendar == date_value.end.calendar:
                    if date_value.start.calendar in CALENDAR_MAP:
                        date.set_calendar(CALENDAR_MAP[date_value.start.calendar])
                else:
                    # TODO handle mixed calendars
                    raise NotImplementedError(
                        "Mixed calendars in date range are not yet implemented"
                    )
        elif date_value.start:
            date.set_modifier(Date.MOD_AFTER)
            date.set_yr_mon_day(
                **gedcom_date_to_numeric_year_month_day(date_value.start)
            )
            if (
                date_value.start.calendar is not None
                and date_value.start.calendar in CALENDAR_MAP
            ):
                date.set_calendar(CALENDAR_MAP[date_value.start.calendar])
        elif date_value.end:
            date.set_modifier(Date.MOD_BEFORE)
            date.set_yr_mon_day(**gedcom_date_to_numeric_year_month_day(date_value.end))
            if (
                date_value.end.calendar is not None
                and date_value.end.calendar in CALENDAR_MAP
            ):
                date.set_calendar(CALENDAR_MAP[date_value.end.calendar])
    return date


def set_privacy_on_object(
    resn_structure: g7types.GedcomStructure, obj: BasicPrimaryObject
) -> None:
    """Set the privacy on a Gramps object based on a RESN structure."""
    assert resn_structure.tag == g7const.RESN, "Not a RESN structure"
    value = resn_structure.value
    if value is None or value == "":
        obj.set_privacy(False)
        return
    assert isinstance(value, list), "Expected RESN value to be a list"
    if "CONFIDENTIAL" in value or "PRIVACY" in value:
        obj.set_privacy(True)
    else:
        obj.set_privacy(False)


def add_media_ref_to_object(
    multimedia_link_structure: g7types.GedcomStructure,
    obj: MediaBaseT,
    xref_handle_map: dict[str, str],
) -> MediaBaseT:
    """Add a media reference to a Gramps object."""
    pointer = multimedia_link_structure.pointer
    if pointer == g7grammar.voidptr:
        # no media reference, return the object as is
        return obj
    media_ref = MediaRef()
    media_handle = xref_handle_map.get(pointer)
    if not media_handle:
        raise ValueError(f"Multimedia object {pointer} not found")
    media_ref.ref = media_handle
    
    # Handle TITL substructure - title that overrides the media object's title
    title_structure = g7util.get_first_child_with_tag(multimedia_link_structure, g7const.TITL)
    if title_structure and title_structure.value:
        assert isinstance(title_structure.value, str), "Expected TITL value to be a string"
        add_attribute_to_object(media_ref, "OBJE:TITL", title_structure.value)
    
    # TODO implement CROP
    # one complication is that GEDCOM uses pixels, Gramps uses fractions.
    # Consequently, image dimensions need to be known to convert.
    
    obj.add_media_reference(media_ref)
    return obj


def add_attribute_to_object(
    obj: AttributeBase | SrcAttributeBase,
    attr_type: str | int | tuple[int, str] | AttributeType | SrcAttributeType,
    value: str,
) -> None:
    """Add an attribute to a Gramps object.
    
    Args:
        obj: The object to add the attribute to (must support add_attribute).
        attr_type: The attribute type (string, int enum value, tuple for custom types, or Type object).
        value: The attribute value.
    """
    if isinstance(obj, SrcAttributeBase):
        attr = SrcAttribute()
        if isinstance(attr_type, str):
            attr.set_type(SrcAttributeType(attr_type))
        elif isinstance(attr_type, int):
            attr.set_type(SrcAttributeType(attr_type))
        elif isinstance(attr_type, tuple):
            attr.set_type(attr_type)
        else:
            attr.set_type(attr_type)
    elif isinstance(obj, AttributeBase):
        attr = Attribute()
        if isinstance(attr_type, str):
            attr.set_type(AttributeType(attr_type))
        elif isinstance(attr_type, int):
            attr.set_type(AttributeType(attr_type))
        elif isinstance(attr_type, tuple):
            attr.set_type(attr_type)
        else:
            attr.set_type(attr_type)
    else:
        raise TypeError(
            f"Object must be an AttributeBase or SrcAttributeBase, got {type(obj)}"
        )
    
    attr.set_value(value)
    obj.add_attribute(attr)


def handle_attribute_structure(
    structure: g7types.GedcomStructure,
    obj: AttributeBase,
) -> None:
    """Handle a GEDCOM 7 attribute structure and add it to a Gramps object.
    
    Args:
        structure: The GEDCOM attribute structure (CAST, DSCR, EDUC, etc.)
        obj: The Gramps object to add the attribute to.
    """
    if structure.tag not in GEDCOM_ATTRIBUTE_MAP:
        # Unknown attribute, add as custom
        add_attribute_to_object(obj, (AttributeType.CUSTOM, structure.tag), str(structure.value or ""))
        return
    
    attr_type = GEDCOM_ATTRIBUTE_MAP[structure.tag]
    value = structure.value or ""
    
    # Handle TYPE substructure for FACT and IDNO (required) and others (optional)
    # For FACT and IDNO, TYPE specifies what kind of fact/ID it is
    # For others, TYPE provides additional context but we keep the standard type
    type_structure = g7util.get_first_child_with_tag(structure, g7const.TYPE)
    if type_structure and type_structure.value and structure.tag in (g7const.FACT, g7const.IDNO):
        # For FACT and IDNO, use TYPE value as the custom attribute name
        type_value = type_structure.value
        attr_type = (AttributeType.CUSTOM, str(type_value))
    
    add_attribute_to_object(obj, attr_type, str(value))


def add_uid_to_object(
    structure: g7types.GedcomStructure,
    obj: AttributeBase | SrcAttributeBase,
) -> None:
    """Add a unique ID to a Gramps object."""
    assert structure.tag == g7const.UID, "Not a UID structure"
    assert isinstance(structure.value, str), "Expected UID value to be a string"
    add_attribute_to_object(obj, "UID", structure.value)


def handle_external_id(
    structure: g7types.GedcomStructure,
    obj: AttributeBase | SrcAttributeBase,
) -> None:
    """Add an external ID (EXID or REFN) to a Gramps object.

    Args:
        structure: The GEDCOM structure containing EXID or REFN tag.
        obj: The Gramps object to add the attribute to.
    """
    assert structure.tag in (g7const.EXID, g7const.REFN), (
        f"Expected EXID or REFN tag, got {structure.tag}"
    )
    assert isinstance(
        structure.value, str
    ), f"Expected {structure.tag} value to be a string"

    # Determine the base type from tag
    base_type = "EXID" if structure.tag == g7const.EXID else "REFN"

    # Check for TYPE substructure
    type_child = next(
        (c for c in structure.children if c.tag == g7const.TYPE), None
    )

    # Build the attribute type string
    if type_child and type_child.value:
        # Include TYPE value in the type string
        type_string = f"{base_type}:{type_child.value}"
    else:
        # Just use the base type
        type_string = base_type

    # Create and add the attribute with clean value (no prefixes)
    add_attribute_to_object(obj, type_string, structure.value)
