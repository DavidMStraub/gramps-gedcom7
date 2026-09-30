"""Allocate GEDCOM cross-reference identifiers for Gramps objects."""

from __future__ import annotations

import re

from gedcom7 import const as g7const

# The grammar allows A-Z, 0-9 and underscore between the at-signs.
_INVALID = re.compile(r"[^A-Z0-9_]")


class XrefMap:
    """The cross-reference identifier standing for each Gramps handle.

    Gramps IDs are used where they can be, since that keeps an exported file
    recognizable and lets a re-import restore the same IDs, but they are free
    text in Gramps and the grammar is not, so they are sanitized and made unique.
    """

    def __init__(self) -> None:
        """Start with no identifiers allocated."""
        self._by_handle: dict[str, str] = {}
        self._taken: set[str] = set()

    def add(self, handle: str, gramps_id: str, prefix: str) -> str:
        """Allocate the identifier for a handle, and return it.

        Called once per object before anything is written, so that a pointer can
        be resolved before its record is reached.
        """
        if handle in self._by_handle:
            return self._by_handle[handle]
        xref = self._unique(self._sanitize(gramps_id, prefix))
        self._by_handle[handle] = xref
        self._taken.add(xref)
        return xref

    def get(self, handle: str | None) -> str | None:
        """Get the identifier allocated for a handle, or None if there is none."""
        if handle is None:
            return None
        return self._by_handle.get(handle)

    def pointer(self, handle: str | None) -> str:
        """Get the pointer to a handle, the void pointer if it has no record.

        A Gramps reference can outlive what it points at, and the specification
        has a pointer for a reference whose target is not in the dataset, so a
        broken reference is written as such rather than dropped.
        """
        return self.get(handle) or g7const.VOIDPTR

    @staticmethod
    def _sanitize(gramps_id: str, prefix: str) -> str:
        """Turn a Gramps ID into something the grammar accepts."""
        cleaned = _INVALID.sub("_", (gramps_id or "").upper()).strip("_")
        return cleaned or prefix

    def _unique(self, candidate: str) -> str:
        """Return the identifier, numbered if that spelling is already used."""
        # VOID is the void pointer's spelling, so no record may claim it.
        if f"@{candidate}@" not in self._taken and candidate != "VOID":
            return f"@{candidate}@"
        suffix = 2
        while f"@{candidate}_{suffix}@" in self._taken:
            suffix += 1
        return f"@{candidate}_{suffix}@"
