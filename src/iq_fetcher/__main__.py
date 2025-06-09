#!/usr/bin/env python3
"""
🚀 Sonatype IQ Server Raw Report Fetcher
Entry point for the application.
"""

import sys
import multiprocessing
from iq_fetcher.config import Config
from iq_fetcher.fetcher import RawReportFetcher
from iq_fetcher.utils import logger


def main():
    logger.info("🚀 Starting fetch process…")
    try:
        cfg = Config.from_env()
        fetcher = RawReportFetcher(cfg)
        fetcher.fetch_all_reports()
        logger.info("✅ Fetch process completed successfully!")
    except Exception as e:
        logger.error(f"💥 Error during fetch process: {e}")
        raise


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("⏹️ Cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 {e}")
        sys.exit(1)
