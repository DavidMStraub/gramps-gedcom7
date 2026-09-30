"""Errors an export raises, naming the Gramps objects they come from."""

from __future__ import annotations

from dataclasses import dataclass

import gedcom7
from gedcom7.validator import Error

from ..report import GrampsObject, summarize

# Validation errors that a value entered in Gramps can cause, such as a number of
# children that is not a number. Any other is a mistake in the exporter.
DATA_ERROR_CATEGORIES = frozenset({"malformed-payload", "invalid-date"})


@dataclass(frozen=True)
class MissingReference:
    """A reference from a Gramps object to one that is not in the database."""

    referrer: GrampsObject | None
    kind: str
    handle: str

    def __str__(self) -> str:
        """Say who references what, e.g. "Person I0042 references a missing event"."""
        referrer = str(self.referrer) if self.referrer else "An object"
        return f"{referrer} references a missing {self.kind}"


class MissingObjectsError(ValueError):
    """Raised when Gramps objects reference objects missing from the database.

    Running Check and Repair on the database removes such references.
    """

    def __init__(self, missing: list[MissingReference]) -> None:
        """Record every missing reference and summarize them in the message."""
        self.missing = missing
        super().__init__(summarize(missing, "references to missing objects"))


@dataclass(frozen=True)
class ValidationProblem:
    """A validation error, and the Gramps object whose data caused it."""

    error: Error
    gramps_object: GrampsObject | None

    @property
    def from_data(self) -> bool:
        """Say whether the data in Gramps caused it, rather than the exporter."""
        return (
            self.gramps_object is not None
            and self.error.category in DATA_ERROR_CATEGORIES
        )

    def __str__(self) -> str:
        """Name the Gramps object if there is one, else the GEDCOM path."""
        where = self.gramps_object or self.error.path
        return f"{where}: {self.error.message}"


class ExportValidationError(gedcom7.GedcomValidationError):
    """Raised when the exported dataset does not conform.

    Each problem names the Gramps object it came from where it can. Where one
    did not come from the data (``from_data`` is false), it is an exporter bug.
    """

    def __init__(self, errors: list[Error], problems: list[ValidationProblem]) -> None:
        """Record the errors and the problems they come from."""
        super().__init__(errors)
        self.problems = problems
        self.args = (summarize(problems, "validation errors"),)

    @property
    def from_data(self) -> bool:
        """Say whether every problem was caused by the data in Gramps."""
        return all(problem.from_data for problem in self.problems)
