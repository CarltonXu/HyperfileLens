"""Gateway agent process entry point."""

import asyncio
import logging

from .agent import GatewayAgent
from .config import GatewayConfig


def configure_logging(config: GatewayConfig) -> None:
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )


async def main() -> None:
    config = GatewayConfig.load()
    configure_logging(config)
    agent = GatewayAgent(config)
    try:
        await agent.start()
    except KeyboardInterrupt:
        logging.getLogger('gateway-agent').info('Shutting down...')
        await agent.stop()
