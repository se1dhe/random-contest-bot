"""
Run Alembic migrations with a PostgreSQL advisory lock.
"""
import asyncio
import os
import subprocess
import sys

import asyncpg

from shared.config import config


LOCK_KEY = 8687411833


def asyncpg_dsn() -> str:
    dsn = config.database_url
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return dsn


async def connect_with_retry(max_attempts: int = 60) -> asyncpg.Connection:
    dsn = asyncpg_dsn()
    for attempt in range(1, max_attempts + 1):
        try:
            return await asyncpg.connect(dsn=dsn)
        except Exception as exc:
            if attempt == max_attempts:
                raise
            print(f"PostgreSQL недоступен, попытка {attempt}/{max_attempts}: {exc}", flush=True)
            await asyncio.sleep(2)
    raise RuntimeError("PostgreSQL connection retry loop exhausted")


async def main() -> int:
    conn = await connect_with_retry()
    try:
        print("PostgreSQL готов, ожидаем advisory lock для миграций...", flush=True)
        await conn.execute("SELECT pg_advisory_lock($1)", LOCK_KEY)
        print("Lock для миграций получен", flush=True)

        result = subprocess.run(
            ["alembic", "-c", "database/alembic.ini", "upgrade", "head"],
            env=os.environ.copy(),
            check=False,
        )
        return result.returncode
    finally:
        try:
            await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_KEY)
        finally:
            await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
