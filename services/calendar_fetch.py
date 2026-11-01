"""Fetch bounded public HTTPS calendars without allowing internal network access."""
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit

MAX_BYTES = 1024 * 1024


def _target(url):
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 33 for c in url):
        raise ValueError('Use a complete HTTPS calendar URL.')
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.fragment or parsed.port not in (None, 443)):
        raise ValueError('Use a direct HTTPS calendar URL without a username or password.')
    host = parsed.hostname.encode('idna').decode('ascii')
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    def allowed(address):
        ip = ipaddress.ip_address(address)
        return ip.is_global and not (getattr(ip, 'ipv4_mapped', None) or getattr(ip, 'sixtofour', None) or getattr(ip, 'teredo', None))
    if not addresses or any(not allowed(a[4][0]) for a in addresses):
        raise ValueError('The calendar must be hosted at a public internet address.')
    return host, addresses[0], (parsed.path or '/') + ('?' + parsed.query if parsed.query else '')


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=10, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        # Connect to the already checked address; TLS still verifies the original hostname.
        family, kind, proto, _, sockaddr = self.address
        raw = socket.socket(family, kind, proto)
        try:
            raw.settimeout(self.timeout)
            raw.connect(sockaddr)
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def fetch_calendar(url):
    connection = None
    try:
        host, address, path = _target(url)
        connection = _PinnedHTTPS(host, address)
        started = time.monotonic()
        connection.request('GET', path, headers={'Accept': 'text/calendar', 'Accept-Encoding': 'identity',
                                                'User-Agent': 'StudentSuccess-Calendar-Import/1.0'})
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise ValueError('This URL redirects. Paste the final HTTPS calendar download URL instead.')
        if response.status != 200:
            raise ValueError('The calendar could not be downloaded. Check that the link allows calendar access.')
        if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
            raise ValueError('Use an uncompressed .ics calendar link or upload the downloaded file.')
        length = response.getheader('Content-Length')
        if length and int(length) > MAX_BYTES:
            raise ValueError('Calendar must be at most 1 MB.')
        raw = bytearray()
        while len(raw) <= MAX_BYTES:
            if time.monotonic() - started > 20:
                raise ValueError('The calendar took too long to download. Try again or upload a file.')
            chunk = response.read1(min(65536, MAX_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        if len(raw) > MAX_BYTES:
            raise ValueError('Calendar must be at most 1 MB.')
        return bytes(raw)
    except (OSError, http.client.HTTPException, UnicodeError):
        raise ValueError('The calendar could not be downloaded. Check the link or upload an .ics file.') from None
    finally:
        if connection:
            connection.close()
