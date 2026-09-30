"""What an import or export could not carry over, and why."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

Progress = Callable[[int, int], None]
"""Called with how much of a task is done, and how much there is in all."""


@dataclass(frozen=True)
class GrampsObject:
    """A Gramps object, named the way a user would look it up."""

    kind: str
    gramps_id: str
    handle: str

    @classmethod
    def of(cls, obj: object) -> GrampsObject:
        """Describe a Gramps primary object."""
        return cls(
            kind=type(obj).__name__,
            gramps_id=getattr(obj, "gramps_id", "") or "",
            handle=getattr(obj, "handle", "") or "",
        )

    def __str__(self) -> str:
        """Name it by its kind and Gramps ID, e.g. "Person I0042"."""
        return f"{self.kind} {self.gramps_id}".strip()


@dataclass(frozen=True)
class ReportEntry:
    """One thing that was not carried over."""

    where: str
    """The Gramps object, or the path through the GEDCOM data, it belongs to."""

    message: str
    """What was left out, and why."""

    gramps_object: GrampsObject | None = None
    """The Gramps object it belongs to, on export."""

    def __str__(self) -> str:
        """Say where and what, e.g. "Person I0042: attribute Caste not written"."""
        return f"{self.where}: {self.message}" if self.where else self.message


@dataclass
class Report:
    """Everything an import or export left out. Empty when nothing was."""

    entries: list[ReportEntry] = field(default_factory=list)

    def add(
        self, where: str, message: str, gramps_object: GrampsObject | None = None
    ) -> None:
        """Record one thing that was left out."""
        self.entries.append(ReportEntry(where, message, gramps_object))

    def messages(self) -> list[str]:
        """List the entries as text, one line each."""
        return [str(entry) for entry in self.entries]

    def __iter__(self) -> Iterator[ReportEntry]:
        """Iterate over the entries."""
        return iter(self.entries)

    def __len__(self) -> int:
        """Count the entries."""
        return len(self.entries)


_collecting: ContextVar[Report | None] = ContextVar("collecting", default=None)


@contextmanager
def collecting(report: Report) -> Iterator[Report]:
    """Send what :func:`note` records meanwhile to this report."""
    token = _collecting.set(report)
    try:
        yield report
    finally:
        _collecting.reset(token)


def note(where: str, message: str) -> None:
    """Record something left out in the report being collected, if any."""
    report = _collecting.get()
    if report is not None:
        report.add(where, message)


def summarize(problems: list, what: str) -> str:
    """Name the first few problems in one line, and how many more there are."""
    first = "; ".join(str(p) for p in problems[:3])
    more = f", and {len(problems) - 3} more" if len(problems) > 3 else ""
    return f"{len(problems)} {what}: {first}{more}"
