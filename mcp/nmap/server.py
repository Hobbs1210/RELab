"""Bounded Nmap network discovery MCP server for authorized lab test targets."""
from __future__ import annotations
import ipaddress, json, os, re, shutil, subprocess, xml.etree.ElementTree as ET
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Device Nmap Discovery MCP", docs_url=None)
TARGET_IP_CONFIG = os.environ.get("TARGET_IP", "192.0.2.10")

def _validate_lab_ip(ip_str: str) -> str:
    clean_ip = ip_str.strip()
    try:
        ip = ipaddress.ip_address(clean_ip)
    except ValueError:
        raise HTTPException(400, f"Invalid IPv4/IPv6 address: {clean_ip}")
    if not (ip.is_private or ip.is_loopback or clean_ip == TARGET_IP_CONFIG):
        raise HTTPException(403, f"Scanning forbidden: {clean_ip} is not a private lab IP or authorized target.")
    return clean_ip

@app.get("/health", operation_id="nmap_status")
def nmap_status() -> dict:
    has_nmap = shutil.which("nmap") is not None
    return {"status": "ready" if has_nmap else "nmap_missing", "nmap_available": has_nmap, "configured_target": TARGET_IP_CONFIG}

@app.get("/profile", operation_id="nmap_discovery_profile")
def nmap_discovery_profile() -> dict:
    return {
        "scope": "Authorized isolated device testing only",
        "configured_target": TARGET_IP_CONFIG,
        "supported_scan_types": ["ping", "quick", "services", "udp_discovery"],
        "safety_guarantee": "Strictly restricted to RFC1918/loopback addresses",
    }

@app.get("/scan", operation_id="nmap_scan_target")
def nmap_scan_target(target_ip: str = "", scan_type: str = "quick") -> dict:
    ip = _validate_lab_ip(target_ip or TARGET_IP_CONFIG)
    nmap_bin = shutil.which("nmap")
    if not nmap_bin:
        raise HTTPException(500, "nmap binary not available")
    
    cmd = [nmap_bin, "-oX", "-"]
    if scan_type == "ping":
        cmd.extend(["-sn", ip])
    elif scan_type == "services":
        cmd.extend(["-sV", "-T3", "--top-ports", "50", ip])
    elif scan_type == "udp_discovery":
        cmd.extend(["-sU", "-T3", "-p", "53,67,68,123,161,5353,1900", ip])
    else:  # quick
        cmd.extend(["-T4", "--top-ports", "100", ip])
        
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        # Parse XML
        ports = []
        host_status = "down"
        if proc.stdout.strip():
            try:
                root = ET.fromstring(proc.stdout)
                for host in root.findall("host"):
                    status = host.find("status")
                    if status is not None:
                        host_status = status.get("state", "unknown")
                    for p in host.findall(".//port"):
                        port_id = p.get("portid")
                        proto = p.get("protocol")
                        state = p.find("state").get("state") if p.find("state") is not None else "unknown"
                        service = p.find("service").get("name") if p.find("service") is not None else ""
                        ports.append({"port": port_id, "protocol": proto, "state": state, "service": service})
            except Exception:
                pass
        return {"target": ip, "scan_type": scan_type, "host_status": host_status, "open_ports": ports, "raw_summary": proc.stdout[-1000:]}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Scan timed out after 60s")

mcp = FastApiMCP(app, name="Device Nmap Discovery MCP", include_operations=["nmap_status", "nmap_discovery_profile", "nmap_scan_target"])
mcp.mount_http(mount_path="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

