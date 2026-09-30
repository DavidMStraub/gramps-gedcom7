"""Process GEDCOM structures and import them into the Gramps database."""

from __future__ import annotations

from dataclasses import dataclass

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db import DbTxn, DbWriteBase

from .family import handle_family
from .header import handle_header
from .individual import handle_individual
from .multimedia import handle_multimedia
from .note import handle_shared_note
from .report import Progress, Report, collecting, summarize
from .repository import handle_repository
from .settings import ImportSettings
from .source import handle_source
from .submitter import handle_submitter, submitter_to_researcher
from .tracking import ReadTracker, summarize_unread, walk
from .util import make_handle, structure_path


@dataclass(frozen=True)
class BrokenPointer:
    """A pointer to a record that is not in the file."""

    path: str
    pointer: str

    def __str__(self) -> str:
        """Say where it is, e.g. "@F3@ FAM > HUSB points at missing @I9@"."""
        return f"{self.path} points at missing {self.pointer}"


class BrokenPointersError(ValueError):
    """Raised when pointers point at records that are not in the file.

    ``ImportSettings.void_broken_pointers`` imports such a file instead,
    leaving out what the pointers link.
    """

    def __init__(self, broken: list[BrokenPointer]) -> None:
        """Record every broken pointer and summarize them in the message."""
        self.broken = broken
        super().__init__(summarize(broken, "pointers to missing records"))


def _check_pointers(
    structures: list[g7types.GedcomStructure],
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
    report: Report,
) -> None:
    """Refuse pointers to missing records, or make them void and report them."""
    broken = [
        structure
        for structure in structures
        if structure.pointer
        and structure.pointer != g7const.VOIDPTR
        and structure.pointer not in xref_handle_map
    ]
    if broken and not settings.void_broken_pointers:
        raise BrokenPointersError(
            [BrokenPointer(structure_path(s), s.pointer) for s in broken]
        )
    for structure in broken:
        report.add(
            structure_path(structure),
            f"points at missing {structure.pointer}, so the link was left out",
        )
        structure.pointer = g7const.VOIDPTR


def process_gedcom_structures(
    gedcom_structures: list[g7types.GedcomStructure],
    db: DbWriteBase,
    settings: ImportSettings,
    progress: Progress | None = None,
) -> Report:
    """Process GEDCOM structures and import them into the Gramps database.

    Args:
        gedcom_structures: The GEDCOM structures to process.
        db: The Gramps database to import the GEDCOM structures into.
        settings: Import settings controlling how GEDCOM data is imported.
        progress: Called with how far the import has got, and how far it goes.

    Returns:
        A report of what was not imported.
    """
    if len(gedcom_structures) < 2:
        raise ValueError("No GEDCOM structures to process.")
    first_structure = gedcom_structures[0]
    if first_structure.tag != g7const.HEAD:
        raise ValueError(
            f"First structure must be a HEAD structure, but got {first_structure.tag}"
        )
    last_structure = gedcom_structures[-1]
    if last_structure.tag != g7const.TRLR:
        raise ValueError(
            f"Last structure must be a TRLR structure, but got {last_structure.tag}"
        )

    report = Report()
    structures = list(walk(gedcom_structures))

    # Create a map of handles to XREFs
    xref_handle_map = {}
    for structure in gedcom_structures:
        if structure.xref and structure.xref not in xref_handle_map:
            xref_handle_map[structure.xref] = make_handle()

    _check_pointers(structures, xref_handle_map, settings, report)
    with collecting(report), ReadTracker(structures) as tracker:
        objects, researcher = _build_objects(
            gedcom_structures, db, xref_handle_map, settings, progress
        )
    for path, message in summarize_unread(tracker.unread()):
        report.add(path, message)

    records = len(gedcom_structures) - 2
    if progress is None:
        add_objects_to_database(objects, db)
    else:
        # Writing takes longer than building, so it gets the second half of
        # the count however many objects the records make.
        last = records

        def step(done: int, total: int) -> None:
            nonlocal last
            current = records + done * records // total
            if current != last:
                last = current
                progress(current, 2 * records)

        add_objects_to_database(objects, db, progress=step)
    if researcher is not None:
        db.set_researcher(researcher)
    return report


def _build_objects(
    gedcom_structures: list[g7types.GedcomStructure],
    db: DbWriteBase,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
    progress: Progress | None,
) -> tuple[list, object | None]:
    """Build the Gramps objects the records make, and the researcher if any."""
    head_subm_xref = handle_header(gedcom_structures[0], db, settings=settings)

    # Create a place cache for deduplication
    # Maps ((jurisdiction_name,), parent_handle) -> place_handle
    # parent_handle is None for top-level places, otherwise the handle of the parent place
    place_cache: dict[tuple[tuple[str, ...], str | None], str] = {}

    # Handle the remaining structures (excluding header and trailer)
    objects = []
    records = gedcom_structures[1:-1]
    for done, structure in enumerate(records, start=1):
        objects += (
            handle_structure(
                structure,
                xref_handle_map=xref_handle_map,
                settings=settings,
                place_cache=place_cache,
            )
            or []
        )
        if progress is not None:
            progress(done, 2 * len(records))

    researcher = None
    if head_subm_xref:
        for structure in records:
            if structure.tag == g7const.SUBM and structure.xref == head_subm_xref:
                researcher = submitter_to_researcher(structure)
                break
    return objects, researcher


def handle_structure(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
    place_cache: dict[tuple[tuple[str, ...], str | None], str],
) -> list | None:
    """Handle a single GEDCOM structure and import it into the Gramps database.

    Args:
        structure: The GEDCOM structure to handle.
        xref_handle_map: Mapping from GEDCOM XREFs to Gramps handles.
        settings: Import settings controlling how GEDCOM data is imported.
        place_cache: Cache mapping place jurisdictions to handles for deduplication.
    """
    if structure.tag == g7const.FAM:
        return handle_family(
            structure,
            xref_handle_map=xref_handle_map,
            settings=settings,
            place_cache=place_cache,
        )
    elif structure.tag == g7const.INDI:
        return handle_individual(
            structure,
            xref_handle_map=xref_handle_map,
            settings=settings,
            place_cache=place_cache,
        )
    elif structure.tag == g7const.OBJE:
        return handle_multimedia(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.REPO:
        return handle_repository(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.SNOTE:
        return handle_shared_note(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.SOUR:
        return handle_source(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.SUBM:
        return handle_submitter(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    return None


# The kinds of Gramps object an import adds, as their database methods name them.
OBJECT_KINDS = frozenset(
    {
        "person", "family", "event", "citation", "source",
        "note", "media", "place", "repository", "tag",
    }
)  # fmt: skip


def add_objects_to_database(objects, db, progress: Progress | None = None):
    """Add the objects to the database in a single batch transaction."""
    db.disable_signals()
    try:
        with DbTxn("GEDCOM 7 import", db, batch=True) as transaction:
            for done, obj in enumerate(objects, start=1):
                if progress is not None:
                    progress(done, len(objects))
                kind = type(obj).__name__.lower()
                if kind not in OBJECT_KINDS:
                    continue
                if kind != "tag" and not obj.gramps_id:
                    obj.gramps_id = getattr(db, f"find_next_{kind}_gramps_id")()
                # Committed rather than added, since adding stamps the object as
                # changed now, losing when the file says it last changed.
                getattr(db, f"commit_{kind}")(
                    obj, transaction, change_time=obj.change or None
                )
    finally:
        db.enable_signals()
        db.request_rebuild()
