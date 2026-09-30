from dataclasses import dataclass


@dataclass
class ImportSettings:
    """Settings for importing GEDCOM 7 files into Gramps."""

    head_plac_form: list[str] | None = None
    """Default place form from HEAD.PLAC.FORM, used when PLAC.FORM is absent."""

    void_broken_pointers: bool = False
    """Import a pointer to a record missing from the file as a void pointer, and
    report it, rather than refusing the file."""


@dataclass
class ExportSettings:
    """Settings for exporting a Gramps database to GEDCOM 7."""

    byte_order_mark: bool = True
    """Begin the data stream with U+FEFF, as the specification says it should."""
