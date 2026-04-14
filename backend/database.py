import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./multi_agent_ops.db")

engine = create_engine(
    DATABASE_URL.replace("+aiosqlite", ""),
    connect_args={"check_same_thread": False},
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()



async def get_db():
    """Dependency for FastAPI routes to get DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def init_db():
    """Initialize database tables (sync version for startup)."""
    from models import Store, WorkflowInstance, AgentRun, EventLog, Alert, Report
    Base.metadata.create_all(bind=engine)
