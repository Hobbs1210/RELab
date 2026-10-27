"""Read-only SQLite and PostgreSQL inspection MCP server for RELab."""
from __future__ import annotations
import os, pathlib, re, sqlite3
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Device Database MCP Server", docs_url=None)

SQLITE_PATH = pathlib.Path(os.environ.get("SQLITE_PATH", "/data/requests.db"))
POSTGRES_URL = os.environ.get("RESEARCH_DATABASE_URL", "")

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|GRANT|REVOKE)\b",
    re.IGNORECASE
)

def _validate_select_only(query: str) -> str:
    cleaned = query.strip()
    if not cleaned.upper().startswith("SELECT") and not cleaned.upper().startswith("WITH"):
        raise HTTPException(400, "Only read-only SELECT / WITH queries are allowed.")
    if FORBIDDEN_SQL.search(cleaned):
        raise HTTPException(403, "Query contains prohibited SQL statements or keywords.")
    return cleaned

@app.get("/health", operation_id="db_status")
def db_status() -> dict:
    sqlite_ok = SQLITE_PATH.exists()
    pg_ok = bool(POSTGRES_URL)
    return {"sqlite_available": sqlite_ok, "postgres_configured": pg_ok}

@app.get("/tables", operation_id="db_list_tables")
def db_list_tables() -> dict:
    sqlite_tables = []
    if SQLITE_PATH.exists():
        try:
            with sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                sqlite_tables = [row[0] for row in cur.fetchall()]
        except Exception as exc:
            sqlite_tables = [f"error: {exc}"]
    
    pg_tables = []
    if POSTGRES_URL:
        try:
            import psycopg
            with psycopg.connect(POSTGRES_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                    pg_tables = [row[0] for row in cur.fetchall()]
        except Exception as exc:
            pg_tables = [f"error: {exc}"]
            
    return {"sqlite_tables": sqlite_tables, "postgres_tables": pg_tables}

@app.get("/schema/{db_type}/{table_name}", operation_id="db_table_schema")
def db_table_schema(db_type: str, table_name: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_]+", table_name):
        raise HTTPException(400, "Invalid table name")
    
    columns = []
    if db_type == "sqlite":
        if not SQLITE_PATH.exists():
            raise HTTPException(404, "SQLite DB not found")
        with sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True) as conn:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table_name});")
            for row in cur.fetchall():
                columns.append({"cid": row[0], "name": row[1], "type": row[2], "notnull": bool(row[3]), "pk": bool(row[5])})
    elif db_type == "postgres":
        if not POSTGRES_URL:
            raise HTTPException(400, "PostgreSQL not configured")
        import psycopg
        with psycopg.connect(POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name=%s;", (table_name,))
                for row in cur.fetchall():
                    columns.append({"name": row[0], "type": row[1], "nullable": row[2] == "YES"})
    else:
        raise HTTPException(400, "db_type must be 'sqlite' or 'postgres'")
        
    return {"db_type": db_type, "table": table_name, "columns": columns}

@app.get("/query/sqlite", operation_id="db_query_sqlite")
def db_query_sqlite(query: str, limit: int = 100) -> dict:
    if not SQLITE_PATH.exists():
        raise HTTPException(404, "SQLite database not present")
    safe_q = _validate_select_only(query)
    safe_limit = max(1, min(limit, 500))
    try:
        with sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(safe_q)
            rows = [dict(row) for row in cur.fetchmany(safe_limit)]
            return {"query": safe_q, "row_count": len(rows), "rows": rows}
    except Exception as exc:
        raise HTTPException(400, f"Query error: {exc}")

@app.get("/query/postgres", operation_id="db_query_postgres")
def db_query_postgres(query: str, limit: int = 100) -> dict:
    if not POSTGRES_URL:
        raise HTTPException(400, "PostgreSQL not configured")
    safe_q = _validate_select_only(query)
    safe_limit = max(1, min(limit, 500))
    try:
        import psycopg
        with psycopg.connect(POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(safe_q)
                col_names = [desc[0] for desc in cur.description] if cur.description else []
                rows = [dict(zip(col_names, row)) for row in cur.fetchmany(safe_limit)]
                return {"query": safe_q, "row_count": len(rows), "rows": rows}
    except Exception as exc:
        raise HTTPException(400, f"Query error: {exc}")

mcp = FastApiMCP(app, name="Device Database MCP Server", include_operations=["db_status", "db_list_tables", "db_table_schema", "db_query_sqlite", "db_query_postgres"])
mcp.mount_http(mount_path="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

