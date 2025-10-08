import sys
import subprocess
from importlib import resources
import importlib.util

def find_app_path():
    """Find the path to the streamlit_app.py file.
    
    Returns:
        str or None: Path to streamlit_app.py if found, None otherwise.
    """
    try:
        traversable = resources.files("gramps_gedcom7").joinpath("streamlit_app.py")
        with resources.as_file(traversable) as p:
            return str(p)
    except Exception:
        spec = importlib.util.find_spec("gramps_gedcom7.streamlit_app")
        if spec and spec.origin:
            return spec.origin
    return None

def main():
    """Launch the Streamlit application in a separate process."""
    app_path = find_app_path()
    if not app_path:
        print("Could not locate gramps_gedcom7.streamlit_app", file=sys.stderr)
        raise SystemExit(2)

    subprocess.check_call([sys.executable, "-m", "streamlit", "run", app_path])


if __name__ == "__main__":
    main()
