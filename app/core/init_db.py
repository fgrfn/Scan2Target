"""Database initialization and default data."""
import logging
from core.database import get_db
from core.auth.manager import get_auth_manager

logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with schema and default data."""
    # Schema is auto-created by Database class
    db = get_db()
    
    # Create default admin user if no users exist
    auth_manager = get_auth_manager()
    
    if not auth_manager.user_repo.user_exists("admin"):
        logger.info("Creating default admin user...")
        auth_manager.register(
            username="admin",
            password="admin",  # CHANGE THIS IN PRODUCTION!
            email="admin@scan2target.local",
            is_admin=True
        )
        logger.warning("✓ Default admin user created: username='admin', password='admin'")
        logger.warning("  ⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")
    
    # Seed/refresh built-in scan profiles (idempotent)
    from core.scanning.profiles import get_profile_repository
    get_profile_repository().seed_defaults()
    logger.info("✓ Built-in scan profiles seeded")
    
    logger.info("✓ Database initialized successfully")


if __name__ == "__main__":
    init_database()
