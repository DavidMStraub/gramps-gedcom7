from dataclasses import dataclass


@dataclass
class ImportSettings:
    """Settings for importing GEDCOM 7 files into Gramps."""
    
    registered_extensions: set[str] | None = None
