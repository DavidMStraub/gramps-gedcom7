"""Helpers shared by the export modules."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import gedcom7
from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import (
    Attribute,
    AttributeType,
    Date,
    EventRoleType,
    SrcAttribute,
)

if TYPE_CHECKING:
    from .exporter import ExportContext

GEDCOM_MONTHS = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)  # fmt: skip

# The calendars whose month numbering the month names above describe, and what
# GEDCOM calls each. Gramps numbers its months while GEDCOM names them, and the
# names differ per calendar, so a date in any other calendar cannot yet be
# written month and all: see date_to_date_value for what becomes of one.
CALENDAR_MAP = {
    Date.CAL_GREGORIAN: None,
    Date.CAL_JULIAN: "JULIAN",
}

# Calendars GEDCOM names but whose months these tables cannot, so that a date in
# one can at least be written as the year it names, in the calendar that names it.
UNNAMED_MONTH_CALENDARS = {
    Date.CAL_HEBREW: "HEBREW",
    Date.CAL_FRENCH: "FRENCH_R",
}

# The inverse of util.GEDCOM_ATTRIBUTE_MAP, by which the import parks a GEDCOM
# attribute in a Gramps one. Standard types are keyed by their number, since the
# name of a standard type is translated and this one is not the English one.
STANDARD_ATTRIBUTE_TAGS = {
    AttributeType.CASTE: g7const.CAST,
    AttributeType.DESCRIPTION: g7const.DSCR,
    AttributeType.ID: g7const.IDNO,
    AttributeType.NATIONAL: g7const.NATI,
    AttributeType.NUM_CHILD: g7const.NCHI,
    AttributeType.SSN: g7const.SSN,
    AttributeType.OCCUPATION: g7const.OCCU,
    AttributeType.AGENCY: g7const.AGNC,
    AttributeType.CAUSE: g7const.CAUS,
}

# Custom attributes the import creates, whose name is the only record of which
# structure they came from.
CUSTOM_ATTRIBUTE_TAGS = {
    "Education": g7const.EDUC,
    "Property": g7const.PROP,
    "Religion": g7const.RELI,
    "Title": g7const.TITL,
    "Number of Marriages": g7const.NMR,
    "Residence": g7const.RESI,
    "Fact": g7const.FACT,
    "Phone": g7const.PHON,
    "Email": g7const.EMAIL,
    "Fax": g7const.FAX,
    "Website": g7const.WWW,
}

# Carried by the import on a media reference and on a date, and written back
# where those are written rather than as an attribute in their own right.
ATTRIBUTES_WRITTEN_ELSEWHERE = ("OBJE:TITL", "Time")

# What the specification calls someone taking part in something. The whole
# vocabulary, and what each Gramps role among them is called, one serving both
# the people at an event and the people a person is associated with.
ROLE_VOCABULARY = frozenset(
    {
        "CHIL", "CLERGY", "FATH", "FRIEND", "GODP", "HUSB", "MOTH", "MULTIPLE",
        "NGHBR", "OFFICIATOR", "PARENT", "SPOU", "WIFE", "WITN", "OTHER",
    }
)  # fmt: skip

ROLE_ENUMS = {
    EventRoleType.CLERGY: "CLERGY",
    EventRoleType.CELEBRANT: "OFFICIATOR",
    EventRoleType.OFFICIATOR: "OFFICIATOR",
    EventRoleType.WITNESS: "WITN",
    EventRoleType.GODPARENT: "GODP",
    EventRoleType.FATHER: "FATH",
    EventRoleType.MOTHER: "MOTH",
    EventRoleType.BRIDE: "WIFE",
    EventRoleType.GROOM: "HUSB",
    EventRoleType.CHILD: "CHIL",
    EventRoleType.PARENT: "PARENT",
    EventRoleType.FRIEND: "FRIEND",
    EventRoleType.NEIGHBOR: "NGHBR",
    EventRoleType.MULTIPLE: "MULTIPLE",
}

assert set(ROLE_ENUMS.values()) <= ROLE_VOCABULARY


def add(
    parent: g7types.GedcomStructure,
    tag: str,
    value: g7types.DataType | None = None,
    *,
    pointer: str | None = None,
) -> g7types.GedcomStructure:
    """Add a substructure to a structure, and return it.

    The value is formatted for whichever structure type the tag denotes under
    this superstructure, so the structure is attached before it is set.
    """
    child = g7types.GedcomStructure(tag=tag, pointer=pointer)
    parent.append_child(child)
    if value is not None:
        gedcom7.set_value(child, value)
    return child


def add_phrase_from_notes(
    parent: g7types.GedcomStructure, obj: object, context: ExportContext
) -> None:
    """Carry an object's notes in the phrase beside a pointer.

    A pointer such as ALIA or CHIL has nowhere to carry a note, which is why the
    import reads the phrase beside it into one. Only one phrase may stand there,
    so several notes are joined into it: writing the first and leaving the rest
    would make them records that nothing points at.
    """
    texts = []
    for handle in obj.get_note_list():  # type: ignore[attr-defined]
        note = context.db.get_note_from_handle(handle)
        if note is not None and note.get():
            texts.append(note.get())
            context.written_notes.add(handle)
    if texts:
        add(parent, g7const.PHRASE, "\n\n".join(texts))


def allows(structure: g7types.GedcomStructure, tag: str) -> bool:
    """Say whether a structure may contain a substructure with this tag."""
    type_id = structure.type_id
    if type_id is None:
        return False
    return tag in g7const.substructures.get(type_id, {})


def _gedcom_date(
    day: int, month: int, year: int, calendar: str | None, year_only: bool = False
) -> g7types.Date | None:
    """Build a date from the numbers Gramps keeps it in, if it can be written.

    A GEDCOM date needs a year, and names a day only within a month, so the
    parts below the first one Gramps leaves at zero are dropped.
    """
    if year == 0:
        return None
    month_name = (
        None if year_only or not 1 <= month <= 12 else GEDCOM_MONTHS[month - 1]
    )
    return g7types.Date(
        calendar=calendar,
        # A year before the common era is negative in Gramps and positive with
        # an epoch here.
        year=abs(year),
        epoch="BCE" if year < 0 else None,
        month=month_name,
        day=day if day and month_name else None,
    )


def _in_a_calendar_that_can_be_written(
    date: Date,
) -> tuple[Date, str | None, bool] | None:
    """Put a date in a calendar it can be written in, and say how much of it.

    A calendar whose months these tables cannot name is converted to Gregorian,
    which says the same day by another name. Converting needs a month to convert,
    though, and Gramps takes a date with none as the first of the year, so an
    incomplete date is left in its own calendar and written as its year alone --
    or, where GEDCOM has no name for that calendar either, not written at all.
    """
    calendar = date.get_calendar()
    if calendar in CALENDAR_MAP:
        return date, CALENDAR_MAP[calendar], False
    _, month, _, _ = date.get_start_date()
    if month:
        converted = date.to_calendar("gregorian")
        return converted, CALENDAR_MAP.get(converted.get_calendar()), False
    if calendar in UNNAMED_MONTH_CALENDARS:
        return date, UNNAMED_MONTH_CALENDARS[calendar], True
    return None


def date_to_date_value(date: Date | None) -> g7types.DateValue | None:
    """Convert a Gramps date to the date value that denotes the same thing.

    Returns None for a date that cannot be written: an empty one, one Gramps
    holds only as text, and one whose year is unknown, none of which has a
    payload in GEDCOM. The text of such a date survives as the DATE.PHRASE that
    :func:`add_date` writes beside it.
    """
    if date is None or date.is_empty() or date.get_modifier() == Date.MOD_TEXTONLY:
        return None

    resolved = _in_a_calendar_that_can_be_written(date)
    if resolved is None:
        return None
    date, name, year_only = resolved

    start_day, start_month, start_year, _ = date.get_start_date()
    start = _gedcom_date(start_day, start_month, start_year, name, year_only)
    if start is None:
        return None
    stop_day, stop_month, stop_year, _ = date.get_stop_date()
    stop = _gedcom_date(stop_day, stop_month, stop_year, name, year_only)

    modifier = date.get_modifier()
    if modifier == Date.MOD_RANGE and stop is not None:
        return g7types.DateRange(start=start, end=stop)
    if modifier == Date.MOD_SPAN and stop is not None:
        return g7types.DatePeriod(from_=start, to=stop)
    if modifier == Date.MOD_BEFORE:
        return g7types.DateRange(end=start)
    if modifier == Date.MOD_AFTER:
        return g7types.DateRange(start=start)
    if modifier == Date.MOD_FROM:
        return g7types.DatePeriod(from_=start)
    if modifier == Date.MOD_TO:
        return g7types.DatePeriod(to=start)

    # A qualifier applies to a single date, so a quality on a range or a period
    # is dropped above rather than written of one end of it.
    quality = date.get_quality()
    if quality == Date.QUAL_CALCULATED:
        return g7types.DateApprox(date=start, approx="CAL")
    if quality == Date.QUAL_ESTIMATED:
        return g7types.DateApprox(date=start, approx="EST")
    if modifier == Date.MOD_ABOUT:
        return g7types.DateApprox(date=start, approx="ABT")
    return start


def add_date(
    parent: g7types.GedcomStructure, date: Date | None
) -> g7types.GedcomStructure | None:
    """Write a date under a structure, with its text as a phrase beside it.

    A date Gramps holds only as text still gets a DATE structure, with an empty
    payload and the text in its phrase, which is how the specification carries a
    date that its own grammar cannot express.
    """
    if date is None or date.is_empty():
        return None
    value = date_to_date_value(date)
    text = date.get_text()
    if value is None and not text:
        return None
    structure = add(parent, g7const.DATE, value)
    if text:
        add(structure, g7const.PHRASE, text)
    return structure


def add_change_date(parent: g7types.GedcomStructure, change: int) -> None:
    """Write when the object was last changed, as a date and a time in UTC."""
    if not change:
        return
    moment = datetime.datetime.fromtimestamp(change, tz=datetime.timezone.utc)
    chan = add(parent, g7const.CHAN)
    date = add(
        chan,
        g7const.DATE,
        g7types.DateExact(
            day=moment.day, month=GEDCOM_MONTHS[moment.month - 1], year=moment.year
        ),
    )
    add(
        date,
        g7const.TIME,
        g7types.Time(
            hour=moment.hour, minute=moment.minute, second=moment.second, tz="Z"
        ),
    )


def add_privacy(parent: g7types.GedcomStructure, private: bool) -> None:
    """Write the restriction that Gramps records as an object being private."""
    if private:
        add(parent, g7const.RESN, ["CONFIDENTIAL"])


def _attribute_structure(
    attribute: Attribute | SrcAttribute,
) -> tuple[str, str, str | None] | None:
    """Name the tag, payload and type an attribute is written as, if any.

    Returns None for an attribute that belongs to something else being written,
    or that this does not know how to place.
    """
    attribute_type = attribute.get_type()
    value = attribute.get_value() or ""
    if attribute_type.is_custom():
        name = attribute_type.string
        if name in ATTRIBUTES_WRITTEN_ELSEWHERE:
            return None
        if name in CUSTOM_ATTRIBUTE_TAGS:
            return CUSTOM_ATTRIBUTE_TAGS[name], value, None
        if name == "UID":
            return g7const.UID, value, None
        # The import spells an identifier's type into the attribute's name,
        # after a colon, and leaves the value alone.
        base, _, identifier_type = name.partition(":")
        if base in (g7const.EXID, g7const.REFN):
            return base, value, identifier_type or None
        # Anything else came from a structure this does not recognize, or from
        # Gramps itself, and a fact named for it says as much without inventing
        # an extension tag.
        return g7const.FACT, value, name
    tag = STANDARD_ATTRIBUTE_TAGS.get(int(attribute_type))
    return None if tag is None else (tag, value, None)


def add_attributes(
    parent: g7types.GedcomStructure, obj: object, context: ExportContext
) -> None:
    """Write an object's attributes, recording those with nowhere to go.

    An attribute is written only where its superstructure may contain it, so
    that what is left over is reported rather than making the file unreadable.

    Gramps holds every attribute value as text, and so does all but one of the
    structures they are written to, so the payload is set as it stands rather
    than formatted from a typed value. Where it does not conform -- a count of
    children that is not a number -- validation reports it.
    """
    for attribute in obj.get_attribute_list():  # type: ignore[attr-defined]
        placed = _attribute_structure(attribute)
        if placed is None:
            continue
        tag, value, identifier_type = placed
        if not allows(parent, tag):
            context.skipped_attributes.append(attribute)
            continue
        structure = add(parent, tag)
        structure.text = value
        if identifier_type is not None and allows(structure, g7const.TYPE):
            add(structure, g7const.TYPE, identifier_type)
