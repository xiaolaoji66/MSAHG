"""Count records, users, and venues in the cited public Foursquare ZIP.

Usage: python scripts/audit_public_foursquare_identity_r1.py dataset_tsmc2014.zip
The script is read-only and performs no download or extraction.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path


EXPECTED_SHA256 = "cbe3fdab373d24b09b5fc53509c8958c77ff72b6c1a68589ce337d4f9a80235b"


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: audit_public_foursquare_identity_r1.py ZIP_PATH")
    path = Path(sys.argv[1])
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit("archive SHA256 mismatch: {}".format(digest))

    counts = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for city in ("NYC", "TKY"):
            matches = [
                name
                for name in archive.namelist()
                if name.endswith("dataset_TSMC2014_{}.txt".format(city))
            ]
            if len(matches) != 1:
                raise SystemExit("expected one {} data member".format(city))
            users = set()
            venues = set()
            rows = 0
            for raw_line in archive.open(matches[0]):
                columns = raw_line.decode("latin-1").rstrip("\r\n").split("\t")
                if len(columns) < 2:
                    continue
                rows += 1
                users.add(columns[0])
                venues.add(columns[1])
            counts[city] = {
                "rows": rows,
                "users": len(users),
                "venues": len(venues),
            }
    print(
        json.dumps(
            {"archive_sha256": digest, "counts": counts},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
