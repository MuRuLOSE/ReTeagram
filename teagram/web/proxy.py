#                            ██╗████████╗███████╗██╗░░░░░░█████╗░██╗░░░██╗███████╗
#                            ██║╚══██╔══╝╚════██║██║░░░░░██╔══██╗╚██╗░██╔╝╚════██║
#                            ██║░░░██║░░░░░███╔═╝██║░░░░░███████║░╚████╔╝░░░███╔═╝
#                            ██║░░░██║░░░██╔══╝░░██║░░░░░██╔══██║░░╚██╔╝░░██╔══╝░░
#                            ██║░░░██║░░░███████╗███████╗██║░░██║░░░██║░░░███████╗
#                            ╚═╝░░░╚═╝░░░╚══════╝╚══════╝╚═╝░░╚═╝░░░╚═╝░░░╚══════╝
#                                            https://t.me/itzlayz
#
#                                    🔒 Licensed under the Apache License
#                                 https://www.apache.org/licenses/LICENSE-2.0

import os
import re
import typing

import atexit
import asyncio

import logging

logger = logging.getLogger(__name__)


class ProxyTunnel:
    def __init__(self, port: int, proxy_created: asyncio.Event, *args, **kwargs):
        self.stream = None

        self.port = port
        self.proxy_created = proxy_created

        self.proxies = [
            (
                "ssh -o StrictHostKeyChecking=no -R 80:localhost:{} serveo.net",
                r"Forwarding HTTP traffic from (https://[^\s]+)",
            ),
            (
                "ssh -o StrictHostKeyChecking=no -R 80:localhost:{} nokey@localhost.run",
                r"tunneled.*?(https:\/\/.+)",
            ),
        ]

        super().__init__(*args, **kwargs)

    def terminate(self):
        try:
            self.stream.terminate()
        except Exception as error:
            return False

        logger.debug("Stream terminated")

        return True

    async def create_proxy_tunnel(self, proxy: typing.Tuple[str, str]):
        logger.info("Creating proxy tunnel...")

        ssh_command = proxy[0].format(self.port)
        url_pattern = proxy[1]

        self.stream = await asyncio.create_subprocess_shell(
            ssh_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        url = ""

        async def get_url():
            while True:
                line = await self.stream.stdout.readline()
                if not line:
                    break
                line = line.decode()
                logger.debug(f"SSH output: {line}")

                if match := re.search(url_pattern, line):
                    nonlocal url
                    url = match[1]

                    if not self.proxy_created.is_set():
                        self.proxy_created.set()

        asyncio.ensure_future(get_url())
        try:
            await asyncio.wait_for(self.proxy_created.wait(), 10)
        except Exception:
            pass

        if url:
            atexit.register(lambda: os.system(f'kill $(pgrep -f "{ssh_command}")'))

        return url

    async def get_proxy(self):
        for i, proxy in enumerate(self.proxies):
            url = await self.create_proxy_tunnel(proxy)
            if url:
                logger.info(f"Successfully created proxy: {url}")
                return url

            if i == len(self.proxies) - 1:
                logger.error(f"Couldn't create proxy. http://localhost:{self.port}")
                return None

            logger.error("Couldn't create proxy, trying another one...")
