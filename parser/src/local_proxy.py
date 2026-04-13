import asyncio
import base64
from loguru import logger

class LocalForwarder:
    def __init__(self, target_host: str, target_port: int, username: str, password: str):
        self.target_host = target_host
        self.target_port = target_port
        
        auth_str = f"{username}:{password}"
        self.auth_b64 = base64.b64encode(auth_str.encode()).decode()
        
        self.server = None
        self.port = 0

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, '127.0.0.1', 0)
        self.port = self.server.sockets[0].getsockname()[1]
        logger.info(f"Local proxy forwarder started on 127.0.0.1:{self.port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Local proxy forwarder stopped.")

    async def handle_client(self, reader, writer):
        try:
            target_reader, target_writer = await asyncio.open_connection(self.target_host, self.target_port)
        except Exception as e:
            logger.error(f"Failed to connect to upstream proxy: {e}")
            writer.close()
            return

        async def forward_client_to_target():
            first_chunk = True
            try:
                while True:
                    data = await reader.read(8192)
                    if not data:
                        break
                    
                    if first_chunk:
                        # Find the end of HTTP headers
                        header_end = data.find(b'\r\n\r\n')
                        if header_end != -1:
                            auth_header = f"Proxy-Authorization: Basic {self.auth_b64}\r\n".encode()
                            # Inject auth header
                            data = data[:header_end+2] + auth_header + data[header_end+2:]
                        first_chunk = False
                        
                    target_writer.write(data)
                    await target_writer.drain()
            except Exception:
                pass
            finally:
                target_writer.close()

        async def forward_target_to_client():
            try:
                while True:
                    data = await target_reader.read(8192)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()
            except Exception:
                pass
            finally:
                writer.close()

        asyncio.create_task(forward_client_to_target())
        asyncio.create_task(forward_target_to_client())
