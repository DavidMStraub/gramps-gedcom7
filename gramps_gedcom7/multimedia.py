"""Handle GEDCOM multimedia records and import them into the Gramps database."""

from typing import List

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import Media
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation


def handle_multimedia(
    structure: g7types.GedcomStructure, xref_handle_map: dict[str, str]
) -> List[BasicPrimaryObject]:
    """Handle a multimedia record and convert it to Gramps objects.

    Args:
        structure: The GEDCOM note structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.

    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    media = Media()
    objects = []
    for child in structure.children:
        if child.tag == g7const.RESN:
            util.set_privacy_on_object(resn_structure=child, obj=media)
        elif child.tag == g7const.SNOTE:
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            media.add_note(note_handle)
        elif child.tag == g7const.NOTE:
            media, note = util.add_note_to_object(child, media)
            objects.append(note)
        elif child.tag == g7const.SOUR:
            citation, other_objects = handle_citation(
                child, xref_handle_map=xref_handle_map
            )
            objects.extend(other_objects)
            media.add_citation(citation.handle)
            objects.append(citation)
        # TODO EXID & REFN
        elif child.tag == g7const.UID:
            util.add_uid_to_object(child, media)
    # TODO handle multiple files
    file_structure = g7util.get_first_child_with_tag(structure, g7const.FILE)
    assert file_structure is not None, "Multimedia structure must have a FILE tag"
    assert isinstance(file_structure.value, str), "Expected FILE value to be a string"
    media.set_path(file_structure.value.removeprefix("file://"))
    form_structure = g7util.get_first_child_with_tag(file_structure, g7const.FORM)
    assert form_structure is not None, "Multimedia file must have a FORM tag"
    assert isinstance(
        form_structure.value, g7types.MediaType
    ), "Expected FORM value to be a MediaType"
    media.set_mime_type(form_structure.value.media_type)
    title = g7util.get_first_child_with_tag(file_structure, g7const.TITL)
    if title is not None:
        assert isinstance(title.value, str), "Expected TITL value to be a string"
        media.set_description(title.value)
    # TODO handle MEDIA & PHRASE
    media = util.add_ids(media, structure=structure, xref_handle_map=xref_handle_map)
    util.set_change_date(structure=structure, obj=media)
    objects.append(media)
    return objects
