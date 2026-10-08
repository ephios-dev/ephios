import ipaddress
import socket
from urllib.parse import urlparse


def url_points_to_public_ip(raw_url: str) -> bool:
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        addrinfo = socket.getaddrinfo(parsed.hostname, None)
        for entry in addrinfo:
            ip_addr = ipaddress.ip_address(entry[4][0])
            if not ip_addr.is_global:
                return False
    except (socket.gaierror, ValueError):
        return False
    return True
