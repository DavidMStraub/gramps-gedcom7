"""Gramps importer?"""

import gedcom7
from gedcom7 import const
from gedcom7.types import GedcomStructure


def importer(s: str):
    """Import a Gedcom 7 string."""
    records = gedcom7.loads(s)
    for record in records:
        handle_record(record)


def handle_record(record: GedcomStructure):
    if record.tag == const.FAM:
        return handle_family(record)
    if record.tag == const.INDI:
        return handle_person(record)


def handle_family(record: GedcomStructure):
    for child in record.children:
        if child.tag == const.RESN:
            print(child.text, child.as_list_enum())
        elif child.tag == const.HUSB:
            print(child.text, child.pointer)
        elif child.tag == const.WIFE:
            print(child.text, child.pointer)
        elif child.tag == const.CHIL:
            print(child.text, child.pointer)


def handle_person(record: GedcomStructure):
    for child in record.children:
        if child.tag == const.RESN:
            print(child.text, child.as_list_enum())
        elif child.tag == const.NAME:
            print(child.text, child.as_personal_name())
        elif child.tag == const.SEX:
            print(child.text, child.as_enum())
        elif child.tag == const.FAMC:
            print(child.text, child.pointer)
        elif child.tag == const.FAMS:
            print(child.text, child.pointer)
        elif child.tag == const.SUBM:
            print(child.text, child.pointer)
        elif child.tag == const.ASSO:
            print(child.text, child.pointer)
        elif child.tag == const.ALIA:
            print(child.text, child.pointer)
        elif child.tag == const.ANCI:
            print(child.text, child.pointer)
        elif child.tag == const.DESI:
            print(child.text, child.pointer)
        elif child.tag in [const.REFN, const.UID, const.EXID]:
            print(child.text)
        elif child.tag == const.NOTE:
            print(child.text)
        elif child.tag == const.SOUR:
            handle_source_citation(record, child)
        elif child.tag == const.OBJE:
            handle_media_link(record, child)
        elif child.tag == const.CHAN:
            print(child.text)
        elif child.tag == const.CREA:
            print(child.text)
        else:
            print(" ", child.tag)


def handle_source_citation(parent: GedcomStructure, child: GedcomStructure):
    """Handle a source citation."""
    print(parent.tag, child.tag, child.text, child.pointer)

def handle_media_link(parent: GedcomStructure, child: GedcomStructure):
    """Handle a media link."""
    print(parent.tag, child.tag, child.text, child.pointer)


if __name__ == "__main__":
    with open("maximal70.ged", encoding="utf-8") as f:
        s = f.read()
    importer(s)
