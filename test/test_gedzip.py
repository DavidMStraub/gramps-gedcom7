"""Tests for importing and exporting GEDZIP archives."""

from __future__ import annotations

import hashlib
import io
import zipfile

import gedcom7
from gramps.gen.db.utils import make_database
from gramps.gen.lib import Media

from gramps_gedcom7 import export_gedzip, import_gedzip, process
from gramps_gedcom7.gedzip import ArchiveNames, extract_to, files_under


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


def all_media(db) -> list[Media]:
    return sorted(db.iter_media(), key=lambda m: m.gramps_id)


def test_round_trip(tmp_path):
    base = tmp_path / "base"
    (base / "photos").mkdir(parents=True)
    (base / "photos" / "a b.jpg").write_bytes(b"one")
    (tmp_path / "abs.jpg").write_bytes(b"two")
    db = db_with_media(
        media("m1", "photos/a b.jpg"),
        media("m2", str(tmp_path / "abs.jpg")),
        media("m3", "https://example.com/c.jpg"),
    )
    target = tmp_path / "out.gdz"
    report = export_gedzip(db, target, files_under(base))
    assert report.messages() == []
    with zipfile.ZipFile(target) as archive:
        assert sorted(archive.namelist()) == [
            "gedcom.ged",
            "media/abs.jpg",
            "media/photos/a b.jpg",
        ]

    extracted = tmp_path / "extracted"
    imported = empty_db()
    report = import_gedzip(target, imported, store_media=extract_to(extracted))
    assert report.messages() == []
    m1, m2, m3 = all_media(imported)
    assert m1.get_path() == str(extracted / "media/photos/a b.jpg")
    assert (extracted / "media/photos/a b.jpg").read_bytes() == b"one"
    assert m1.get_checksum() == hashlib.md5(b"one").hexdigest()
    assert m2.get_path() == str(extracted / "media/abs.jpg")
    assert m3.get_path() == "https://example.com/c.jpg"


def test_import_without_storing_keeps_names(tmp_path):
    (tmp_path / "a b.jpg").write_bytes(b"one")
    target = tmp_path / "out.gdz"
    export_gedzip(db_with_media(media("m1", "a b.jpg")), target, files_under(tmp_path))
    imported = empty_db()
    import_gedzip(target, imported)
    (m1,) = all_media(imported)
    assert m1.get_path() == "media/a b.jpg"


def test_unavailable_file_is_reported_on_both_sides(tmp_path):
    db = db_with_media(media("m1", "gone.jpg"))
    buffer = io.BytesIO()
    report = export_gedzip(db, buffer, files_under(tmp_path))
    assert report.messages() == [
        "Media M1: file gone.jpg not found, left out of the archive"
    ]
    report = import_gedzip(buffer, empty_db())
    assert [(e.where, e.message) for e in report] == [
        ("@M1@ OBJE > FILE", "file missing from archive")
    ]


def test_files_can_come_from_anywhere():
    """A storage backend can give bytes or a function opening the file."""
    db = db_with_media(media("m1", "a.jpg"), media("m2", "b.jpg"))
    content = {"a.jpg": b"one", "b.jpg": b"two"}
    buffer = io.BytesIO()
    export_gedzip(db, buffer, lambda m: lambda: io.BytesIO(content[m.get_path()]))
    stored = {}

    def store(obj, name, file):
        stored[name] = file.read()
        return f"s3://{name}"

    import_gedzip(buffer, (imported := empty_db()), store_media=store)
    assert stored == {"media/a.jpg": b"one", "media/b.jpg": b"two"}
    assert [m.get_path() for m in all_media(imported)] == [
        "s3://media/a.jpg",
        "s3://media/b.jpg",
    ]


def test_archive_names():
    names = ArchiveNames()
    assert names.name("photos/a.jpg") == "media/photos/a.jpg"
    assert names.name("/home/me/a.jpg") == "media/a.jpg"
    assert names.name("/other/a.jpg") == "media/a-2.jpg"
    assert names.name("C:\\pics\\a.jpg") == "media/a-3.jpg"
    assert names.name("../up/b.jpg") == "media/b.jpg"
    assert names.name("/home/me/a.jpg") == "media/a.jpg"


def test_extract_keeps_other_files(tmp_path):
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "a.jpg").write_bytes(b"theirs")
    store = extract_to(tmp_path)
    obj = Media()
    assert store(obj, "media/a.jpg", io.BytesIO(b"ours")) == str(
        tmp_path / "media" / "a-2.jpg"
    )
    assert (tmp_path / "media" / "a.jpg").read_bytes() == b"theirs"
    assert store(obj, "media/a.jpg", io.BytesIO(b"theirs")) == str(
        tmp_path / "media" / "a.jpg"
    )
    assert sorted(p.name for p in (tmp_path / "media").iterdir()) == [
        "a-2.jpg",
        "a.jpg",
    ]


def test_archive_is_valid_gedzip(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"one")
    buffer = io.BytesIO()
    export_gedzip(db_with_media(media("m1", "a.jpg")), buffer, files_under(tmp_path))
    with gedcom7.GedzipReader(buffer) as archive:
        assert archive.missing() == []
        assert gedcom7.validate(archive.records) == []
