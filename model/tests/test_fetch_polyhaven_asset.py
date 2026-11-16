from __future__ import annotations

import hashlib
import json

import pytest

TEXTURE_FILES = {
    name: {
        "2k": {
            "jpg": {
                "size": 10 + index,
                "url": f"https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/x/x_{name.lower()}_2k.jpg",
                "md5": f"{index:032x}",
            },
            "png": {"size": 1, "url": "https://example.invalid/x.png", "md5": "0" * 32},
        }
    }
    for index, name in enumerate(("Diffuse", "Rough", "Displacement", "AO"))
}


@pytest.fixture
def fetch(load_script_module):
    return load_script_module("fetch_polyhaven_asset")


def test_texture_entry_takes_the_three_jpg_maps(fetch) -> None:
    entry = fetch.manifest_entry("x", TEXTURE_FILES, "2k", "2026-10-22")
    assert entry["source"] == "https://polyhaven.com/a/x"
    assert entry["license"] == "CC0-1.0"
    assert entry["downloaded_on"] == "2026-10-22"
    assert list(entry["files"]) == ["Diffuse", "Rough", "Displacement"]
    assert entry["files"]["Rough"] == {
        "path": "x_rough_2k.jpg",
        "size": 11,
        "url": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/x/x_rough_2k.jpg",
        "md5": f"{1:032x}",
    }


def test_hdri_entry_takes_the_hdr_sky(fetch) -> None:
    files = {"hdri": {"2k": {"hdr": {"size": 5, "url": "https://h/sky_2k.hdr", "md5": "a" * 32}}}}
    entry = fetch.manifest_entry("sky", files, "2k", "2026-10-22")
    assert entry["files"] == {
        "HDRI": {"path": "sky_2k.hdr", "size": 5, "url": "https://h/sky_2k.hdr", "md5": "a" * 32}
    }
    with pytest.raises(KeyError):
        fetch.manifest_entry("sky", files, "4k", "2026-10-22")


def test_install_verifies_downloads_and_rewrites_the_manifest(fetch, tmp_path, monkeypatch) -> None:
    group = tmp_path / "exterior"
    group.mkdir()
    manifest = group / "sources.json"
    manifest.write_text(
        json.dumps(
            [{"id": "x", "downloaded_on": "2026-01-01", "files": {}}, {"id": "old", "files": {}}]
        )
        + "\n"
    )
    monkeypatch.setattr(fetch, "ASSETS", tmp_path)
    payloads = {"https://h/a.jpg": b"aaa", "https://h/b.jpg": b"bbbb"}
    entry = {
        "id": "x",
        "downloaded_on": "2026-10-22",
        "files": {
            name: {
                "path": url.rsplit("/", 1)[1],
                "size": len(data),
                "url": url,
                "md5": hashlib.md5(data).hexdigest(),
            }
            for name, (url, data) in zip(("Diffuse", "Rough"), payloads.items(), strict=True)
        },
    }
    (group / "a.jpg").write_bytes(b"aaa")
    reads = []

    def read(url):
        reads.append(url)
        return payloads[url]

    assert fetch.install("exterior", entry, read=read) == ["b.jpg"]
    assert reads == ["https://h/b.jpg"]
    assert (group / "b.jpg").read_bytes() == b"bbbb"
    assert json.loads(manifest.read_text()) == [entry, {"id": "old", "files": {}}]

    rerun = {**entry, "downloaded_on": "2026-10-23"}
    assert fetch.install("exterior", rerun, read=read) == []
    assert json.loads(manifest.read_text())[0]["downloaded_on"] == "2026-10-22"
    assert manifest.read_text().endswith("]\n")

    payloads["https://h/b.jpg"] = b"corrupt"
    (group / "b.jpg").unlink()
    with pytest.raises(SystemExit, match="b.jpg"):
        fetch.install("exterior", entry, read=read)
    assert not (group / "b.jpg").exists()
