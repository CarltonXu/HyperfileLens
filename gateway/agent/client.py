#!/usr/bin/env python3
"""HyperFileLens Gateway Agent entry point."""

import asyncio

from hfl_gateway.main import main


if __name__ == '__main__':
    asyncio.run(main())
