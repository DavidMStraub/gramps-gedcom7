"""Handle GEDCOM repository records and import them into the Gramps database."""

from typing import List
from gramps.gen.lib import Repository, NoteType, Url, UrlType
from gramps.gen.lib.primaryobj import BasicPrimaryObject
from gedcom7 import types as g7types, const as g7const, util as g7util
from . import util
from .settings import ImportSettings


def handle_repository(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> List[BasicPrimaryObject]:
    """Handle a repository record and convert it to Gramps objects.

    Args:
        structure: The GEDCOM note structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.

    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    repository = Repository()
    objects = []
    for child in structure.children:
        if child.tag == g7const.NAME:
            # set repository name
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                repository.set_name(child.value)
        elif child.tag == g7const.SNOTE:
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            repository.add_note(note_handle)
        elif child.tag == g7const.WWW:
            assert isinstance(child.value, str), "Expected value to be a string"
            url = Url()
            url.set_path(child.value)
            url.set_type(UrlType(UrlType.WEB_HOME))
            repository.add_url(url)
        elif child.tag == g7const.EMAIL:
            assert isinstance(child.value, str), "Expected value to be a string"
            url = Url()
            url.set_path(child.value)
            url.set_type(UrlType(UrlType.EMAIL))
            repository.add_url(url)
        elif child.tag == g7const.NOTE:
            repository, note = util.add_note_to_object(child, repository)
            objects.append(note)
        # TODO handle PHON
        # TODO handle address
        # TODO handle identifier
    repository = util.add_ids(
        repository, structure=structure, xref_handle_map=xref_handle_map
    )
    util.set_change_date(structure=structure, obj=repository)
    objects.append(repository)
    return objects
