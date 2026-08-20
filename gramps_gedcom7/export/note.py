"""Write Gramps notes as GEDCOM shared note records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import Note, NoteType

from . import util
from .util import add

if TYPE_CHECKING:
    from .exporter import ExportContext

# What the import reads a note in HTML as, and what says so on the way out.
HTML_MIME = "text/html"


def note_to_record(note: Note, context: ExportContext) -> g7types.GedcomStructure:
    """Write a note as a shared note record.

    Only the notes :func:`add_note` did not write inside the structure carrying
    them get here: those several structures share, those Gramps calls general,
    and those whose structure has no room for a note of its own.
    """
    record = g7types.GedcomStructure(
        tag=g7const.SNOTE, xref=context.xrefs.get(note.handle)
    )
    record.text = note.get()
    if int(note.get_type()) == NoteType.HTML_CODE:
        add(record, g7const.MIME, HTML_MIME)
    util.add_change_date(record, note.change)
    return record


def add_note(
    parent: g7types.GedcomStructure, note: Note, context: ExportContext
) -> g7types.GedcomStructure | None:
    """Write one note where its object carries it, or point at its record.

    A note nothing else points at is written inside the structure that carries
    it, which is where it came from and what says what kind of note it is: a
    shared note belongs to no one structure, so reading one back leaves Gramps
    to call it a general note. A note Gramps already calls general is therefore
    written as a record, since writing it inside a structure would make a reader
    call it something more particular than it is.
    """
    if note.handle in context.written_notes:
        # Already written where it belongs, by whatever knew where that was.
        return None
    shared = (
        context.note_backlinks.get(note.handle, 0) > 1
        or int(note.get_type()) == NoteType.GENERAL
    )
    if not shared and util.allows(parent, g7const.NOTE):
        structure = add(parent, g7const.NOTE)
        structure.text = note.get()
        if int(note.get_type()) == NoteType.HTML_CODE:
            add(structure, g7const.MIME, HTML_MIME)
        context.written_notes.add(note.handle)
        return structure
    pointer = context.xrefs.get(note.handle)
    if pointer is None or not util.allows(parent, g7const.SNOTE):
        return None
    return add(parent, g7const.SNOTE, pointer=pointer)


def add_notes(
    parent: g7types.GedcomStructure, obj: object, context: ExportContext
) -> None:
    """Write the notes an object carries, where the structure allows them."""
    for handle in obj.get_note_list():  # type: ignore[attr-defined]
        note = context.db.get_note_from_handle(handle)
        if note is not None:
            add_note(parent, note, context)
