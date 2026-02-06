"""Seed default users (admin, faculty). Run after DB is up: python -m scripts.seed_users"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.core.security import get_password_hash
from app.db.models import User
from app.core.config import get_settings

settings = get_settings()
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif "sqlite" in db_url:
    pass  # use as-is


async def seed():
    engine = create_async_engine(db_url)
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        for email, password, full_name, role in [
            ("admin@university.edu", "admin123", "Admin User", "admin"),
            ("faculty@university.edu", "faculty123", "Faculty Demo", "faculty"),
        ]:
            r = await session.execute(select(User).where(User.email == email))
            if r.scalar_one_or_none():
                print(f"User {email} already exists")
                continue
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=role,
            )
            session.add(user)
            print(f"Created user {email} ({role})")
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
