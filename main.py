#!/usr/bin/env python3
"""
🚀 Sonatype IQ Server Raw Report Fetcher
Entry point for the application.
"""

import sys
from iq_fetcher.config import Config
from iq_fetcher.fetcher import RawReportFetcher
from iq_fetcher.utils import logger


def main():
    logger.info("🚀 Starting fetch process…")
    cfg = Config.from_env()
    RawReportFetcher(cfg).fetch_all_reports()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("⏹️ Cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 {e}")
        sys.exit(1)
