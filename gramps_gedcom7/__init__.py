from importlib.metadata import PackageNotFoundError, version

from .importer import import_gedcom
from .settings import ImportSettings

try:
    __version__ = version("gramps-gedcom7")
except PackageNotFoundError:  # package is not installed
    __version__ = "unknown"
