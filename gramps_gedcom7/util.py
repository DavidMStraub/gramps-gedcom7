import uuid

from gedcom7 import types as g7types
from gramps.gen.lib.primaryobj import BasicPrimaryObject


def make_handle() -> str:
    """Generate a unique handle for a new object."""
    return uuid.uuid4().hex


def add_ids(
    obj: BasicPrimaryObject, structure: g7types.GedcomStructure
) -> BasicPrimaryObject:
    """Add a handle and Gramps ID to a new Gramps object."""
    obj.handle = make_handle()
    if not structure.xref or len(structure.xref) < 3:
        raise ValueError(f"Invalid xref ID: {structure.xref}")
    obj.gramps_id = structure.xref[1:-1]
    return obj
