"""Handle GEDCOM shared note records and import them into the Gramps database."""

from typing import List
from gramps.gen.lib import Note, NoteType
from gramps.gen.lib.primaryobj import BasicPrimaryObject
from gedcom7 import types as g7types, const as g7const
from . import util


def handle_shared_note(structure: g7types.GedcomStructure) -> List[BasicPrimaryObject]:
    """Handle a shared note record and convert it to Gramps objects.
    
    Args:
        structure: The GEDCOM note structure to handle.
        
    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    note = util.add_ids(Note(), structure)
    for child in structure.children:
        if child.tag == g7const.MIME:
            if child.value == g7const.MIME_HTML:
                note.type = NoteType(NoteType.HTML_CODE)
    
    return [note]
    