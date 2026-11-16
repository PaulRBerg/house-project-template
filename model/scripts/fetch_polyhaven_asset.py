"""Fetch a CC0 Poly Haven asset into ``assets/<group>`` and record it in that group's ``sources.json``.

just model-asset <exterior|interior> <asset-id> [resolution]

Textures fetch the JPG Diffuse, Rough and Displacement maps. HDRIs fetch the ``.hdr`` sky.
Each download is checked against the size and MD5 that Poly Haven's file API publishes, and
the manifest entry is written in the shape the existing entries use. Re-running on an
installed asset verifies the files and refreshes the entry without downloading again.
"""

import argparse
import datetime
import hashlib
import json
import sys
import urllib.error
import urllib.request

from project_paths import ASSETS

API = "https://api.polyhaven.com/files/"
PAGE = "https://polyhaven.com/a/"
LICENSE = "CC0-1.0"
TEXTURE_MAPS = ("Diffuse", "Rough", "Displacement")
USER_AGENT = (
    "house-project-template-model/1.0 (+https://github.com/PaulRBerg/house-project-template)"
)


def manifest_entry(asset_id, files, resolution, today):
    """The ``sources.json`` entry for ``asset_id`` from its Poly Haven file listing."""
    if "hdri" in files:
        variants = {"HDRI": files["hdri"][resolution]["hdr"]}
    else:
        variants = {name: files[name][resolution]["jpg"] for name in TEXTURE_MAPS}
    return {
        "id": asset_id,
        "source": PAGE + asset_id,
        "license": LICENSE,
        "downloaded_on": today,
        "files": {
            name: {
                "path": variant["url"].rsplit("/", 1)[1],
                "size": variant["size"],
                "url": variant["url"],
                "md5": variant["md5"],
            }
            for name, variant in variants.items()
        },
    }


def merge_entry(entries, entry):
    """``entries`` with ``entry`` replacing its same-id predecessor in place, or appended."""
    merged = [entry if existing["id"] == entry["id"] else existing for existing in entries]
    return merged if entry in merged else [*merged, entry]


def _read(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _matches(path, record):
    return (
        path.is_file()
        and path.stat().st_size == record["size"]
        and hashlib.md5(path.read_bytes()).hexdigest() == record["md5"]
    )


def install(group, entry, read=_read):
    """Download every file of ``entry`` into ``assets/<group>`` and verify size and MD5."""
    directory = ASSETS / group
    fetched = []
    for record in entry["files"].values():
        target = directory / record["path"]
        if _matches(target, record):
            continue
        target.write_bytes(read(record["url"]))
        if not _matches(target, record):
            target.unlink()
            raise SystemExit(f"{target.name}: download does not match the published size and MD5")
        fetched.append(target.name)
    manifest = directory / "sources.json"
    entries = json.loads(manifest.read_text())
    if not fetched:
        # A verified re-run keeps the date the files were actually downloaded on.
        for existing in entries:
            if existing["id"] == entry["id"]:
                entry["downloaded_on"] = existing["downloaded_on"]
    manifest.write_text(json.dumps(merge_entry(entries, entry), indent=2) + "\n")
    return fetched


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("group", choices=("exterior", "interior"))
    parser.add_argument(
        "asset_id", help="Poly Haven slug, e.g. leafy_grass or belfast_sunset_puresky"
    )
    parser.add_argument(
        "resolution", nargs="?", default="2k", help="Poly Haven size tag (default 2k)"
    )
    args = parser.parse_args(argv)
    try:
        files = json.loads(_read(API + args.asset_id))
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{args.asset_id}: Poly Haven returned {error.code}") from error
    today = datetime.date.today().isoformat()
    try:
        entry = manifest_entry(args.asset_id, files, args.resolution, today)
    except KeyError as error:
        raise SystemExit(
            f"{args.asset_id}: no {error.args[0]} file at {args.resolution}"
        ) from error
    fetched = install(args.group, entry)
    for record in entry["files"].values():
        state = "fetched" if record["path"] in fetched else "present"
        print(f"{state}\t{args.group}/{record['path']}")
    print(f"recorded\t{args.group}/sources.json: {args.asset_id}")


if __name__ == "__main__":
    sys.exit(main())
