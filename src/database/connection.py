"""Database connection management"""

import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool

from .models import Base
from ..config import DATA_DIR

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manage database connections"""
    
    def __init__(self, 
                 db_type: str = 'sqlite',
                 db_path: Optional[str] = None,
                 connection_string: Optional[str] = None,
                 echo: bool = False):
        """
        Initialize database connection
        
        Args:
            db_type: 'sqlite' or 'postgresql'
            db_path: Path for SQLite database
            connection_string: Full connection string (overrides other params)
            echo: Whether to log SQL statements
        """
        
        self.db_type = db_type
        self.echo = echo
        
        # Build connection string
        if connection_string:
            self.connection_string = connection_string
        elif db_type == 'sqlite':
            if not db_path:
                db_path = str(DATA_DIR / 'real_estate.db')
            self.connection_string = f'sqlite:///{db_path}'
        elif db_type == 'postgresql':
            # Get from environment variables
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '5432')
            user = os.getenv('DB_USER', 'postgres')
            password = os.getenv('DB_PASSWORD', 'postgres')
            database = os.getenv('DB_NAME', 'real_estate')
            
            self.connection_string = (
                f'postgresql://{user}:{password}@{host}:{port}/{database}'
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        # Create engine with appropriate pool
        if db_type == 'sqlite':
            # SQLite doesn't work well with connection pooling
            self.engine = create_engine(
                self.connection_string,
                echo=echo,
                poolclass=NullPool,
                connect_args={'check_same_thread': False}  # For SQLite
            )
            
            # Enable foreign keys for SQLite
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL with connection pooling
            self.engine = create_engine(
                self.connection_string,
                echo=echo,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True  # Verify connections before using
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )
        
        logger.info(f"Database connection initialized: {db_type}")
    
    def create_tables(self, drop_existing: bool = False):
        """Create database tables"""
        
        try:
            if drop_existing:
                logger.warning("Dropping existing tables")
                Base.metadata.drop_all(self.engine)
            
            logger.info("Creating database tables")
            Base.metadata.create_all(self.engine)
            
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session context manager"""
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def execute_raw(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Execute raw SQL query"""
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            return result
    
    def get_table_stats(self) -> Dict[str, int]:
        """Get count of records in each table"""
        
        stats = {}
        
        with self.get_session() as session:
            for table in Base.metadata.tables.keys():
                count = session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()
                stats[table] = count
        
        return stats
    
    def vacuum_database(self):
        """Optimize database (mainly for SQLite)"""
        
        if self.db_type == 'sqlite':
            logger.info("Vacuuming SQLite database")
            with self.engine.connect() as conn:
                conn.execute(text("VACUUM"))
                conn.commit()
        elif self.db_type == 'postgresql':
            logger.info("Running PostgreSQL VACUUM ANALYZE")
            with self.engine.connect() as conn:
                conn.execute(text("VACUUM ANALYZE"))
                conn.commit()
    
    def backup_database(self, backup_path: Optional[str] = None):
        """Backup database (SQLite only)"""
        
        if self.db_type != 'sqlite':
            logger.warning("Backup only supported for SQLite")
            return
        
        import sqlite3
        import shutil
        from datetime import datetime
        
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = str(DATA_DIR / f'backup_{timestamp}.db')
        
        # Get the database file path from connection string
        db_path = self.connection_string.replace('sqlite:///', '')
        
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        
        self.engine.dispose()
        logger.info("Database connection closed")
