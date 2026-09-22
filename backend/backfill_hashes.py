import hashlib
import os

from app.database import SessionLocal
from app.models import Document


def calculate_sha256(filepath):
    sha256 = hashlib.sha256()

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()


db = SessionLocal()

try:
    documents = (
        db.query(Document)
        .filter(Document.file_hash == None)
        .all()
    )

    print(f"Documents to process: {len(documents)}")

    updated = 0
    missing = 0

    for document in documents:

        filepath = document.filepath

        # Convert old relative paths such as:
        # uploads\filename.pdf
        # into the backend uploads directory.
        if not os.path.isabs(filepath):
            filepath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                filepath
            )

        if not os.path.exists(filepath):
            print(f"FILE NOT FOUND - ID {document.id}: {filepath}")
            missing += 1
            continue

        file_hash = calculate_sha256(filepath)

        document.file_hash = file_hash

        print(
            f"ID {document.id} -> "
            f"{document.filename} -> "
            f"{file_hash}"
        )

        updated += 1

    db.commit()

    print()
    print(f"Hashes updated: {updated}")
    print(f"Files missing: {missing}")

finally:
    db.close()