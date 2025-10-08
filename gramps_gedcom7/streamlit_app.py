"""Streamlit app for GEDCOM 7 to Gramps-XML conversion."""

import streamlit as st
import tempfile
import traceback
import gzip
from pathlib import Path
from typing import Optional, Tuple, List

import gi
gi.require_version("Gtk", "3.0")

from gramps_gedcom7.importer import import_gedcom
from gramps.gen.db.utils import make_database
from gramps.gen.db import DbWriteBase
from gramps.cli.user import User
from gramps.plugins.export.exportxml import export_data


class StreamlitProgressCallback:
    """Progress callback for Streamlit."""

    def __init__(self, progress_bar):
        self.progress_bar = progress_bar
        self.current = 0
        self.total = 0

    def __call__(self, value):
        """Callback function for progress updates."""
        if value is not None:
            if isinstance(value, (int, float)) and 0 <= value <= 1:
                self.progress_bar.progress(value)
            else:
                try:
                    normalized = min(max(float(value), 0.0), 1.0)
                    self.progress_bar.progress(normalized)
                except:
                    pass


def convert_gedcom_to_xml(
    gedcom_file, progress_callback=None
) -> Tuple[Optional[bytes], List[str], List[str]]:
    """
    Converts a GEDCOM file to Gramps-XML format.
    Uses the same logic as gedcom2xml.py

    Returns:
        Tuple[Optional[bytes], List[str], List[str]]: (XML data, errors, warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        if progress_callback:
            progress_callback(0.1)

        db: DbWriteBase = make_database("sqlite")
        db.load(":memory:", callback=None)
        user = User()

        if progress_callback:
            progress_callback(0.3)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ged", delete=False, encoding="utf-8"
        ) as input_temp:
            gedcom_content = gedcom_file.read()
            if isinstance(gedcom_content, bytes):
                try:
                    gedcom_content = gedcom_content.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        gedcom_content = gedcom_content.decode("latin-1")
                    except UnicodeDecodeError:
                        gedcom_content = gedcom_content.decode("cp1252")
            input_temp.write(gedcom_content)
            input_temp_path = input_temp.name

        try:
            if progress_callback:
                progress_callback(0.5)

            import_gedcom(input_file=input_temp_path, db=db)

            if progress_callback:
                progress_callback(0.7)

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".gramps", delete=False, encoding="utf-8"
            ) as output_temp:
                output_temp_path = output_temp.name

            export_data(database=db, filename=output_temp_path, user=user)

            if progress_callback:
                progress_callback(0.9)

            with open(output_temp_path, "rb") as xml_file:
                raw_content = xml_file.read()
            
            if raw_content.startswith(b'\x1f\x8b'):
                xml_content = gzip.decompress(raw_content)
            else:
                xml_content = raw_content

            Path(output_temp_path).unlink(missing_ok=True)

            if progress_callback:
                progress_callback(1.0)

            return xml_content, errors, warnings

        finally:
            Path(input_temp_path).unlink(missing_ok=True)

    except Exception as e:
        error_msg = f"Conversion error: {str(e)}"
        errors.append(error_msg)
        full_error = traceback.format_exc()
        errors.append(f"Full error:\n{full_error}")
        return None, errors, warnings


def main():
    """Main function of the Streamlit app."""
    st.set_page_config(
        page_title="GEDCOM 7 to Gramps XML Converter", page_icon="🌳", layout="wide"
    )

    st.title("🌳 GEDCOM 7 to Gramps XML Converter")
    st.markdown("---")

    st.markdown(
        """
    This app converts GEDCOM 7 files to Gramps XML format.
    
    **Instructions:**
    1. Upload your GEDCOM file
    2. Click "Convert"
    3. Download the resulting Gramps XML file
    """
    )

    st.subheader("📁 Upload GEDCOM 7 File")
    uploaded_file = st.file_uploader(
        "Choose a GEDCOM file",
        type=["ged", "gedcom"],
        help="Supported formats: .ged, .gedcom (max. 200 MB)",
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        st.info(f"📊 File size: {len(uploaded_file.getvalue()) / 1024:.2f} KB")

        st.subheader("🔄 Conversion")

        col1, col2 = st.columns([1, 3])

        with col1:
            convert_button = st.button("🚀 Convert", type="primary")

        if convert_button:
            with st.spinner("Converting..."):
                progress_bar = st.progress(0)
                callback = StreamlitProgressCallback(progress_bar)

                xml_data, errors, warnings = convert_gedcom_to_xml(
                    uploaded_file, callback
                )

                progress_bar.progress(1.0)

                if xml_data is not None:
                    st.success("✅ Conversion completed successfully!")

                    output_filename = uploaded_file.name.rsplit(".", 1)[0] + ".gramps"
                    st.download_button(
                        label="📥 Download Gramps file",
                        data=xml_data,
                        file_name=output_filename,
                        mime="application/xml",
                    )

                else:
                    st.error("❌ Conversion failed!")

                if warnings:
                    st.subheader("⚠️ Warnings")
                    for warning in warnings:
                        st.warning(warning)

                if errors:
                    st.subheader("❌ Errors")
                    for error in errors:
                        st.error(error)

                if xml_data is not None:
                    st.subheader("📈 Statistics")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Input file",
                            f"{len(uploaded_file.getvalue()) / 1024:.1f} KB",
                        )

                    with col2:
                        st.metric("Output file", f"{len(xml_data) / 1024:.1f} KB")

                    with col3:
                        compression_ratio = len(xml_data) / len(
                            uploaded_file.getvalue()
                        )
                        st.metric("Size ratio", f"{compression_ratio:.2f}x")

    with st.sidebar:
        st.markdown("### ℹ️ About this App")
        st.markdown(
            """
        This app uses the `gramps-gedcom7` library to convert 
        GEDCOM 7 files to Gramps format.
        
        **Supported Features:**
        - GEDCOM 7 standard
        - Complete data conversion
        - Error and warning reports
        - Progress indication
        """
        )

        st.markdown("### 🔧 Technical Details")
        st.markdown(
            """
        - **Input format:** GEDCOM 7
        - **Output format:** Gramps XML
        - **Maximum file size:** 200 MB
        - **Supported encodings:** UTF-8
        """
        )

        st.markdown("### 📚 Helpful Links")
        st.markdown(
            """
        - [GEDCOM 7 Standard](https://gedcom.io/)
        - [Gramps Genealogy Software](https://gramps-project.org/)
        - [gramps-gedcom7 Repository](https://github.com/DavidMStraub/gramps-gedcom7)
        - [python-gedcom7 Library](https://github.com/DavidMStraub/python-gedcom7)
        """
        )


if __name__ == "__main__":
    main()
