"""YARA and secret/credential scanning MCP server for IoT artifacts."""
from __future__ import annotations
import math, os, pathlib, re
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Device YARA & Secrets Scanner MCP", docs_url=None)
ROOTS = {
    "firmware": pathlib.Path("/firmware"),
    "extracted": pathlib.Path("/extracted"),
    "analysis": pathlib.Path("/analysis"),
}

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "jwt_token": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_api_key": re.compile(r"(?:api_key|apikey|secret|password)[\s:=]+['\"]([A-Za-z0-9_=-]{16,64})['\"]", re.IGNORECASE),
    "hardcoded_ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
}

@app.get("/health", operation_id="yara_status")
def yara_status() -> dict:
    has_yara = False
    try:
        import yara
        has_yara = True
    except ImportError:
        pass
    return {"status": "ready", "yara_c_bindings": has_yara, "built_in_detectors": list(SECRET_PATTERNS.keys())}

@app.get("/scan_secrets", operation_id="secret_scan")
def secret_scan(category: str = "firmware", subpath: str = "", max_matches: int = 50) -> dict:
    root = ROOTS.get(category)
    if not root or not root.exists():
        raise HTTPException(400, f"Invalid category: {category}")
    target = (root / subpath.lstrip("/")).resolve()
    if not target.is_relative_to(root.resolve()):
        raise HTTPException(403, "Access outside allowed root path")
    
    matches = []
    files_to_scan = [target] if target.is_file() else list(target.rglob("*"))[:50]
    for p in files_to_scan:
        if not p.is_file() or p.stat().st_size > 50 * 1024 * 1024:
            continue
        try:
            content = p.read_bytes()
            text = content.decode("utf-8", errors="ignore")
            for name, pattern in SECRET_PATTERNS.items():
                for m in pattern.finditer(text):
                    val = m.group(0)
                    # Redact part of the secret if sensitive
                    redacted = val[:6] + "..." + val[-4:] if len(val) > 12 else "[MATCH]"
                    matches.append({"file": str(p.name), "detector": name, "redacted_value": redacted, "offset": m.start()})
                    if len(matches) >= max_matches:
                        break
                if len(matches) >= max_matches:
                    break
        except Exception:
            continue
        if len(matches) >= max_matches:
            break
            
    return {"category": category, "path": subpath, "scanned_files": len(files_to_scan), "match_count": len(matches), "matches": matches}

@app.get("/rules", operation_id="yara_list_rules")
def yara_list_rules() -> dict:
    return {
        "builtin_detectors": list(SECRET_PATTERNS.keys()),
        "description": "High-confidence signature matches for cryptographic keys, tokens, and hardcoded secrets.",
    }

mcp = FastApiMCP(app, name="Device YARA & Secrets Scanner MCP", include_operations=["yara_status", "secret_scan", "yara_list_rules"])
mcp.mount_http(mount_path="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

