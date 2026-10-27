"""Zeek network security monitoring and protocol extraction MCP server."""
from __future__ import annotations
import csv, json, os, pathlib, re, shutil, subprocess
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Device Zeek Protocol Analysis MCP", docs_url=None)
PCAP_ROOT = pathlib.Path(os.environ.get("PCAP_PATH", "/captures")).resolve()
ZEEK_OUTPUT_ROOT = pathlib.Path(os.environ.get("ZEEK_OUT", "/data/zeek")).resolve()

def _safe_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", name) or ".." in name:
        raise HTTPException(400, "Invalid filename")
    return name

@app.get("/health", operation_id="zeek_status")
def zeek_status() -> dict:
    has_zeek = shutil.which("zeek") is not None
    return {"status": "ready" if has_zeek else "zeek_not_installed", "zeek_available": has_zeek}

@app.post("/analyze/{pcap_name}", operation_id="zeek_analyze")
def zeek_analyze(pcap_name: str) -> dict:
    fname = _safe_name(pcap_name)
    target = (PCAP_ROOT / fname).resolve()
    if not target.is_relative_to(PCAP_ROOT) or not target.is_file():
        raise HTTPException(404, f"PCAP not found: {fname}")
    
    out_dir = ZEEK_OUTPUT_ROOT / fname
    out_dir.mkdir(parents=True, exist_ok=True)
    
    zeek_bin = shutil.which("zeek")
    if not zeek_bin:
        raise HTTPException(500, "Zeek binary not found")
        
    try:
        proc = subprocess.run([zeek_bin, "-C", "-r", str(target), "LogAscii::use_json=T"], cwd=str(out_dir), capture_output=True, text=True, timeout=120)
        logs = [p.name for p in out_dir.glob("*.log")]
        return {"pcap": fname, "returncode": proc.returncode, "logs_generated": logs, "stderr": proc.stderr[:1000]}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Zeek analysis timed out after 120s")

@app.get("/logs/{pcap_name}", operation_id="zeek_list_logs")
def zeek_list_logs(pcap_name: str) -> dict:
    fname = _safe_name(pcap_name)
    out_dir = ZEEK_OUTPUT_ROOT / fname
    if not out_dir.exists():
        return {"pcap": fname, "analyzed": False, "logs": []}
    logs = [p.stem for p in out_dir.glob("*.log")]
    return {"pcap": fname, "analyzed": True, "logs": logs}

@app.get("/log/{pcap_name}/{log_type}", operation_id="zeek_get_log")
def zeek_get_log(pcap_name: str, log_type: str, limit: int = 100) -> dict:
    fname = _safe_name(pcap_name)
    ltype = _safe_name(log_type)
    out_dir = ZEEK_OUTPUT_ROOT / fname
    log_file = out_dir / f"{ltype}.log"
    if not log_file.is_file():
        raise HTTPException(404, f"Log {ltype}.log not found for {fname}. Run zeek_analyze first.")
    
    records = []
    with log_file.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
            elif not line.startswith("#"):
                records.append({"raw": line})
            if len(records) >= limit:
                break
                
    return {"pcap": fname, "log_type": ltype, "record_count": len(records), "records": records}

mcp = FastApiMCP(app, name="Device Zeek Protocol Analysis MCP", include_operations=["zeek_status", "zeek_analyze", "zeek_list_logs", "zeek_get_log"])
mcp.mount_http(mount_path="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

