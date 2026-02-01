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
    
    # Add default scan profiles if needed
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM scan_profiles")
        row = cursor.fetchone()
        
        if row['count'] == 0:
            logger.info("Creating default scan profiles...")
            profiles = [
                ('color_300_pdf', 'Color @300 DPI', 300, 'Color', 'A4', 'pdf'),
                ('gray_150_pdf', 'Grayscale @150 DPI', 150, 'Gray', 'A4', 'pdf'),
                ('photo_600_jpeg', 'Photo @600 DPI', 600, 'Color', 'A4', 'jpeg'),
            ]
            
            cursor.executemany("""
                INSERT INTO scan_profiles (id, name, dpi, color_mode, paper_size, format)
                VALUES (?, ?, ?, ?, ?, ?)
            """, profiles)
            logger.info("✓ Default scan profiles created")
    
    logger.info("✓ Database initialized successfully")


if __name__ == "__main__":
    init_database()
