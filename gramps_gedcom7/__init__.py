from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gramps-gedcom7")
except PackageNotFoundError:  # package is not installed
    __version__ = "unknown"

# Imported after the version, which the export writes into the header it builds.
from .export import export_gedcom  # noqa: E402
from .importer import import_gedcom  # noqa: E402
from .settings import ExportSettings, ImportSettings  # noqa: E402

__all__ = [
    "ExportSettings",
    "ImportSettings",
    "export_gedcom",
    "import_gedcom",
]
