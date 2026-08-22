"""
Main CLI entry point for V2Ray Aggregator.

Provides command-line interface for running the application.
"""
import sys
import argparse
from pathlib import Path

from app.config import get_settings, load_settings
from app.logging_config import setup_logging, get_logger
from app.database.database import init_database, create_tables


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="V2Ray Configuration Aggregator - Collect and publish V2Ray configs from Telegram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run              Start the application (scheduler + bot)
  python main.py collect          Run a single collection cycle
  python main.py status           Show system status
  python main.py init-db          Initialize database
  python main.py test-parser      Test parser functionality
  python main.py generate         Generate output files from database
  python main.py publish          Publish generated files to GitHub
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    subparsers.add_parser('run', help='Start the application (scheduler + bot)')
    
    # Collect command
    subparsers.add_parser('collect', help='Run a single collection cycle')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Init database command
    subparsers.add_parser('init-db', help='Initialize database tables')
    
    # Test parser command
    subparsers.add_parser('test-parser', help='Test parser functionality')
    
    # Generate command
    subparsers.add_parser('generate', help='Generate output files from database')
    
    # Publish command
    subparsers.add_parser('publish', help='Publish to GitHub')
    
    return parser.parse_args()


def cmd_init_db():
    """Initialize database tables."""
    logger = get_logger(__name__)
    
    try:
        logger.info("Initializing database...")
        init_database()
        create_tables()
        logger.info("Database initialized successfully")
        return 0
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1


def cmd_status():
    """Show system status."""
    logger = get_logger(__name__)
    
    try:
        settings = get_settings()
        
        logger.info("=== V2Ray Aggregator Status ===")
        logger.info(f"Database: {settings.database_path}")
        logger.info(f"Dry Run: {settings.dry_run}")
        logger.info(f"Log Level: {settings.log_level}")
        logger.info(f"Collection Interval: {settings.collection_interval_minutes} minutes")
        
        # Check database connection
        from app.database.database import get_session
        from app.database.repository import ChannelRepository, ConfigRepository, CollectionRunRepository
        
        with get_session() as session:
            channels = ChannelRepository.get_all(session)
            configs = ConfigRepository.get_stats(session)
            runs = CollectionRunRepository.get_latest(session, limit=1)
            
            logger.info(f"Channels configured: {len(channels)}")
            logger.info(f"Total unique configs: {configs['total_unique']}")
            logger.info(f"Active configs: {configs['active_count']}")
            logger.info(f"Invalid configs: {configs['invalid_count']}")
            
            if runs:
                latest_run = runs[0]
                logger.info(f"Latest collection run: {latest_run.started_at}")
                logger.info(f"Latest run status: {latest_run.status}")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return 1


def cmd_collect():
    """Run a single collection cycle."""
    logger = get_logger(__name__)
    
    try:
        logger.info("Starting collection cycle...")
        
        # Import collector
        from app.collector.collector import collect_sync
        import asyncio
        
        # Run collection
        stats = asyncio.run(collect_sync())
        
        logger.info(f"Collection cycle completed successfully")
        logger.info(f"Messages scanned: {stats['messages_scanned']}")
        logger.info(f"Configs found: {stats['configs_found']}")
        logger.info(f"Configs added: {stats['configs_added']}")
        logger.info(f"Duplicates removed: {stats['duplicates_removed']}")
        logger.info(f"Invalid configs: {stats['invalid_configs']}")
        
        if stats['errors']:
            logger.warning(f"Errors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        
        return 0
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        return 1


def cmd_run():
    """Start the application."""
    logger = get_logger(__name__)
    
    try:
        logger.info("Starting V2Ray Aggregator...")
        logger.info("Note: Full application not implemented yet in Phase 1")
        logger.info("Use 'python main.py collect' for manual collection")
        return 0
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        return 1


def cmd_test_parser():
    """Test parser functionality."""
    logger = get_logger(__name__)
    
    try:
        logger.info("Testing parser...")
        logger.info("Note: Parser not implemented yet in Phase 1")
        return 0
    except Exception as e:
        logger.error(f"Parser test failed: {e}")
        return 1


def cmd_publish():
    """Publish to GitHub."""
    logger = get_logger(__name__)
    
    try:
        logger.info("Publishing configurations to GitHub...")
        from app.github.publisher import GitHubPublisher
        from app.output.generator import OutputGenerator
        from app.config import settings
        
        # First generate output files
        logger.info("Generating output files...")
        init_database()
        create_tables()
        
        generator = OutputGenerator()
        generator.generate()
        
        # Then publish to GitHub
        publisher = GitHubPublisher()
        result = publisher.publish(source_dir=Path(settings.output_dir))
        
        if result["success"]:
            if result.get("commit_hash"):
                logger.info(f"Successfully published! Commit hash: {result['commit_hash']}")
            else:
                logger.info("No changes to commit")
            return 0
        else:
            logger.error(f"Publish failed: {result.get('error')}")
            return 1
            
    except Exception as e:
        logger.error(f"GitHub publish failed: {e}")
        return 1


def cmd_generate():
    """Generate output files from database."""
    logger = get_logger(__name__)
    
    try:
        logger.info("Starting output generation...")
        
        from app.output.generator import OutputGenerator
        init_database()
        create_tables()
        
        generator = OutputGenerator()
        stats = generator.generate()
        
        logger.info(f"Output generation completed successfully")
        logger.info(f"Total configs: {stats['total_configs']}")
        for protocol, count in stats.get('configs_by_protocol', {}).items():
            logger.info(f"  {protocol}: {count}")
        
        return 0
    except Exception as e:
        logger.error(f"Output generation failed: {e}")
        return 1


def main():
    """Main entry point."""
    args = parse_args()
    
    # Load settings and setup logging
    try:
        settings = load_settings()
        setup_logging(settings.log_level)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        print("Please ensure .env file exists with required variables.", file=sys.stderr)
        return 1
    
    logger = get_logger(__name__)
    
    # Handle commands
    if args.command == 'init-db':
        return cmd_init_db()
    elif args.command == 'status':
        return cmd_status()
    elif args.command == 'collect':
        return cmd_collect()
    elif args.command == 'run':
        return cmd_run()
    elif args.command == 'test-parser':
        return cmd_test_parser()
    elif args.command == 'publish':
        return cmd_publish()
    elif args.command == 'generate':
        return cmd_generate()
    else:
        # No command or invalid command
        print("Please specify a command. Use --help for usage.", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())