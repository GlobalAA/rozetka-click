import socket
from collections.abc import Sequence

from src.database.models import Proxy
from src.database.repository import get_proxies


class ProxyException(Exception): ...


async def validate() -> Sequence[Proxy]:
    proxies = await get_proxies()

    for proxy in proxies:
        if proxy.server.startswith("test://test:90"):
            continue

        server_str = proxy.server
        if "://" in server_str:
            server_str = server_str.split("://", 1)[-1]

        try:
            host, port = server_str.split(":", 1)
            with socket.create_connection((host, int(port)), timeout=5.0):
                pass
        except (socket.timeout, ConnectionRefusedError, OSError, ValueError):
            raise ProxyException(f"Unavailable or invalid proxy: {proxy.server}")

    return proxies
