from typing import TypeVar, Union

from gramps.gen.lib.mediabase import MediaBase
from gramps.gen.lib.primaryobj import BasicPrimaryObject
from gramps.gen.lib.notebase import NoteBase
from gramps.gen.lib.attrbase import AttributeBase, SrcAttributeBase


BasicPrimaryObjectT = TypeVar("BasicPrimaryObjectT", bound=BasicPrimaryObject)
NoteBaseT = TypeVar("NoteBaseT", bound=NoteBase)
MediaBaseT = TypeVar("MediaBaseT", bound=MediaBase)
