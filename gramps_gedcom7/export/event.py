"""Write Gramps events and places as GEDCOM structures."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gramps.gen.lib import Event, EventType, Place, PlaceType

from . import util
from .citation import add_citations
from .multimedia import add_media_refs
from .note import add_notes
from .util import ROLE_ENUMS, add

if TYPE_CHECKING:
    from gramps.gen.db import DbReadBase

    from .exporter import ExportContext

# Written under an individual record.
INDIVIDUAL_EVENT_TAGS = {
    EventType.ADOPT: g7const.ADOP,
    EventType.BAPTISM: g7const.BAPM,
    EventType.BAR_MITZVAH: g7const.BARM,
    EventType.BAS_MITZVAH: g7const.BASM,
    EventType.BIRTH: g7const.BIRT,
    EventType.BLESS: g7const.BLES,
    EventType.BURIAL: g7const.BURI,
    EventType.CENSUS: g7const.CENS,
    EventType.CHRISTEN: g7const.CHR,
    EventType.ADULT_CHRISTEN: g7const.CHRA,
    EventType.CONFIRMATION: g7const.CONF,
    EventType.CREMATION: g7const.CREM,
    EventType.DEATH: g7const.DEAT,
    EventType.EMIGRATION: g7const.EMIG,
    EventType.FIRST_COMMUN: g7const.FCOM,
    EventType.GRADUATION: g7const.GRAD,
    EventType.IMMIGRATION: g7const.IMMI,
    EventType.NATURALIZATION: g7const.NATU,
    EventType.ORDINATION: g7const.ORDN,
    EventType.PROBATE: g7const.PROB,
    EventType.RETIREMENT: g7const.RETI,
    EventType.WILL: g7const.WILL,
}

# Written under a family record.
FAMILY_EVENT_TAGS = {
    EventType.ANNULMENT: g7const.ANUL,
    EventType.CENSUS: g7const.CENS,
    EventType.DIVORCE: g7const.DIV,
    EventType.DIV_FILING: g7const.DIVF,
    EventType.ENGAGEMENT: g7const.ENGA,
    EventType.MARR_BANNS: g7const.MARB,
    EventType.MARR_CONTR: g7const.MARC,
    EventType.MARR_LIC: g7const.MARL,
    EventType.MARR_SETTL: g7const.MARS,
    EventType.MARRIAGE: g7const.MARR,
}

_LATITUDE = re.compile(g7grammar.latitude)
_LONGITUDE = re.compile(g7grammar.longitude)


def event_tag(event: Event, tags: dict[int, str]) -> tuple[str, str | None]:
    """Name the tag an event is written as, and the type to write beneath it.

    An event with no counterpart is written as the generic event structure, which
    requires a type to say what it was. A custom Gramps type gives its own name;
    a standard one with no GEDCOM tag gives its untranslated name, so that a file
    written under one locale reads the same as under another.
    """
    event_type = event.get_type()
    if not event_type.is_custom():
        tag = tags.get(int(event_type))
        if tag is not None:
            return tag, None
    return g7const.EVEN, event_type.xml_str() or "Event"


def add_coordinate(
    parent: g7types.GedcomStructure, tag: str, coordinate: str, pattern: re.Pattern[str]
) -> None:
    """Write a coordinate, which Gramps keeps as the text the user entered.

    The import leaves a coordinate in the notation it was read in, so that
    notation is written back as it stands. One entered in Gramps as a signed
    number is turned into it.
    """
    coordinate = coordinate.strip()
    if not coordinate:
        return
    if pattern.fullmatch(coordinate):
        add(parent, tag).text = coordinate
        return
    try:
        add(parent, tag, float(coordinate))
    except ValueError:
        # Neither notation, so there is no coordinate here to write.
        return


def place_jurisdictions(
    place: Place, db: DbReadBase
) -> tuple[list[str], list[str]]:
    """List a place and the places enclosing it, and what each one is.

    GEDCOM names a place by its jurisdictions from the smallest outwards, which
    is the Gramps hierarchy read from the place up through its enclosing places.
    """
    names: list[str] = []
    forms: list[str] = []
    seen: set[str] = set()
    current: Place | None = place
    while current is not None and current.handle not in seen:
        seen.add(current.handle)
        # A comma separates jurisdictions and the payload has no escape for one,
        # so a name containing a comma cannot be written as it stands.
        names.append(current.get_name().get_value().replace(",", " ").strip())
        place_type = current.get_type()
        forms.append(place_type.xml_str() if int(place_type) != PlaceType.UNKNOWN else "")
        placerefs = current.get_placeref_list()
        current = (
            db.get_place_from_handle(placerefs[0].ref)
            if placerefs and placerefs[0].ref
            else None
        )
    return names, forms


def add_place(
    parent: g7types.GedcomStructure, place: Place, db: DbReadBase
) -> g7types.GedcomStructure:
    """Write the place an event happened at.

    A place whose name is empty is still written, with an empty payload, since
    Gramps records that the event had a place and what else is known about it.
    """
    names, forms = place_jurisdictions(place, db)
    structure = add(parent, g7const.PLAC, names)
    if any(forms):
        add(structure, g7const.FORM, forms)
    if place.get_latitude() and place.get_longitude():
        map_structure = add(structure, g7const.MAP)
        add_coordinate(map_structure, g7const.LATI, place.get_latitude(), _LATITUDE)
        add_coordinate(map_structure, g7const.LONG, place.get_longitude(), _LONGITUDE)
        if len(map_structure.children) != 2:
            # Both are required, so half a pair is no pair.
            structure.children.remove(map_structure)
    return structure


def add_event(
    parent: g7types.GedcomStructure,
    event: Event,
    tags: dict[int, str],
    context: ExportContext,
    owner: str,
) -> g7types.GedcomStructure:
    """Write an event under the record it belongs to.

    Gramps events are objects of their own that any number of records may point
    at, while GEDCOM writes an event inside the record it belongs to. The record
    that owns it is decided before anything is written; the others are named here
    as associates, which is how the specification records who else took part.
    """
    tag, event_type = event_tag(event, tags)
    structure = add(parent, tag)
    if event_type is not None:
        add(structure, g7const.TYPE, event_type)
    description = event.get_description()
    if description and tag == g7const.EVEN:
        # The generic event structure's payload says what happened, which is
        # what the Gramps description holds.
        structure.text = description
        description = ""
    util.add_privacy(structure, event.get_privacy())
    util.add_date(structure, event.get_date_object())
    if event.get_place_handle():
        place = context.db.get_place_from_handle(event.get_place_handle())
        if place is not None:
            add_place(structure, place, context.db)
    if description:
        add(structure, g7const.NOTE, description)
    util.add_attributes(structure, event, context)
    add_notes(structure, event, context)
    add_media_refs(structure, event, context)
    add_citations(structure, event, context)
    for participant, role in context.participants(event.handle, owner):
        pointer = context.xrefs.get(participant)
        if pointer is None:
            continue
        associate = add(structure, g7const.ASSO, pointer=pointer)
        enum = ROLE_ENUMS.get(int(role)) if not role.is_custom() else None
        add(associate, g7const.ROLE, enum or "OTHER")
        if enum is None:
            add(associate.children[-1], g7const.PHRASE, role.xml_str() or str(role))
    return structure
