"""Export a Gramps database as a GEDCOM 7 dataset."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

import gedcom7
from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db import DbReadBase

from .. import __version__
from ..settings import ExportSettings
from .family import family_to_record
from .header import make_header
from .individual import person_to_record
from .multimedia import media_to_record
from .note import note_to_record
from .source import repository_to_record, source_to_record
from .xrefs import XrefMap

if TYPE_CHECKING:
    from gramps.gen.lib import Attribute, Event, EventRoleType

logger = logging.getLogger(__name__)


@dataclass
class ExportContext:
    """What the export modules need beyond the object they are writing.

    Which record an event is written under is decided before anything is
    written, since a Gramps event may be pointed at from several records while a
    GEDCOM event lives inside one.
    """

    db: DbReadBase
    xrefs: XrefMap
    settings: ExportSettings
    owners: dict[str, set[str]] = field(default_factory=dict)
    people_at: dict[str, list[tuple[str, EventRoleType]]] = field(default_factory=dict)
    note_backlinks: dict[str, int] = field(default_factory=dict)
    written_notes: set[str] = field(default_factory=set)
    skipped_attributes: list[Attribute] = field(default_factory=list)

    def owned_event(self, event_handle: str, owner_handle: str) -> Event | None:
        """Get the event if this record is the one to write it, else None."""
        if owner_handle not in self.owners.get(event_handle, set()):
            return None
        return self.db.get_event_from_handle(event_handle)

    def participants(
        self, event_handle: str, owner_handle: str
    ) -> list[tuple[str, EventRoleType]]:
        """List the people at an event other than the record writing it."""
        return [
            (handle, role)
            for handle, role in self.people_at.get(event_handle, [])
            if handle != owner_handle
        ]


# Every kind of Gramps object written as a record of its own, in the order the
# records are written: how to reach them, what to call one whose Gramps ID
# cannot be used, and what writes it. A Gramps citation is not among them, being
# written where it is cited rather than as a record.
RECORD_KINDS = (
    ("get_person_handles", "get_person_from_handle", "I", person_to_record),
    ("get_family_handles", "get_family_from_handle", "F", family_to_record),
    ("get_source_handles", "get_source_from_handle", "S", source_to_record),
    ("get_repository_handles", "get_repository_from_handle", "R", repository_to_record),
    ("get_media_handles", "get_media_from_handle", "M", media_to_record),
    ("get_note_handles", "get_note_from_handle", "N", note_to_record),
)


def _handles(db: DbReadBase, getter: str) -> list[str]:
    """List the handles of one kind of object.

    Only some of these take an argument saying whether to sort, and sorting is
    by a locale's collation, which is not what an export order should turn on.
    """
    try:
        return list(getattr(db, getter)(sort_handles=False))
    except TypeError:
        return list(getattr(db, getter)())


def _in_order(db: DbReadBase, getter: str, xrefs: XrefMap) -> list[str]:
    """List the handles of one kind of object, in the order they are written.

    A handle is a fresh identifier every time a file is read, so writing records
    in the order the database yields them would put the same data in a different
    order every time. Ordering by cross-reference identifier instead makes two
    exports of the same data the same file.
    """
    return sorted(_handles(db, getter), key=lambda handle: xrefs.get(handle) or "")


def _allocate_xrefs(db: DbReadBase, xrefs: XrefMap) -> None:
    """Allocate an identifier for every record that will be written.

    Every one is allocated before any record is written, so that a pointer can
    be resolved whichever order the records come in.
    """
    for handles_getter, object_getter, prefix, _ in RECORD_KINDS:
        objects = [
            (getattr(db, object_getter)(handle), handle)
            for handle in _handles(db, handles_getter)
        ]
        # By Gramps ID, so that which of two objects claiming one identifier has
        # to give way does not depend on the order the database yields them in.
        for obj, handle in sorted(objects, key=lambda pair: pair[0].gramps_id or ""):
            xrefs.add(handle, obj.gramps_id, prefix)


def _plan_events(db: DbReadBase, context: ExportContext) -> None:
    """Decide which record writes each event, and who else took part in it.

    A person and a family that point at the same event each write their own copy
    of it, there being no way to name a family as an associate; two people
    sharing one write it once, the second appearing as an associate of the first.
    """
    for handle in _in_order(db, "get_person_handles", context.xrefs):
        person = db.get_person_from_handle(handle)
        for event_ref in person.get_event_ref_list():
            context.people_at.setdefault(event_ref.ref, []).append(
                (handle, event_ref.get_role())
            )
    # The first person to point at an event writes it, and the first family
    # likewise, each kind independently of the other.
    for handles_getter, object_getter in (
        ("get_person_handles", "get_person_from_handle"),
        ("get_family_handles", "get_family_from_handle"),
    ):
        owned: set[str] = set()
        for handle in _in_order(db, handles_getter, context.xrefs):
            for event_ref in getattr(db, object_getter)(handle).get_event_ref_list():
                if event_ref.ref not in owned:
                    owned.add(event_ref.ref)
                    context.owners.setdefault(event_ref.ref, set()).add(handle)


def _plan_notes(db: DbReadBase, context: ExportContext) -> None:
    """Count what points at each note, which decides where the note is written."""
    for handle in _handles(db, "get_note_handles"):
        context.note_backlinks[handle] = sum(1 for _ in db.find_backlink_handles(handle))


def db_to_structures(
    db: DbReadBase, settings: ExportSettings | None = None
) -> list[g7types.GedcomStructure]:
    """Convert a Gramps database to the structures of a GEDCOM 7 dataset."""
    settings = settings or ExportSettings()
    xrefs = XrefMap()
    _allocate_xrefs(db, xrefs)
    context = ExportContext(db=db, xrefs=xrefs, settings=settings)
    _plan_events(db, context)
    _plan_notes(db, context)

    records: list[g7types.GedcomStructure] = [make_header(__version__)]
    for handles_getter, object_getter, _, write in RECORD_KINDS:
        for handle in _in_order(db, handles_getter, xrefs):
            # Only notes are ever in this set, and notes come last, so by now
            # every note written inside another structure is known and only the
            # rest need records of their own.
            if handle in context.written_notes:
                continue
            records.append(write(getattr(db, object_getter)(handle), context))
    records.append(g7types.GedcomStructure(tag=g7const.TRLR))

    if context.skipped_attributes:
        names = sorted({str(a.get_type()) for a in context.skipped_attributes})
        logger.warning(
            "%s attributes were not written, having no place in the structure "
            "holding them: %s",
            len(context.skipped_attributes),
            ", ".join(names),
        )
    gedcom7.generate_schema(records)
    return records


def export_gedcom(
    db: DbReadBase,
    output_file: str | Path | BinaryIO,
    settings: ExportSettings | None = None,
    validate: bool = True,
) -> None:
    """Export a Gramps database to a GEDCOM 7 file.

    Args:
        db: The Gramps database to export.
        output_file: Where to write, as a path or a file opened in binary mode.
        settings: Export settings controlling how the dataset is written.
        validate: Check the dataset before writing it, and refuse to write one
            that does not conform. Turn it off to write anyway and see what a
            reader makes of it.
    """
    settings = settings or ExportSettings()
    records = db_to_structures(db, settings=settings)
    if validate:
        errors = gedcom7.validate(records)
        if errors:
            raise gedcom7.GedcomValidationError(errors)
    mark = settings.byte_order_mark
    if isinstance(output_file, (str, Path)):
        with open(output_file, "wb") as handle:
            gedcom7.dump(records, handle, byte_order_mark=mark)
    elif isinstance(output_file, io.TextIOBase):
        raise TypeError(
            "output_file must be opened in binary mode, e.g. open(path, 'wb'), "
            "since a GEDCOM 7 data stream is UTF-8 with its own line terminators"
        )
    else:
        gedcom7.dump(records, output_file, byte_order_mark=mark)
