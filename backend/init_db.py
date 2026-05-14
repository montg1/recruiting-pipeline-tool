"""
Database Initialization Script for Supabase (or any PostgreSQL DB)

This script safely creates the tables and triggers defined in schema.sql
by connecting directly to the database.

IMPORTANT: When running schema changes on Supabase, it is highly recommended
to use the Direct Connection URL (port 5432), NOT the connection pooler (port 6543).
"""

import os
from sqlalchemy import text
from database import engine

# Path to the raw SQL schema file
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")

def init_db():
    print(f"Connecting to Database...")
    
    # Read the SQL file
    if not os.path.exists(SCHEMA_FILE):
        print(f"Error: {SCHEMA_FILE} not found!")
        return

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()

    print("Running schema.sql on the database...")
    
    with engine.begin() as connection:
        # Execute the raw SQL schema (this includes tables, indexes, and TRIGGERS)
        # SQLAlchemy's Base.metadata.create_all() does NOT create triggers, 
        # so executing the raw SQL is the safest approach for this project.
        connection.execute(text(sql_script))
        
    print("✅ Database initialized successfully!")
    print("Tables, indexes, and triggers have been created.")

if __name__ == "__main__":
    init_db()
