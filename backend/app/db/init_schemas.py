import asyncio
import os
from pathlib import Path
from db.surreal_conn import SurrealConn

async def load_schemas():
    """
    Load SurrealDB schemas from schemas.surql file.
    Executes statements sequentially.
    """
    print("🔄 Initializing SurrealDB schemas...")
    
    # Get database connection
    conn = SurrealConn()
    try:
        db = await conn.getting_db()
    except Exception as e:
        print(f"❌ Failed to connect to SurrealDB: {e}")
        return

    # Read schema file
    schema_path = Path(__file__).parent / "schemas.surql"
    if not schema_path.exists():
        print(f"❌ Schema file not found at: {schema_path}")
        return
        
    with open(schema_path, "r", encoding="utf-8") as f:
        surql_content = f.read()

    # Split by semicolon to get individual statements roughly
    # Note: This is a simple split. Complex statements with semicolons in strings might need better parsing,
    # but for our schema file it should be sufficient as we use DEFINE TABLE ...; format.
    # A better approach for robust execution allows executing the whole block if the driver supports it.
    # The python surrealdb SDK usually supports .query() which can take multiple statements.
    
    try:
        print(f"📂 Reading schema from {schema_path}")
        # Execute the entire script at once
        await db.query(surql_content)
        print("✅ Schemas applied successfully")
    except Exception as e:
        print(f"❌ Error applying schemas: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(load_schemas())
