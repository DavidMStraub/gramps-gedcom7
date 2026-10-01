"""Export a Gramps database as a GEDCOM 7 dataset."""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO

import gedcom7
from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db import DbReadBase
from gramps.gen.errors import HandleError

from .. import __version__
from ..report import GrampsObject, Progress, Report
from ..settings import ExportSettings
from .errors import (
    ExportValidationError,
    MissingObjectsError,
    MissingReference,
    ValidationProblem,
)
from .family import family_to_record
from .header import make_header
from .individual import person_to_record
from .multimedia import media_to_record
from .note import note_to_record
from .source import repository_to_record, source_to_record
from .xrefs import XrefMap

if TYPE_CHECKING:
    from gramps.gen.lib import Event, EventRoleType

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
    report: Report = field(default_factory=Report)
    # The Gramps object each structure was written from, by the structure's id.
    origins: dict[int, GrampsObject] = field(default_factory=dict)
    missing: dict[tuple[str, str, str], MissingReference] = field(default_factory=dict)
    current: GrampsObject | None = None

    def load(self, kind: str, handle: str) -> Any:
        """Get an object by handle, or None if it is missing or filtered out.

        A missing one is recorded rather than raised, so that every missing
        reference can be reported at once.
        """
        try:
            return getattr(self.db, f"get_{kind}_from_handle")(handle)
        except HandleError:
            if not self._record_missing(kind, handle):
                raise
            return None

    def _record_missing(self, kind: str, handle: str) -> bool:
        """Find what is missing, in the database beneath any proxy.

        A proxy loads what an object references to decide what to hide, so the
        object that failed to load may exist and be referencing what does not.
        """
        base = getattr(self.db, "basedb", self.db)
        if not getattr(base, f"has_{kind}_handle")(handle):
            self._add_missing(self.current, kind, handle)
            return True
        obj = getattr(base, f"get_{kind}_from_handle")(handle)
        found = False
        for class_name, ref in obj.get_referenced_handles_recursively():
            ref_kind = class_name.lower()
            if not getattr(base, f"has_{ref_kind}_handle")(ref):
                self._add_missing(GrampsObject.of(obj), ref_kind, ref)
                found = True
        return found

    def xref(self, kind: str, handle: str | None) -> str | None:
        """Get the identifier of a referenced record, or None if it has none.

        One with none is either filtered out, which leaves the reference out, or
        missing from the database, which is recorded.
        """
        xref = self.xrefs.get(handle)
        if xref is None and handle:
            base = getattr(self.db, "basedb", self.db)
            if not getattr(base, f"has_{kind}_handle")(handle):
                self._add_missing(self.current, kind, handle)
        return xref

    def pointer(self, kind: str, handle: str | None) -> str:
        """Get the pointer to a referenced record, the void pointer if it has none."""
        return self.xref(kind, handle) or g7const.VOIDPTR

    def _add_missing(self, referrer: GrampsObject | None, kind: str, handle: str) -> None:
        key = (referrer.handle if referrer else "", kind, handle)
        self.missing.setdefault(key, MissingReference(referrer, kind, handle))

    @contextmanager
    def writing(
        self, obj: object, structure: g7types.GedcomStructure | None = None
    ) -> Iterator[None]:
        """Attribute what is loaded and written meanwhile to this object."""
        described = GrampsObject.of(obj)
        if structure is not None:
            self.origins[id(structure)] = described
        previous, self.current = self.current, described
        try:
            yield
        finally:
            self.current = previous

    def origin(self, structure: g7types.GedcomStructure | None) -> GrampsObject | None:
        """Find the Gramps object a structure, or the nearest above it, came from."""
        while structure is not None:
            if id(structure) in self.origins:
                return self.origins[id(structure)]
            structure = structure.parent
        return None

    def owned_event(self, event_handle: str, owner_handle: str) -> Event | None:
        """Get the event if this record is the one to write it, else None."""
        if owner_handle not in self.owners.get(event_handle, set()):
            return None
        return self.load("event", event_handle)

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
# records are written: what to call one whose Gramps ID cannot be used, and what
# writes it. A Gramps citation is not among them, being written where it is
# cited rather than as a record.
RECORD_KINDS = (
    ("person", "I", person_to_record),
    ("family", "F", family_to_record),
    ("source", "S", source_to_record),
    ("repository", "R", repository_to_record),
    ("media", "M", media_to_record),
    ("note", "N", note_to_record),
)


def _handles(db: DbReadBase, kind: str) -> list[str]:
    """List the handles of one kind of object.

    Only some of these take an argument saying whether to sort, and sorting is
    by a locale's collation, which is not what an export order should turn on.
    """
    getter = getattr(db, f"get_{kind}_handles")
    try:
        return list(getter(sort_handles=False))
    except TypeError:
        return list(getter())


def _load_records(context: ExportContext) -> dict[str, list[Any]]:
    """Load every object written as a record, once.

    Through a proxy, listing and loading can be slow enough that doing either
    twice would double the time an export takes.
    """
    loaded = {}
    for kind, _, _ in RECORD_KINDS:
        objects = (context.load(kind, handle) for handle in _handles(context.db, kind))
        loaded[kind] = [obj for obj in objects if obj is not None]
    return loaded


