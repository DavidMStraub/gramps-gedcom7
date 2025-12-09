"""Handle GEDCOM submitter records and import them into the Gramps database."""

from typing import List

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import Address, Repository, RepositoryType, Researcher, Url, UrlType
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .settings import ImportSettings


def submitter_to_researcher(structure: g7types.GedcomStructure) -> Researcher:
    """Convert a GEDCOM SUBMITTER_RECORD to a Gramps Researcher.

    Args:
        structure: The GEDCOM submitter structure.

    Returns:
        A Researcher object.
    """
    researcher = Researcher()

    for child in structure.children:
        if child.tag == g7const.NAME:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                researcher.set_name(child.value)
        elif child.tag == g7const.ADDR:
            # ADDRESS_STRUCTURE
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                researcher.set_street(child.value)
            for addr_child in child.children:
                if addr_child.tag == g7const.ADR1:
                    researcher.set_street(addr_child.value or "")
                elif addr_child.tag == g7const.ADR2:
                    # Append to street
                    if addr_child.value and isinstance(addr_child.value, str):
                        street = researcher.get_street()
                        if street:
                            researcher.set_street(street + "\n" + addr_child.value)
                        else:
                            researcher.set_street(addr_child.value)
                elif addr_child.tag == g7const.ADR3:
                    # Append to street
                    if addr_child.value and isinstance(addr_child.value, str):
                        street = researcher.get_street()
                        if street:
                            researcher.set_street(street + "\n" + addr_child.value)
                        else:
                            researcher.set_street(addr_child.value)
                elif addr_child.tag == g7const.CITY:
                    researcher.set_city(addr_child.value or "")
                elif addr_child.tag == g7const.STAE:
                    researcher.set_state(addr_child.value or "")
                elif addr_child.tag == g7const.POST:
                    researcher.set_postal_code(addr_child.value or "")
                elif addr_child.tag == g7const.CTRY:
                    researcher.set_country(addr_child.value or "")
        elif child.tag == g7const.PHON:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                researcher.set_phone(child.value)
        elif child.tag == g7const.EMAIL:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                researcher.set_email(child.value)
        # TODO: handle FAX, WWW, LANG, notes, media

    return researcher


def handle_submitter(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> List[BasicPrimaryObject]:
    """Handle a submitter record and convert it to a Gramps Repository.

    Following libgedcom pattern, submitters are converted to Repository objects
    with type 'GEDCOM data'. The submitter referenced in HEAD will be separately
    converted to a Researcher object.

    Args:
        structure: The GEDCOM submitter structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.
        settings: Import settings.

    Returns:
        A list containing a Repository object.
    """
    repo = Repository()
    objects = []

    # Get submitter name for repository name
    name_struct = g7util.get_first_child_with_tag(structure, g7const.NAME)
    if name_struct and name_struct.value:
        repo_name = f"Submitter: {name_struct.value}"
    else:
        repo_name = f"Submitter {structure.xref or 'Unknown'}"
    repo.set_name(repo_name)

    # Set repository type to custom "GEDCOM data"
    rtype = RepositoryType()
    rtype.set((RepositoryType.CUSTOM, "GEDCOM data"))
    repo.set_type(rtype)

    # Handle address and contact information
    for child in structure.children:
        if child.tag == g7const.ADDR:
            addr = Address()
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                addr.set_street(child.value)
            for addr_child in child.children:
                if addr_child.tag == g7const.CITY:
                    addr.set_city(addr_child.value or "")
                elif addr_child.tag == g7const.STAE:
                    addr.set_state(addr_child.value or "")
                elif addr_child.tag == g7const.POST:
                    addr.set_postal_code(addr_child.value or "")
                elif addr_child.tag == g7const.CTRY:
                    addr.set_country(addr_child.value or "")
            repo.add_address(addr)
        elif child.tag == g7const.PHON:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                url = Url()
                url.set_path(child.value)
                url.set_type(UrlType.CUSTOM)
                url.set_description("Phone")
                repo.add_url(url)
        elif child.tag == g7const.EMAIL:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                url = Url()
                url.set_path(child.value)
                url.set_type(UrlType.EMAIL)
                repo.add_url(url)
        elif child.tag == g7const.FAX:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                url = Url()
                url.set_path(child.value)
                url.set_type(UrlType.CUSTOM)
                url.set_description("Fax")
                repo.add_url(url)
        elif child.tag == g7const.WWW:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                url = Url()
                url.set_path(child.value)
                url.set_type(UrlType.WEB_HOME)
                repo.add_url(url)
        elif child.tag == g7const.SNOTE:
            if child.pointer != g7grammar.voidptr:
                try:
                    note_handle = xref_handle_map[child.pointer]
                    repo.add_note(note_handle)
                except KeyError:
                    # If the note handle is not found, skip adding the note.
                    pass
        elif child.tag == g7const.NOTE:
            repo, note = util.add_note_to_object(child, repo)
            objects.append(note)
        elif child.tag == g7const.OBJE:
            # Repository doesn't support media references in Gramps, skip
            pass
        elif child.tag == g7const.EXID:
            # Repository doesn't support attributes in Gramps, skip
            pass
        elif child.tag == g7const.REFN:
            # Repository doesn't support attributes in Gramps, skip
            pass
        elif child.tag == g7const.UID:
            # Repository doesn't support attributes in Gramps, skip
            pass
        # TODO: handle LANG

    repo = util.add_ids(repo, structure=structure, xref_handle_map=xref_handle_map)
    util.set_change_date(structure=structure, obj=repo)
    objects.append(repo)
    return objects
