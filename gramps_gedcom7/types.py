from typing import TypeVar

from gramps.gen.lib.primaryobj import BasicPrimaryObject
from gramps.gen.lib.notebase import NoteBase

BasicPrimaryObjectT = TypeVar("BasicPrimaryObjectT", bound=BasicPrimaryObject)
NoteBaseT = TypeVar("NoteBaseT", bound=NoteBase)