def _allocate_xrefs(loaded: dict[str, list[Any]], xrefs: XrefMap) -> None:
    """Allocate an identifier for every record that will be written.

    Every one is allocated before any record is written, so that a pointer can
    be resolved whichever order the records come in.
    """
    for kind, prefix, _ in RECORD_KINDS:
        # By Gramps ID, so that which of two objects claiming one identifier has
        # to give way does not depend on the order the database yields them in.
        for obj in sorted(loaded[kind], key=lambda obj: obj.gramps_id or ""):
            xrefs.add(obj.handle, obj.gramps_id, prefix)


def _in_order(objects: list[Any], xrefs: XrefMap) -> list[Any]:
    """Sort objects in the order their records are written.

    A handle is a fresh identifier every time a file is read, so writing records
    in the order the database yields them would put the same data in a different
    order every time. Ordering by cross-reference identifier instead makes two
    exports of the same data the same file.
    """
    return sorted(objects, key=lambda obj: xrefs.get(obj.handle) or "")


def _plan_events(loaded: dict[str, list[Any]], context: ExportContext) -> None:
    """Decide which record writes each event, and who else took part in it.

    A person and a family that point at the same event each write their own copy
    of it, there being no way to name a family as an associate; two people
    sharing one write it once, the second appearing as an associate of the first.
    """
    for person in _in_order(loaded["person"], context.xrefs):
        for event_ref in person.get_event_ref_list():
            context.people_at.setdefault(event_ref.ref, []).append(
                (person.handle, event_ref.get_role())
            )
    # The first person to point at an event writes it, and the first family
    # likewise, each kind independently of the other.
    for kind in ("person", "family"):
        owned: set[str] = set()
        for obj in _in_order(loaded[kind], context.xrefs):
            for event_ref in obj.get_event_ref_list():
                if event_ref.ref not in owned:
                    owned.add(event_ref.ref)
                    context.owners.setdefault(event_ref.ref, set()).add(obj.handle)


def _plan_notes(loaded: dict[str, list[Any]], context: ExportContext) -> None:
    """Count what points at each note, which decides where the note is written."""
    for note in loaded["note"]:
        context.note_backlinks[note.handle] = sum(
            1 for _ in context.db.find_backlink_handles(note.handle)
        )


def _build(
    db: DbReadBase, settings: ExportSettings, progress: Progress | None
) -> tuple[list[g7types.GedcomStructure], ExportContext]:
    """Build the dataset, and the context that says where each part came from."""
    context = ExportContext(db=db, xrefs=XrefMap(), settings=settings)
    loaded = _load_records(context)
    _allocate_xrefs(loaded, context.xrefs)
    _plan_events(loaded, context)
    _plan_notes(loaded, context)

    total = sum(len(objects) for objects in loaded.values())
    done = 0
    records: list[g7types.GedcomStructure] = [make_header(__version__)]
    for kind, _, write in RECORD_KINDS:
        for obj in _in_order(loaded[kind], context.xrefs):
            # Only notes are ever in this set, and notes come last, so by now
            # every note written inside another structure is known and only the
            # rest need records of their own.
            if obj.handle not in context.written_notes:
                with context.writing(obj):
                    record = write(obj, context)
                context.origins[id(record)] = GrampsObject.of(obj)
                records.append(record)
            done += 1
            if progress is not None:
                progress(done, total)
    records.append(g7types.GedcomStructure(tag=g7const.TRLR))

    if context.missing:
        raise MissingObjectsError(list(context.missing.values()))
    if context.report:
        logger.warning(
            "%s things were not written: %s",
            len(context.report),
            "; ".join(context.report.messages()[:3]),
        )
    gedcom7.generate_schema(records)
    return records, context


def db_to_structures(
    db: DbReadBase,
    settings: ExportSettings | None = None,
    progress: Progress | None = None,
) -> list[g7types.GedcomStructure]:
    """Convert a Gramps database to the structures of a GEDCOM 7 dataset.

    Raises :class:`MissingObjectsError` if objects reference missing ones.
    """
    records, _ = _build(db, settings or ExportSettings(), progress)
    return records


def export_gedcom(
    db: DbReadBase,
    output_file: str | Path | BinaryIO,
    settings: ExportSettings | None = None,
    validate: bool = True,
    progress: Progress | None = None,
) -> Report:
    """Export a Gramps database to a GEDCOM 7 file.

    Args:
        db: The Gramps database to export.
        output_file: Where to write, as a path or a file opened in binary mode.
        settings: Export settings controlling how the dataset is written.
        validate: Check the dataset before writing it, and refuse to write one
            that does not conform. Turn it off to write anyway and see what a
            reader makes of it.
        progress: Called with the number of records written so far and the
            number there are in all.

    Returns:
        A report of what was not written.

    Raises:
        MissingObjectsError: Objects reference objects missing from the database.
        ExportValidationError: The dataset does not conform.
    """
    settings = settings or ExportSettings()
    records, context = _build(db, settings, progress)
    if validate:
        errors = gedcom7.validate(records)
        if errors:
            problems = [
                ValidationProblem(error, context.origin(error.structure))
                for error in errors
            ]
            raise ExportValidationError(errors, problems)
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
    return context.report
