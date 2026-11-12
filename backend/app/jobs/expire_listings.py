"""Job d'expiration des annonces : python -m app.jobs.expire_listings

Conçu pour tourner en CronJob Kubernetes (projet 3), par exemple toutes les 5 minutes.
Idempotent, sans état, code de sortie 0 en cas de succès.
"""

import logging
from datetime import datetime

from app.database import SessionLocal
from app.services.listings import expire_listings

logger = logging.getLogger("foodbridge.jobs.expire")


def run() -> int:
    with SessionLocal() as db:
        count = expire_listings(db, datetime.now().astimezone())
    logger.info("expired_listings=%d", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run()
