"""Utility functions for handling GEDCOM 7 data in Gramps."""

from __future__ import annotations

import uuid

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import Note, NoteType

from .types import BasicPrimaryObjectT, NoteBaseT


def make_handle() -> str:
    """Generate a unique handle for a new object."""
    return uuid.uuid4().hex


def add_ids(
    obj: BasicPrimaryObjectT,
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
) -> BasicPrimaryObjectT:
    """Add a handle and Gramps ID to a new Gramps object."""
    if not structure.xref or len(structure.xref) < 3:
        raise ValueError(f"Invalid xref ID: {structure.xref}")
    if structure.xref not in xref_handle_map:
        raise ValueError(f"Xref ID {structure.xref} not found in xref_handle_map")
    obj.handle = xref_handle_map[structure.xref]
    obj.gramps_id = structure.xref[1:-1]
    return obj


GEDCOM_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def set_change_date(
    structure: g7types.GedcomStructure,
    obj: BasicPrimaryObjectT,
) -> BasicPrimaryObjectT:
    """Set the change date for a Gramps object."""
    change_structure = g7util.get_first_child_with_tag(structure, g7const.CHAN)
    if not change_structure:
        # take creation date as fallback
        change_structure = g7util.get_first_child_with_tag(structure, g7const.CREA)
    if not change_structure:
        # no date found
        return obj
    date_structure = g7util.get_first_child_with_tag(change_structure, g7const.DATE)
    if not date_structure:
        # no date found
        return obj
    assert isinstance(
        date_structure.value, g7types.DateExact
    ), "Expected date to be a DateExact object"
    time_structure = g7util.get_first_child_with_tag(change_structure, g7const.TIME)
    if time_structure:
        assert isinstance(
            time_structure.value, g7types.Time
        ), "Expected time to be a Time object"
        time = time_structure.value
    else:
        time = None
    datetime_value = g7util.date_exact_and_time_to_python_datetime(
        date=date_structure.value,
        time=time,
    )
    obj.change = int(datetime_value.timestamp())
    return obj


def structure_to_note(structure: g7types.GedcomStructure) -> Note:
    """Create a note from a GEDCOM structure of type NOTE or SNOTE.

    Args:
        structure: The GEDCOM note structure to handle.

    Returns:
        A note object.
    """
    note = Note()
    if structure.value is not None:
        assert isinstance(structure.value, str), "Expected value to be a string"
        note.set(structure.value)
    for child in structure.children:
        # set note type to HTML if MIME type is HTML
        if child.tag == g7const.MIME:
            if child.value == g7const.MIME_HTML:
                note.type = NoteType(NoteType.HTML_CODE)
        elif child.tag == g7const.TRAN:
            # iterate over translations - we just append them
            if child.value is None:
                continue
            assert isinstance(child.value, str), "Expected value to be a string"
            note.append("\n\n" + child.value)
    return note


def add_note_to_object(
    structure: g7types.GedcomStructure,
    obj: NoteBaseT,
) -> tuple[NoteBaseT, Note]:
    """Add a note to a Gramps object."""
    note = structure_to_note(structure)
    note.type = NoteType(NoteType.SOURCE)
    note.handle = make_handle()
    # set note change date to parent change date
    set_change_date(structure=structure, obj=note)
    obj.add_note(note.handle)
    return obj, note


def get_next_gramps_id(
    xref_handle_map: dict[str, str],
    prefix: str,
) -> str:
    """Get the next available Gramps ID for a given prefix."""
    existing_ids = {handle[1:-1] for handle in xref_handle_map.values()}
    next_id = 1
    while f"{prefix}{next_id:04d}" in existing_ids:
        next_id += 1
    return f"{prefix}{next_id:04d}"
