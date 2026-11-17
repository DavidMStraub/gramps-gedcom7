"""Test how a child is related to its parents, as PEDI and ADOP.FAMC say."""

import io
import pathlib

import gedcom7
import pytest
from gedcom7 import const as g7const
from gramps.gen.db.utils import make_database
from gramps.gen.lib import ChildRefType

from gramps_gedcom7 import process
from gramps_gedcom7.export import db_to_structures
from gramps_gedcom7.importer import import_gedcom

GEDCOM_FILE = pathlib.Path(__file__).parent / "data" / "pedigree.ged"

BIRTH = ("Birth", "Birth")
ADOPTED = ("Adopted", "Adopted")


def empty_db():
    db = make_database("sqlite")
    db.load(":memory:")
    return db


def import_file(source):
    db = empty_db()
    report = import_gedcom(source, db)
    return db, report


def gedcom(body):
    return io.StringIO("0 HEAD\n1 GEDC\n2 VERS 7.0\n" + body + "0 TRLR\n")


@pytest.fixture
def db():
    database, _ = import_file(str(GEDCOM_FILE))
    return database


def relations(db):
    """Each child's relation to father and mother, by child and family ID."""
    found = {}
    for family in db.iter_families():
        for ref in family.get_child_ref_list():
            child = db.get_person_from_handle(ref.ref)
            found[(child.gramps_id, family.gramps_id)] = (
                ref.get_father_relation().xml_str(),
                ref.get_mother_relation().xml_str(),
            )
    return found


def find(structure, tag):
    return next((c for c in structure.children if c.tag == tag), None)


def find_all(structure, tag):
    return [c for c in structure.children if c.tag == tag]


def record(records, xref):
    return next(r for r in records if r.xref == xref)


def pedigrees(records, xref):
    """The PEDI under each FAMC of an individual, with its phrase."""
    found = {}
    for famc in find_all(record(records, xref), g7const.FAMC):
        pedi = find(famc, g7const.PEDI)
        phrase = find(pedi, g7const.PHRASE) if pedi else None
        found[famc.pointer] = (
            pedi.text if pedi else None,
            phrase.text if phrase else None,
        )
    return found


EXPECTED = {
    ("I3", "F1"): BIRTH,
    ("I4", "F1"): ADOPTED,
    ("I4", "F2"): BIRTH,
    ("I5", "F1"): ("Foster", "Foster"),
    ("I6", "F1"): ("Ward", "Ward"),
    ("I7", "F1"): ("SEALING", "SEALING"),
    ("I9", "F3"): ("Adopted", "Birth"),
}


def test_pedigree_sets_the_child_relations(db):
    assert relations(db) == EXPECTED


def test_relations_survive_a_round_trip(db):
    records = db_to_structures(db)
    assert gedcom7.validate(records) == []
    reimported = empty_db()
    import_gedcom(io.StringIO(gedcom7.dumps(records)), reimported)
    assert relations(reimported) == EXPECTED


def test_pedigree_is_written_unless_by_birth(db):
    records = db_to_structures(db)
    assert pedigrees(records, "@I3@") == {"@F1@": (None, None)}
    assert pedigrees(records, "@I4@") == {
        "@F1@": ("ADOPTED", None),
        "@F2@": (None, None),
    }
    assert pedigrees(records, "@I5@") == {"@F1@": ("FOSTER", None)}
    assert pedigrees(records, "@I6@") == {"@F1@": ("OTHER", "Ward")}
    assert pedigrees(records, "@I7@") == {"@F1@": ("SEALING", None)}


def test_adoption_by_one_parent_is_written_on_the_adoption(db):
    records = db_to_structures(db)
    assert pedigrees(records, "@I9@") == {"@F3@": ("ADOPTED", None)}
    famc = find(find(record(records, "@I9@"), g7const.ADOP), g7const.FAMC)
    assert famc.pointer == "@F3@"
    assert find(famc, g7const.ADOP).text == "HUSB"


def test_differing_relations_without_an_adoption_are_named_in_the_phrase(db):
    family = db.get_family_from_gramps_id("F1")
    (ref, *_) = family.get_child_ref_list()
    ref.set_father_relation(ChildRefType(ChildRefType.STEPCHILD))
    process.add_objects_to_database([family], db)
    records = db_to_structures(db)
    assert pedigrees(records, "@I3@") == {
        "@F1@": ("OTHER", "Stepchild (father), Birth (mother)")
    }


def test_contradicting_pedigree_is_reported():
    db, report = import_file(
        gedcom(
            "0 @I1@ INDI\n1 FAMC @F1@\n2 PEDI ADOPTED\n1 FAMC @F1@\n2 PEDI BIRTH\n"
            "0 @F1@ FAM\n1 CHIL @I1@\n"
        )
    )
    assert relations(db) == {("I1", "F1"): ADOPTED}
    assert any("contradicts an earlier pedigree" in str(e) for e in report)


def test_pedigree_for_a_family_without_the_child_is_reported():
    _, report = import_file(
        gedcom("0 @I1@ INDI\n1 FAMC @F1@\n2 PEDI ADOPTED\n0 @F1@ FAM\n")
    )
    assert any("does not list the individual as a child" in str(e) for e in report)
