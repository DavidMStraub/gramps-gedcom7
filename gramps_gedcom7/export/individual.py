"""Write Gramps people as GEDCOM individual records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import ChildRefType, Name, NameType, Person, PersonRef

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

PEDIGREE_ENUMS = {
    ChildRefType.ADOPTED: "ADOPTED",
    ChildRefType.BIRTH: "BIRTH",
    ChildRefType.FOSTER: "FOSTER",
}

# The whole of g7:enumset-PEDI, a custom relation named by one of which is
# written as that value.
PEDIGREE_VOCABULARY = frozenset({"ADOPTED", "BIRTH", "FOSTER", "SEALING", "OTHER"})

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
    # The slash delimits the surname in the payload, which has no way to spell
    # one that belongs to a name. It becomes a space there, so the words on
    # either side stay apart, and the parts beneath keep the name as written.
    payload_given, payload_surname, payload_suffix = (
        " ".join(part.replace("/", " ").split()) if "/" in part else part
        for part in (given, surname, suffix)
    )
    if not (payload_given or payload_surname or payload_suffix):
        if not (any(parts) or given or surname or suffix):
            # An empty name is not a name, and the payload cannot be empty.
            return None
        # Nothing to spell out, but parts to write beneath: the surname markers
        # stand for the name that is not recorded.
        personal = g7types.PersonalName(fullname="//")
    elif payload_surname:
        personal = g7types.PersonalName(
            fullname=" ".join(
                part
                for part in (payload_given, payload_surname, payload_suffix)
                if part
            ),
            given=payload_given or None,
            surname=payload_surname,
            suffix=payload_suffix or None,
        )
    else:
        # With no surname there are no slashes to place, and the name is written
        # as it stands.
        personal = g7types.PersonalName(
            fullname=" ".join(part for part in (payload_given, payload_suffix) if part)
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
    pointer = context.xref("person", person_ref.ref)
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


def _parent_relations(
    person: Person, context: ExportContext
) -> dict[str, tuple[list[ChildRefType], str | None]]:
    """Get, for each parent family, how the person is related to its parents.

    Each family gives the relations to the parents it has (to both if it has
    neither), and which of them adopted the person: HUSB, WIFE, BOTH or None.
    """
    found = {}
    for handle in person.get_parent_family_handle_list():
        family = context.load("family", handle)
        if family is None:
            continue
        child_ref = next(
            (r for r in family.get_child_ref_list() if r.ref == person.handle), None
        )
        if child_ref is None:
            continue
        father = child_ref.get_father_relation()
        mother = child_ref.get_mother_relation()
        relations = []
        if family.get_father_handle():
            relations.append(father)
        if family.get_mother_handle():
            relations.append(mother)
        relations = relations or [father, mother]
        by_father = father == ChildRefType.ADOPTED and bool(family.get_father_handle())
        by_mother = mother == ChildRefType.ADOPTED and bool(family.get_mother_handle())
        adopted_by = (
            "BOTH" if by_father and by_mother
            else "HUSB" if by_father
            else "WIFE" if by_mother
            else None
        )  # fmt: skip
        found[handle] = (relations, adopted_by)
    return found


def _pedigree_name(relation: ChildRefType) -> str:
    return relation.xml_str() or str(relation)


def _add_pedigree(
    famc: g7types.GedcomStructure,
    relations: list[ChildRefType],
    half_adoption: bool,
) -> None:
    """Write how a child is related to its parents, unless by birth.

    PEDI is one value for both parents. Where an adoption event names the one
    parent who adopted, PEDI gives the other's relation, ADOPTED standing for
    birth since that is how the import reads it. Otherwise, where they differ,
    its phrase says what each relation is.
    """
    relations = [r for r in relations if r != ChildRefType.NONE]
    if len({_pedigree_name(r) for r in relations}) == 1:
        _write_pedigree(famc, relations[0])
        return
    if half_adoption:
        (other,) = [r for r in relations if r != ChildRefType.ADOPTED]
        if other == ChildRefType.BIRTH:
            add(famc, g7const.PEDI, "ADOPTED")
        else:
            _write_pedigree(famc, other)
        return
    if len(relations) == 2:
        father, mother = relations
        pedigree = add(famc, g7const.PEDI, "OTHER")
        add(
            pedigree,
            g7const.PHRASE,
            f"{_pedigree_name(father)} (father), {_pedigree_name(mother)} (mother)",
        )


def _write_pedigree(famc: g7types.GedcomStructure, relation: ChildRefType) -> None:
    """Write one relation as PEDI, unless by birth."""
    if relation.is_custom():
        name = _pedigree_name(relation)
        enum = name if name in PEDIGREE_VOCABULARY else None
    else:
        enum = PEDIGREE_ENUMS.get(int(relation))
    if enum == "BIRTH":
        return
    pedigree = add(famc, g7const.PEDI, enum or "OTHER")
    if enum is None:
        add(pedigree, g7const.PHRASE, _pedigree_name(relation))


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

    parents = _parent_relations(person, context)
    adoptions = [(h, by) for h, (_, by) in parents.items() if by is not None]
    # An adoption event can name the family, but only when there is one to name.
    adoptive_family = adoptions[0] if len(adoptions) == 1 else None
    adoption_written = False
    for event_ref in person.get_event_ref_list():
        event = context.owned_event(event_ref.ref, person.handle)
        if event is not None:
            structure = add_event(
                record, event, INDIVIDUAL_EVENT_TAGS, context, person.handle
            )
            if (
                structure.tag == g7const.ADOP
                and adoptive_family is not None
                and not adoption_written
            ):
                family_handle, side = adoptive_family
                pointer = context.pointer("family", family_handle)
                famc = add(structure, g7const.FAMC, pointer=pointer)
                add(famc, g7const.ADOP, side)
                adoption_written = True

    for handle in person.get_parent_family_handle_list():
        famc = add(record, g7const.FAMC, pointer=context.pointer("family", handle))
        relations, adopted_by = parents.get(handle, ([], None))
        half_adoption = adoption_written and adopted_by in ("HUSB", "WIFE")
        _add_pedigree(famc, relations, half_adoption)
    for handle in person.get_family_handle_list():
        add(record, g7const.FAMS, pointer=context.pointer("family", handle))

    for person_ref in person.get_person_ref_list():
        add_association(record, person_ref, context)

    add_notes(record, person, context)
    add_media_refs(record, person, context)
    add_citations(record, person, context)
    util.add_change_date(record, person.change)
    return record
