"""
Application startup and initialization for V2Ray Aggregator.

Handles application lifecycle, database initialization, and component startup.
"""
from app.config import get_settings
from app.logging_config import setup_logging, get_logger
from app.database.database import init_database, create_tables


class Application:
    """Main application class."""
    
    def __init__(self):
        """Initialize application."""
        self.settings = get_settings()
        self.logger = None
        self._initialized = False
    
    def initialize(self):
        """
        Initialize application components.
        
        Sets up logging, database, and other core components.
        """
        if self._initialized:
            return
        
        # Setup logging
        setup_logging(self.settings.log_level)
        self.logger = get_logger(__name__)
        
        self.logger.info("Initializing V2Ray Aggregator...")
        
        # Initialize database
        try:
            init_database()
            create_tables()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
        
        self._initialized = True
        self.logger.info("Application initialized successfully")
    
    def shutdown(self):
        """Shutdown application gracefully."""
        if self.logger:
            self.logger.info("Shutting down application...")
        
        # Cleanup resources here when needed
        # (e.g., close database connections, stop scheduler, etc.)
        
        if self.logger:
            self.logger.info("Application shutdown complete")
    
    def run(self):
        """
        Run the application.
        
        This is a placeholder for the full application logic.
        In later phases, this will start the scheduler and admin bot.
        """
        self.initialize()
        
        self.logger.info("Application ready")
        self.logger.info("Note: Full application logic not implemented in Phase 1")
        self.logger.info("Use CLI commands for specific operations")


def create_application() -> Application:
    """
    Create and return application instance.
    
    Returns:
        Application instance
    """
    return Application()


# Global application instance
_app: Application | None = None


def get_application() -> Application:
    """
    Get global application instance, creating if necessary.
    
    Returns:
        Application instance
    """
    global _app
    if _app is None:
        _app = create_application()
    return _app
