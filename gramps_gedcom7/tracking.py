"""Find what an import left out, as the parts of the data it never read."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from types import TracebackType
from typing import Any

from gedcom7 import const as g7const
from gedcom7.types import GedcomStructure

# Reading any of these is reading the structure. Its tag is not among them, being
# what every handler compares to find the structures it does read.
_CONTENT = frozenset({"text", "pointer", "children"})

# What the header says about the file rather than the data in it.
_FILE_TAGS = frozenset(
    {g7const.GEDC, g7const.SCHMA, g7const.SOUR, g7const.DEST, g7const.DATE, g7const.LANG}
)


def walk(records: Iterable[GedcomStructure]) -> Iterator[GedcomStructure]:
    """Yield every structure in a dataset."""
    stack = list(reversed(list(records)))
    while stack:
        structure = stack.pop()
        yield structure
        stack.extend(reversed(structure.children))


class ReadTracker:
    """Record which structures are read while in use, by swapping their class."""

    def __init__(self, structures: list[GedcomStructure]) -> None:
        """Track these structures, all of them plain GedcomStructure."""
        self._structures = structures
        self._read: set[int] = set()
        mark = self._read.add

        def tracked(name: str) -> property:
            # A property takes precedence over the slot it shadows, so only
            # reading these costs anything more than it did.
            slot: Any = GedcomStructure.__dict__[name]

            def get(structure: GedcomStructure):
                mark(id(structure))
                return slot.__get__(structure, GedcomStructure)

            def set_(structure: GedcomStructure, value) -> None:
                slot.__set__(structure, value)

            return property(get, set_)

        self._tracked = type(
            "Tracked",
            (GedcomStructure,),
            {"__slots__": (), **{name: tracked(name) for name in _CONTENT}},
        )

    def __enter__(self) -> ReadTracker:
        """Start recording reads."""
        for structure in self._structures:
            structure.__class__ = self._tracked
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Stop recording, leaving the structures as they were."""
        for structure in self._structures:
            structure.__class__ = GedcomStructure

    def unread(self) -> list[GedcomStructure]:
        """List the structures never read whose superstructure was."""
        found = []
        for structure in self._structures:
            if id(structure) in self._read:
                continue
            parent = structure.parent
            if parent is not None and id(parent) not in self._read:
                continue
            if parent is None and structure.tag == g7const.TRLR:
                continue
            if (
                parent is not None
                and parent.parent is None
                and parent.tag == g7const.HEAD
                and structure.tag in _FILE_TAGS
            ):
                continue
            found.append(structure)
        return found


def summarize_unread(structures: list[GedcomStructure]) -> list[tuple[str, str]]:
    """Group structures by the tags leading to them, and say how often each came.

    A large file would otherwise report the same thing once per record.
    """
    groups: dict[str, list[GedcomStructure]] = {}
    for structure in structures:
        tags = []
        node: GedcomStructure | None = structure
        while node is not None:
            tags.append(node.tag)
            record = node
            node = node.parent
        groups.setdefault(" > ".join(reversed(tags)), []).append(record)
    summary = []
    for path, records in groups.items():
        message = "not imported"
        if len(records) > 1:
            message += f", {len(records)} times"
        if records[0].xref:
            message += f" (first in {records[0].xref})"
        summary.append((path, message))
    return summary
