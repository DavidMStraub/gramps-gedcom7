"""Write Gramps people as GEDCOM individual records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import Name, NameType, Person, PersonRef

from . import util
from .citation import add_citations
from .event import INDIVIDUAL_EVENT_TAGS, add_event
from .multimedia import add_media_refs
from .note import add_notes
from .util import ROLE_VOCABULARY, add, add_phrase_from_notes

if TYPE_CHECKING:
    from .exporter import ExportContext

SEX_ENUMS = {
    Person.MALE: "M",
    Person.FEMALE: "F",
    Person.OTHER: "X",
    Person.UNKNOWN: "U",
}

NAME_TYPE_ENUMS = {
    NameType.AKA: "AKA",
    NameType.BIRTH: "BIRTH",
    NameType.MARRIED: "MARRIED",
}

# The whole of g7:enumset-NAME-TYPE. Gramps keeps the values it has no type of
# its own for as custom types named by the value, so one named by a value in
# here is written as that value rather than as OTHER with a phrase.
NAME_TYPE_VOCABULARY = frozenset(
    {"AKA", "BIRTH", "IMMIGRANT", "MAIDEN", "MARRIED", "PROFESSIONAL", "OTHER"}
)

# What Gramps gives a name that nobody has said anything about, and so what a
# name read from a structure with no type of its own comes back as. Writing it
# would put a type on every name in every file that never had one.
DEFAULT_NAME_TYPE = NameType.BIRTH

# The relation the import gives a person reference made from an alias, which is
# a claim that two records are the same person rather than an association.
ALIAS_RELATION = "ALIA"


def add_name_type(structure: g7types.GedcomStructure, name: str) -> None:
    """Say what kind of name this is, where Gramps holds that as free text."""
    if not name:
        return
    if name in NAME_TYPE_VOCABULARY:
        add(structure, g7const.TYPE, name)
        return
    type_structure = add(structure, g7const.TYPE, "OTHER")
    add(type_structure, g7const.PHRASE, name)


def add_name(
    parent: g7types.GedcomStructure, name: Name, context: ExportContext
) -> g7types.GedcomStructure | None:
    """Write one of a person's names, if there is a name there to write.

    The payload spells the name out with its surname marked, and the parts are
    written beneath it as well, so that a reader that parses neither the one nor
    the other still has the whole name.
    """
    surnames = name.get_surname_list()
    primary = next(
        (s for s in surnames if s.get_primary()), surnames[0] if surnames else None
    )
    given = name.get_first_name()
    surname = primary.get_surname() if primary else ""
    suffix = name.get_suffix()
    parts = (
        name.get_title(),
        name.get_nick_name(),
        primary.get_prefix() if primary else "",
    )
    if not (given or surname or suffix):
        if not any(parts):
            # An empty name is not a name, and the payload cannot be empty.
            return None
        # Nothing to spell out, but parts to write beneath: the surname markers
        # stand for the name that is not recorded.
        personal = g7types.PersonalName(fullname="//")
    elif surname:
        personal = g7types.PersonalName(
            fullname=" ".join(part for part in (given, surname, suffix) if part),
            given=given or None,
            surname=surname,
            suffix=suffix or None,
        )
    else:
        # With no surname there are no slashes to place, and the name is written
        # as it stands.
        personal = g7types.PersonalName(
            fullname=" ".join(part for part in (given, suffix) if part)
        )
    structure = add(parent, g7const.NAME, personal)

    name_type = name.get_type()
    if name_type.is_custom():
        add_name_type(structure, name_type.string)
    elif int(name_type) in NAME_TYPE_ENUMS and int(name_type) != DEFAULT_NAME_TYPE:
        add(structure, g7const.TYPE, NAME_TYPE_ENUMS[int(name_type)])

    if name.get_title():
        add(structure, g7const.NPFX, name.get_title())
    if given:
        add(structure, g7const.GIVN, given)
    if name.get_nick_name():
        add(structure, g7const.NICK, name.get_nick_name())
    if primary and primary.get_prefix():
        add(structure, g7const.SPFX, primary.get_prefix())
    if surname:
        add(structure, g7const.SURN, surname)
    if suffix:
        add(structure, g7const.NSFX, suffix)
    add_notes(structure, name, context)
    add_citations(structure, name, context)
    return structure


def add_association(
    parent: g7types.GedcomStructure, person_ref: PersonRef, context: ExportContext
) -> None:
    """Write a person's link to another person, as an alias or an association."""
    pointer = context.xrefs.get(person_ref.ref)
    if pointer is None:
        return
    relation = person_ref.get_relation() or ""
    if relation == ALIAS_RELATION:
        alias = add(parent, g7const.ALIA, pointer=pointer)
        add_phrase_from_notes(alias, person_ref, context)
        return
    associate = add(parent, g7const.ASSO, pointer=pointer)
    if relation in ROLE_VOCABULARY:
        add(associate, g7const.ROLE, relation)
    else:
        role = add(associate, g7const.ROLE, "OTHER")
        if relation:
            add(role, g7const.PHRASE, relation)
    add_notes(associate, person_ref, context)
    add_citations(associate, person_ref, context)


def person_to_record(person: Person, context: ExportContext) -> g7types.GedcomStructure:
    """Write a person as an individual record."""
    record = g7types.GedcomStructure(
        tag=g7const.INDI, xref=context.xrefs.get(person.handle)
    )
    util.add_privacy(record, person.get_privacy())

    add_name(record, person.get_primary_name(), context)
    for name in person.get_alternate_names():
        add_name(record, name, context)

    gender = SEX_ENUMS.get(person.get_gender())
    if gender is not None:
        add(record, g7const.SEX, gender)

    util.add_attributes(record, person, context)

    for event_ref in person.get_event_ref_list():
        event = context.owned_event(event_ref.ref, person.handle)
        if event is not None:
            add_event(record, event, INDIVIDUAL_EVENT_TAGS, context, person.handle)

    for handle in person.get_parent_family_handle_list():
        add(record, g7const.FAMC, pointer=context.xrefs.pointer(handle))
    for handle in person.get_family_handle_list():
        add(record, g7const.FAMS, pointer=context.xrefs.pointer(handle))

    for person_ref in person.get_person_ref_list():
        add_association(record, person_ref, context)

    add_notes(record, person, context)
    add_media_refs(record, person, context)
    add_citations(record, person, context)
    util.add_change_date(record, person.change)
    return record
