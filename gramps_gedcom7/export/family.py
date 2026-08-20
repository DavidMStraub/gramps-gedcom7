"""Write Gramps families as GEDCOM family records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import Family

from . import util
from .citation import add_citations
from .event import FAMILY_EVENT_TAGS, add_event
from .multimedia import add_media_refs
from .note import add_notes
from .util import add, add_phrase_from_notes

if TYPE_CHECKING:
    from .exporter import ExportContext


def family_to_record(family: Family, context: ExportContext) -> g7types.GedcomStructure:
    """Write a family as a family record."""
    record = g7types.GedcomStructure(
        tag=g7const.FAM, xref=context.xrefs.get(family.handle)
    )
    util.add_privacy(record, family.get_privacy())

    util.add_attributes(record, family, context)

    for event_ref in family.get_event_ref_list():
        event = context.owned_event(event_ref.ref, family.handle)
        if event is not None:
            add_event(record, event, FAMILY_EVENT_TAGS, context, family.handle)

    if family.get_father_handle():
        add(record, g7const.HUSB, pointer=context.xrefs.pointer(family.get_father_handle()))
    if family.get_mother_handle():
        add(record, g7const.WIFE, pointer=context.xrefs.pointer(family.get_mother_handle()))
    for child_ref in family.get_child_ref_list():
        child = add(record, g7const.CHIL, pointer=context.xrefs.pointer(child_ref.ref))
        add_phrase_from_notes(child, child_ref, context)

    add_notes(record, family, context)
    add_media_refs(record, family, context)
    add_citations(record, family, context)
    util.add_change_date(record, family.change)
    return record
