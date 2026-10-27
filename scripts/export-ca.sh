#!/usr/bin/env bash
# Export RELab TLS Root Certificates for target devices, Android, iOS, and client environments.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORT_DIR="$ROOT/certs/export"
mkdir -p "$EXPORT_DIR/android"

printf "=== RELab CA Certificate Exporter ===\n"

# 1. Locate mitmproxy CA certificate
MITM_CA=""
for path in "$ROOT/data/mitm/mitmproxy-ca-cert.pem" "$HOME/.mitmproxy/mitmproxy-ca-cert.pem"; do
  if [[ -f "$path" ]]; then
    MITM_CA="$path"
    break
  fi
done

if [[ -z "$MITM_CA" ]]; then
  # Check inside docker volume or container if running
  if docker compose -f "$ROOT/compose.yaml" ps -q mitm >/dev/null 2>&1; then
    docker compose -f "$ROOT/compose.yaml" cp mitm:/home/mitmproxy/.mitmproxy/mitmproxy-ca-cert.pem "$EXPORT_DIR/device-mitm-ca.crt" 2>/dev/null || true
    if [[ -f "$EXPORT_DIR/device-mitm-ca.crt" ]]; then
      MITM_CA="$EXPORT_DIR/device-mitm-ca.crt"
    fi
  fi
fi

if [[ -n "$MITM_CA" && -f "$MITM_CA" ]]; then
  cp "$MITM_CA" "$EXPORT_DIR/device-mitm-ca.crt"
  printf "Found mitmproxy CA: %s\n" "$MITM_CA"

  # Generate binary DER format
  if command -v openssl >/dev/null 2>&1; then
    openssl x509 -in "$EXPORT_DIR/device-mitm-ca.crt" -outform DER -out "$EXPORT_DIR/device-mitm-ca.der" 2>/dev/null || true
    
    # Generate Android system cert hash format (<hash>.0)
    hash=$(openssl x509 -inform PEM -subject_hash_old -in "$EXPORT_DIR/device-mitm-ca.crt" 2>/dev/null | head -n1 || true)
    if [[ -n "$hash" ]]; then
      cp "$EXPORT_DIR/device-mitm-ca.crt" "$EXPORT_DIR/android/${hash}.0"
      printf "Exported Android system cert: %s/android/%s.0\n" "$EXPORT_DIR" "$hash"
    fi
  fi
  printf "Exported PEM: %s/device-mitm-ca.crt\n" "$EXPORT_DIR"
  printf "Exported DER: %s/device-mitm-ca.der\n" "$EXPORT_DIR"
else
  printf "Notice: mitmproxy CA certificate not found yet. It is generated when mitm starts.\n"
fi

# 2. Check lab edge server certificate
if [[ -f "$ROOT/certs/server.crt" ]]; then
  cp "$ROOT/certs/server.crt" "$EXPORT_DIR/device-edge-server.crt"
  printf "Exported Edge cert: %s/device-edge-server.crt\n" "$EXPORT_DIR"
fi

cat <<EOF

===================================================================
                   Target Installation Instructions
===================================================================

[1] Android (System Store - Rooted/Magisk):
    adb root
    adb remount
    adb push $EXPORT_DIR/android/*.0 /system/etc/security/cacerts/
    adb shell chmod 644 /system/etc/security/cacerts/*.0
    adb reboot

[2] Android (User Store - Unrooted):
    Push device-mitm-ca.crt to device storage:
    adb push $EXPORT_DIR/device-mitm-ca.crt /sdcard/Download/
    Install via: Settings -> Security -> Encryption & credentials -> Install a certificate -> CA certificate.

[3] Linux / Debian Host (Client testing):
    sudo cp $EXPORT_DIR/device-mitm-ca.crt /usr/local/share/ca-certificates/
    sudo update-ca-certificates

[4] Python / Curl Client Testing:
    export SSL_CERT_FILE=$EXPORT_DIR/device-mitm-ca.crt
    export REQUESTS_CA_BUNDLE=$EXPORT_DIR/device-mitm-ca.crt
    curl --cacert $EXPORT_DIR/device-mitm-ca.crt https://device.example.test/

[5] MCP Integration:
    With certificates installed on the target device, HTTPS flows will be cleanly
    decrypted and surfaced in 'device-mitm' (port 8302) and 'device-api' (port 8090).
===================================================================
EOF
