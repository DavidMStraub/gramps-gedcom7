"""Patch for gedcom7 parser to preserve extension tag names.

This patch is necessary until the upstream gedcom7 library is fixed.
See: https://github.com/DavidMStraub/python-gedcom7/issues/5
"""

import re
from gedcom7 import cast, const, grammar
from gedcom7.types import GedcomStructure


def loads_patched(string: str) -> list[GedcomStructure]:
    """Load from a string - patched version that preserves extension tags."""
    context: dict[int, GedcomStructure] = {}
    records: list[GedcomStructure] = []
    ext: dict[str, str] = {}
    
    for match in re.finditer(grammar.line, string):
        data = match.groupdict()
        level = int(data["level"])
        
        # handle continuation lines
        if data["tag"] == const.CONT:
            context[level - 1].text += "\n" + data["linestr"]
            continue
            
        # PATCH: Store original tag and URI separately
        original_tag = data["tag"]
        uri_tag = ext.get(data["tag"]) or data["tag"]
        
        structure = GedcomStructure(
            tag=uri_tag,  # Keep URI for compatibility
            pointer=data["pointer"],
            xref=data["xref"],
            text=data["linestr"],
        )
        
        # PATCH: Add original_tag attribute if it's an extension
        if original_tag != uri_tag:
            structure.original_tag = original_tag
        
        # handle extension tags
        if (
            structure.tag == const.TAG
            and level >= 2
            and 0 in context
            and 1 in context
            and context[0].tag == const.HEAD
            and context[1].tag == const.SCHMA
        ):
            tag_name, tag_uri = structure.text.split(" ", 1)
            ext[tag_name] = tag_uri
            
        context[level] = structure
        
        # append structure to output
        if level > 0:
            parent = context[level - 1]
            parent.append_child(structure)
        else:
            records.append(structure)
            
    return records