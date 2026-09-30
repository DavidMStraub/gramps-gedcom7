from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gramps-gedcom7")
except PackageNotFoundError:  # package is not installed
    __version__ = "unknown"

# Imported after the version, which the export writes into the header it builds.
from .export import export_gedcom  # noqa: E402
from .export.errors import ExportValidationError, MissingObjectsError  # noqa: E402
from .importer import import_gedcom  # noqa: E402
from .process import BrokenPointersError  # noqa: E402
from .report import Report  # noqa: E402
from .settings import ExportSettings, ImportSettings  # noqa: E402

__all__ = [
    "BrokenPointersError",
    "ExportSettings",
    "ExportValidationError",
    "ImportSettings",
    "MissingObjectsError",
    "Report",
    "export_gedcom",
    "import_gedcom",
]
