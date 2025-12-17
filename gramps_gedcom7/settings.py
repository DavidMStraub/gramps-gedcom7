from dataclasses import dataclass


@dataclass
class ImportSettings:
    """Settings for importing GEDCOM 7 files into Gramps."""

    head_plac_form: list[str] | None = None
    """Default place form from HEAD.PLAC.FORM, used when PLAC.FORM is absent."""
