"""Enhanced note handler with GEDCOM 7 HTML subset support.

This module extends the standard note handler to properly handle GEDCOM 7's
HTML subset formatting, preserving rich text that GRAMPS supports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import types as g7types
from gramps.gen.lib import Note, NoteType, StyledText, StyledTextTag, StyledTextTagType

from . import util
from .settings import ImportSettings

if TYPE_CHECKING:
    from gedcom7.types import GedcomStructure


def handle_shared_note_enhanced(
    structure: GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> tuple[Note, list]:
    """Handle a shared note with HTML formatting support.

    GEDCOM 7 supports an HTML subset in NOTE values:
    - <b>bold</b>
    - <i>italic</i>
    - <u>underline</u>
    - <sup>superscript</sup>
    - <sub>subscript</sub>
    - <a href="url">link</a>

    Args:
        structure: The GEDCOM structure containing the note data.
        xref_handle_map: A map of XREFs to Gramps handles.
        settings: Import settings.

    Returns:
        A tuple containing the Gramps Note object and an empty list.
    """
    if not structure.xref:
        raise ValueError("SNOTE structure must have an XREF")

    note = Note()
    note.handle = xref_handle_map.get(structure.xref, util.make_handle())
    
    # Get the note text
    if structure.value and isinstance(structure.value, str):
        # Convert HTML subset to StyledText
        styled_text = convert_html_to_styled_text(structure.value)
        note.set_styledtext(styled_text)
    
    # Process children
    for child in structure.children:
        if child.tag == "MIME":
            # GEDCOM 7 MIME type
            if child.value == "text/html":
                note.set_format(Note.FLOWED)
            elif child.value == "text/plain":
                note.set_format(Note.FORMATTED)
        
        elif child.tag == "LANG":
            # Language of the note
            # Could be stored as an attribute
            pass
        
        elif child.tag == "TRAN":
            # Translation - create a separate note
            if isinstance(child.value, str):
                trans_note = Note()
                trans_note.handle = util.make_handle()
                trans_note.set_text(child.value)
                trans_note.set_type(NoteType.TRANSCRIPT)
                
                # Link translation to original
                note.add_note(trans_note.handle)
                
                # Check for language
                for tran_child in child.children:
                    if tran_child.tag == "LANG" and isinstance(tran_child.value, str):
                        # Add language as attribute
                        from gramps.gen.lib import Attribute
                        attr = Attribute()
                        attr.set_type("Language")
                        attr.set_value(tran_child.value)
                        trans_note.add_attribute(attr)
        
        elif child.tag == "SOUR":
            # Source citation on the note itself
            from .citation import handle_citation
            citation, other_objects = handle_citation(
                child,
                xref_handle_map=xref_handle_map,
                settings=settings,
            )
            note.add_citation(citation.handle)

    return note, []


def convert_html_to_styled_text(html_text: str) -> StyledText:
    """Convert GEDCOM 7 HTML subset to GRAMPS StyledText.

    Args:
        html_text: Text containing HTML subset tags.

    Returns:
        A StyledText object with appropriate formatting.
    """
    import re
    
    # Create styled text
    styled = StyledText()
    
    # Track current position and tags
    plain_text = []
    tags = []
    pos = 0
    
    # Simple HTML tag parser
    tag_pattern = re.compile(r'<(/?)(\w+)(?:\s+href="([^"]+)")?>|([^<]+)')
    
    # Stack for nested tags
    tag_stack = []
    
    for match in tag_pattern.finditer(html_text):
        closing, tag_name, href, text = match.groups()
        
        if text:
            # Plain text
            plain_text.append(text)
            pos += len(text)
        
        elif tag_name:
            # HTML tag
            if closing:
                # Closing tag - pop from stack and create StyledTextTag
                if tag_stack and tag_stack[-1][0] == tag_name:
                    start_tag, start_pos = tag_stack.pop()
                    
                    # Map HTML tags to GRAMPS style tags
                    if tag_name == 'b':
                        tag = StyledTextTag(
                            StyledTextTagType.BOLD,
                            [(start_pos, pos)]
                        )
                        tags.append(tag)
                    elif tag_name == 'i':
                        tag = StyledTextTag(
                            StyledTextTagType.ITALIC,
                            [(start_pos, pos)]
                        )
                        tags.append(tag)
                    elif tag_name == 'u':
                        tag = StyledTextTag(
                            StyledTextTagType.UNDERLINE,
                            [(start_pos, pos)]
                        )
                        tags.append(tag)
                    elif tag_name == 'sup':
                        tag = StyledTextTag(
                            StyledTextTagType.SUPERSCRIPT,
                            [(start_pos, pos)]
                        )
                        tags.append(tag)
                    elif tag_name == 'sub':
                        # GRAMPS doesn't have subscript, use a custom tag
                        tag = StyledTextTag(
                            StyledTextTagType.FONTFACE,
                            [(start_pos, pos)],
                            "subscript"
                        )
                        tags.append(tag)
                    elif tag_name == 'a':
                        # Link - store the URL
                        if len(tag_stack) > 0 and len(tag_stack[-1]) > 2:
                            url = tag_stack[-1][2]
                            tag = StyledTextTag(
                                StyledTextTagType.LINK,
                                [(start_pos, pos)],
                                url
                            )
                            tags.append(tag)
            else:
                # Opening tag - push to stack
                if tag_name == 'a' and href:
                    tag_stack.append((tag_name, pos, href))
                else:
                    tag_stack.append((tag_name, pos))
    
    # Set the plain text and tags
    styled.set_text(''.join(plain_text))
    for tag in tags:
        styled.set_tags(styled.get_tags() + [tag])
    
    return styled


def handle_inline_note_enhanced(
    structure: GedcomStructure,
    settings: ImportSettings,
) -> Note:
    """Handle an inline NOTE with HTML formatting.

    Args:
        structure: The GEDCOM structure containing the note.
        settings: Import settings.

    Returns:
        A Note object.
    """
    note = Note()
    note.handle = util.make_handle()
    
    if isinstance(structure.value, str):
        # Convert HTML subset to StyledText
        styled_text = convert_html_to_styled_text(structure.value)
        note.set_styledtext(styled_text)
    
    # Process any MIME type
    for child in structure.children:
        if child.tag == "MIME":
            if child.value == "text/html":
                note.set_format(Note.FLOWED)
            elif child.value == "text/plain":
                note.set_format(Note.FORMATTED)
    
    return note