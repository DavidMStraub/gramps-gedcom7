"""Handle GEDCOM submitter records and import them into the Gramps database."""

from typing import List
from gramps.gen.lib.primaryobj import BasicPrimaryObject
from gedcom7 import types as g7types


def handle_submitter(structure: g7types.GedcomStructure) -> List[BasicPrimaryObject]:
    """Handle a submitter record and convert it to Gramps objects.
    
    Args:
        structure: The GEDCOM submitter structure to handle.
        
    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    # TODO: Implement submitter import
    return []
