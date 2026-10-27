"""ADB Android companion app inspection MCP server."""
from __future__ import annotations
import os, re, shutil, subprocess
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Device ADB Companion MCP", docs_url=None)
ADB_SERVER_HOST = os.environ.get("ADB_SERVER_SOCKET", "tcp:127.0.0.1:5037")

def _adb_cmd(args: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    adb_bin = shutil.which("adb")
    if not adb_bin:
        raise HTTPException(500, "adb binary not found in container")
    full_cmd = [adb_bin]
    if "tcp:" in ADB_SERVER_HOST:
        parts = ADB_SERVER_HOST.replace("tcp:", "").split(":")
        full_cmd.extend(["-H", parts[0], "-P", parts[1] if len(parts) > 1 else "5037"])
    full_cmd.extend(args)
    try:
        return subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "ADB command timed out")

@app.get("/health", operation_id="adb_status")
def adb_status() -> dict:
    has_adb = shutil.which("adb") is not None
    return {"status": "ready" if has_adb else "adb_missing", "adb_available": has_adb, "server_socket": ADB_SERVER_HOST}

@app.get("/devices", operation_id="adb_devices")
def adb_devices() -> dict:
    proc = _adb_cmd(["devices", "-l"])
    devices = []
    for line in proc.stdout.splitlines()[1:]:
        line = line.strip()
        if line:
            parts = line.split()
            devices.append({"serial": parts[0], "status": parts[1] if len(parts) > 1 else "unknown", "details": " ".join(parts[2:])})
    return {"device_count": len(devices), "devices": devices}

@app.get("/logcat", operation_id="adb_logcat")
def adb_logcat(tag: str = "", lines: int = 100) -> dict:
    safe_lines = max(10, min(lines, 500))
    args = ["logcat", "-d", "-t", str(safe_lines)]
    if tag:
        clean_tag = re.sub(r"[^A-Za-z0-9_.-]", "", tag)[:40]
        args.extend([f"{clean_tag}:*", "*:S"])
    proc = _adb_cmd(args, timeout=15)
    return {"tag_filter": tag or "all", "lines_requested": safe_lines, "log": proc.stdout[-15000:]}

@app.get("/packages", operation_id="adb_list_packages")
def adb_list_packages(third_party_only: bool = True) -> dict:
    args = ["shell", "pm", "list", "packages"]
    if third_party_only:
        args.append("-3")
    proc = _adb_cmd(args, timeout=15)
    pkgs = [line.replace("package:", "").strip() for line in proc.stdout.splitlines() if line.startswith("package:")]
    return {"third_party_only": third_party_only, "package_count": len(pkgs), "packages": pkgs}

@app.get("/package/{package_name}", operation_id="adb_dump_package")
def adb_dump_package(package_name: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.]+", package_name):
        raise HTTPException(400, "Invalid package name format")
    proc = _adb_cmd(["shell", "dumpsys", "package", package_name], timeout=20)
    return {"package": package_name, "dump_tail": proc.stdout[:15000]}

mcp = FastApiMCP(app, name="Device ADB Companion MCP", include_operations=["adb_status", "adb_devices", "adb_logcat", "adb_list_packages", "adb_dump_package"])
mcp.mount_http(mount_path="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

