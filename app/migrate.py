"""Create tables safely. Run once per rollout: python -m app.migrate"""

from __future__ import annotations

import logging
import os
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from .database import Base

MIGRATION_LOCK_ID = 727001
WAIT_SECONDS = int(os.environ.get("DB_WAIT_SECONDS", "90"))


def main() -> int:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        try:
            with engine.begin() as connection:
                if connection.dialect.name == "postgresql":
                    # Two pods can start together. The lock lets only one create tables.
                    connection.execute(
                        text("SELECT pg_advisory_xact_lock(:id)"), {"id": MIGRATION_LOCK_ID}
                    )
                Base.metadata.create_all(connection)
            logging.info("database schema is ready")
            return 0
        except OperationalError as error:
            if time.monotonic() > deadline:
                logging.error("database not reachable: %s", error)
                return 1
            logging.info("waiting for database")
            time.sleep(3)


if __name__ == "__main__":
    sys.exit(main())
