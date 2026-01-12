from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    # Step Two uses create_all to be immediately runnable.
    # In a mature deployment, you'd swap this for Alembic migrations.
    Base.metadata.create_all(bind=engine)
