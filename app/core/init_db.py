"""Database initialization and default data."""
import logging

from core.auth.manager import get_auth_manager
from core.database import get_db

logger = logging.getLogger(__name__)


def init_database():
    """Initialize the schema and idempotent built-in data."""
    # Schema is created by Database. Instantiating it here makes startup errors
    # explicit before background scanner discovery begins.
    get_db()

    auth_manager = get_auth_manager()
    if auth_manager.setup_required():
        logger.warning(
            "No users configured. Open the Web UI to create the first administrator."
        )
    else:
        logger.info("Authentication database initialized")

    from core.scanning.profiles import get_profile_repository

    get_profile_repository().seed_defaults()
    logger.info("Built-in scan profiles seeded")
    logger.info("Database initialized successfully")


if __name__ == "__main__":
    init_database()
