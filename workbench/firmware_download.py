"""Conservative, size-limited HTTPS firmware acquisition for user-approved public URLs.

No credentials, proxies, private IPs, link-local IPs, Unix sockets, or cross-protocol
redirects. Connections are pinned to the IP addresses checked before TLS negotiation.
"""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote

MAX_BYTES = 100 * 1024 * 1024
CHUNK = 64 * 1024

class DownloadError(ValueError):
    pass


def _destination_name(url: str, provided: str | None) -> str:
    name = provided or unquote(urlsplit(url).path.rsplit('/', 1)[-1]) or 'firmware.bin'
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}', name) or '..' in name or name.startswith('.'):
        raise DownloadError('Invalid filename: use an ordinary basename without paths')
    if name.endswith('.json') or name.endswith('.part'):
        raise DownloadError('Choose a firmware filename rather than a metadata/temporary suffix')
    return name


def _resolve_public_https(url: str):
    if len(url) > 4096 or any(ord(c) < 32 for c in url):
        raise DownloadError('Invalid URL')
    parts = urlsplit(url)
    if parts.scheme.lower() != 'https' or not parts.hostname or parts.username is not None or parts.password is not None:
        raise DownloadError('Only public HTTPS URLs without embedded credentials are allowed')
    if parts.fragment:
        raise DownloadError('URL fragments are not allowed')
    try:
        port = parts.port or 443
    except ValueError as exc:
        raise DownloadError('Invalid URL port') from exc
    if port != 443:
        raise DownloadError('Only HTTPS port 443 is supported')
    hostname = parts.hostname
    try:
        answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as exc:
        raise DownloadError('Cannot resolve download host') from exc
    addresses = list(dict.fromkeys(answer[4][0] for answer in answers))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise DownloadError('Download host resolves to a private, local, reserved, or non-global IP')
    return parts, hostname, port, addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, port: int, addresses: list[str]):
        super().__init__(hostname, port=port, timeout=15, context=ssl.create_default_context())
        self.addresses = addresses

    def connect(self):
        last_error = None
        for address in self.addresses:
            try:
                raw = socket.create_connection((address, self.port), timeout=self.timeout)
                try:
                    self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
                except Exception:
                    raw.close()
                    raise
                return
            except (OSError, ssl.SSLError) as exc:
                last_error = exc
        raise DownloadError(f'TLS connection failed: {type(last_error).__name__}')


def download_firmware(url: str, directory: Path, *, filename: str | None = None,
                      expected_sha256: str | None = None, max_bytes: int = MAX_BYTES) -> dict:
    """Download an approved public HTTPS firmware image, atomically, with SHA-256."""
    if not isinstance(url, str):
        raise DownloadError('URL must be a string')
    if expected_sha256 is not None and not re.fullmatch(r'[a-fA-F0-9]{64}', expected_sha256):
        raise DownloadError('Expected SHA-256 must be exactly 64 hex digits')
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_BYTES:
        raise DownloadError('max_bytes must be within 1..104857600')
    name = _destination_name(url, filename)
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    # Never follow symlinks or overwrite existing files. Requires a private destination folder.
    if (directory / name).exists() or (directory / (name + '.json')).exists():
        raise DownloadError('Filename already exists; choose a different name')
    current = url
    history = []
    for hop in range(5):
        parts, host, port, addresses = _resolve_public_https(current)
        conn = PinnedHTTPSConnection(host, port, addresses)
        path = (parts.path or '/') + (('?' + parts.query) if parts.query else '')
        # Query strings are intentionally NOT written to provenance metadata.
        history.append(urlunsplit((parts.scheme, parts.netloc, parts.path, '', '')))
        try:
            conn.request('GET', path, headers={'User-Agent': 'DeviceRELab-FirmwareResearch/1.0', 'Accept': 'application/octet-stream', 'Connection': 'close'})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location:
                    raise DownloadError('Redirect without Location')
                current = urljoin(current, location)
                continue
            if response.status != 200:
                raise DownloadError(f'Firmware server returned HTTP {response.status}')
            content_length = response.getheader('Content-Length')
            if content_length:
                try:
                    size = int(content_length)
                except ValueError as exc:
                    raise DownloadError('Invalid Content-Length') from exc
                if size > max_bytes:
                    raise DownloadError('Firmware exceeds maximum permitted size')
            content_type = (response.getheader('Content-Type') or '').split(';')[0].strip().lower()
            if content_type in ('text/html', 'application/xhtml+xml'):
                raise DownloadError('URL appears to be a web page, not a firmware image')
            fd, tmp = tempfile.mkstemp(dir=directory, prefix='.firmware-', suffix='.part')
            total = 0
            digest = hashlib.sha256()
            try:
                with os.fdopen(fd, 'wb') as stream:
                    while True:
                        chunk = response.read(CHUNK)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_bytes:
                            raise DownloadError('Firmware exceeds maximum permitted size')
                        stream.write(chunk)
                        digest.update(chunk)
                if not total:
                    raise DownloadError('Firmware download is empty')
                checksum = digest.hexdigest()
                if expected_sha256 and checksum != expected_sha256.lower():
                    raise DownloadError('SHA-256 mismatch; downloaded data discarded')
                output = directory / name
                # Exclusive creation prevents overwriting, including preexisting symlinks.
                with output.open('xb') as dest, open(tmp, 'rb') as src:
                    while (chunk := src.read(CHUNK)):
                        dest.write(chunk)
                result = {'filename': name, 'size': total, 'sha256': checksum,
                          'downloaded_at': datetime.now(timezone.utc).isoformat(),
                          'source': history[-1], 'redirects': history[:-1],
                          'checksum_verified': bool(expected_sha256), 'source_trust_verified': False,
                          'warning': 'Acquisition and hash validation do not establish firmware authenticity.'}
                (directory / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
                return result
            finally:
                Path(tmp).unlink(missing_ok=True)
        finally:
            conn.close()
    raise DownloadError('Too many redirects')
