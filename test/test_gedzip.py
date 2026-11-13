"""Tests for importing and exporting GEDZIP archives."""

from __future__ import annotations

import io
import zipfile

import gedcom7
import pytest
from gramps.gen.db.utils import make_database
from gramps.gen.lib import Media

from gramps_gedcom7 import export_gedzip, import_gedzip, process
from gramps_gedcom7.gedzip import archive_name

CONTENT = {"photos/a b.jpg": b"one", "b.jpg": b"two"}


def empty_db():
    db = make_database("sqlite")
    db.load(":memory:")
    return db


def media(handle: str, path: str) -> Media:
    obj = Media()
    obj.handle = handle
    obj.gramps_id = handle.upper()
    obj.set_path(path)
    obj.set_mime_type("image/jpeg")
    return obj


def db_with_media(*objects: Media):
    db = empty_db()
    process.add_objects_to_database(list(objects), db)
    return db


def from_content(obj: Media):
    if obj.get_path() not in CONTENT:
        return None
    return lambda: io.BytesIO(CONTENT[obj.get_path()])


def paths(db) -> list[str]:
    return [m.get_path() for m in sorted(db.iter_media(), key=lambda m: m.gramps_id)]


def test_round_trip(tmp_path):
    db = db_with_media(
        media("m1", "photos/a b.jpg"),
        media("m2", "b.jpg"),
        media("m3", "HTTPS://example.com/c.jpg"),
    )
    target = tmp_path / "out.gdz"
    assert export_gedzip(db, target, from_content).messages() == []
    with zipfile.ZipFile(target) as archive:
        assert sorted(archive.namelist()) == ["b.jpg", "gedcom.ged", "photos/a b.jpg"]
        assert archive.read("photos/a b.jpg") == b"one"
    imported = empty_db()
    assert import_gedzip(target, imported).messages() == []
    assert paths(imported) == ["photos/a b.jpg", "b.jpg", "HTTPS://example.com/c.jpg"]


def test_files_are_given_by_path(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"one")
    buffer = io.BytesIO()
    export_gedzip(
        db_with_media(media("m1", "a.jpg")),
        buffer,
        lambda obj: str(tmp_path / obj.get_path()),
    )
    with zipfile.ZipFile(buffer) as archive:
        assert archive.read("a.jpg") == b"one"


def test_unavailable_file_is_reported_on_both_sides():
    buffer = io.BytesIO()
    report = export_gedzip(db_with_media(media("m1", "gone.jpg")), buffer, from_content)
    assert report.messages() == [
        "Media M1: file gone.jpg not found, left out of the archive"
    ]
    report = import_gedzip(buffer, empty_db())
    assert [(e.where, e.message) for e in report] == [
        ("@M1@ OBJE > FILE", "file missing from archive")
    ]


def test_absolute_path_is_left_out():
    buffer = io.BytesIO()
    report = export_gedzip(
        db_with_media(media("m1", "/home/me/a.jpg")), buffer, from_content
    )
    assert report.messages() == [
        "Media M1: path /home/me/a.jpg not relative, file left out of the archive"
    ]
    with zipfile.ZipFile(buffer) as archive:
        assert archive.namelist() == ["gedcom.ged"]


@pytest.mark.parametrize(
    "path, name",
    [
        ("photos/a.jpg", "photos/a.jpg"),
        ("./photos//a.jpg", "photos/a.jpg"),
        ("photos/../a.jpg", "a.jpg"),
        ("/home/a.jpg", None),
        ("../a.jpg", None),
        ("C:\\pics\\a.jpg", None),
        ("C:/pics/a.jpg", None),
    ],
)
def test_archive_name(path, name):
    assert archive_name(path) == name


def test_archive_is_valid_gedzip():
    buffer = io.BytesIO()
    export_gedzip(db_with_media(media("m1", "b.jpg")), buffer, from_content)
    with gedcom7.GedzipReader(buffer) as archive:
        assert archive.missing() == []
        assert gedcom7.validate(archive.records) == []
