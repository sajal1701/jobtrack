"""Assign pre-authentication records to a registered account, with local access."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobtrack import store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help="Existing account that should own all unassigned records")
    args = parser.parse_args()
    database = Path(os.environ.get("JOBTRACK_DB", ROOT / ".data/jobtrack.sqlite3"))
    if not database.is_file():
        parser.error("Database not found. Start the app and register an account first.")
    store.initialize(database)
    try:
        count = store.claim_legacy_applications(database, args.username)
    except ValueError as error:
        parser.error(str(error))
    print(f"Assigned {count} unowned applications to {args.username.lower()}.")


if __name__ == "__main__":
    main()
