import asyncio
from database.session import create_db_tables

async def main():
    print("Creating database tables...")
    await create_db_tables()
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
