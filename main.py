#!/usr/bin/env python3
"""
🚀 Sonatype IQ Server Raw Report Fetcher
Fetches raw scan reports from all applications in IQ Server and saves them as CSV files.
"""

import os
import sys
import json
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator, HttpUrl, ValidationInfo
import requests
import logging
from error_handler import ErrorHandler


# Simplified models - only what we actually need
class Application(BaseModel):
    id: str
    publicId: str
    name: str

    class Config:
        extra = "allow"


class ReportInfo(BaseModel):
    reportId: Optional[str] = None
    scanId: Optional[str] = None
    reportDataUrl: Optional[str] = None

    class Config:
        extra = "allow"


# Utility: get base_dir and resolve_path
base_dir = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(__file__)
)


def resolve_path(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(base_dir, path)


# Load .env
load_dotenv(dotenv_path=resolve_path("config/.env"))


# Terminal colors
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


# Pretty logging with more emojis and life!
class PrettyFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        if record.levelname == "INFO":
            if "✅" in msg or "✓" in msg or "Successfully" in msg:
                return f"{Colors.GREEN}{msg}{Colors.END}"
            if "❌" in msg or "✗" in msg or "Failed" in msg:
                return f"{Colors.RED}{msg}{Colors.END}"
            if "🔍" in msg or "Found" in msg or "Fetching" in msg:
                return f"{Colors.CYAN}{Colors.BOLD}{msg}{Colors.END}"
            if "🎉" in msg or "🏆" in msg or "completed" in msg:
                return f"{Colors.PURPLE}{Colors.BOLD}{msg}{Colors.END}"
            if "🚀" in msg or "Starting" in msg or "Welcome" in msg:
                return f"{Colors.BLUE}{Colors.BOLD}{msg}{Colors.END}"
            return f"{Colors.BLUE}{msg}{Colors.END}"
        if record.levelname == "ERROR":
            return f"{Colors.RED}{Colors.BOLD}{msg}{Colors.END}"
        if record.levelname == "WARNING":
            return f"{Colors.YELLOW}{Colors.BOLD}{msg}{Colors.END}"
        return msg


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(PrettyFormatter())
logger.addHandler(handler)
logger.propagate = False


class IQServerError(Exception):
    pass


class Config(BaseModel):
    """
    Configuration for connecting to the IQ Server and output settings.
    """

    iq_server_url: HttpUrl
    iq_username: str
    iq_password: str
    organization_id: Optional[str] = None
    output_dir: str = "raw_reports"

    @field_validator("iq_username", "iq_password")
    @classmethod
    def not_empty(cls, v: Any, info: ValidationInfo) -> str:
        if not v or not str(v).strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return str(v)

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables with Pydantic validation.
        """
        url = os.getenv("IQ_SERVER_URL", "").rstrip("/")
        user = os.getenv("IQ_USERNAME", "")
        pwd = os.getenv("IQ_PASSWORD", "")
        org = os.getenv("ORGANIZATION_ID")
        out = os.getenv("OUTPUT_DIR", "raw_reports")

        # Let Pydantic handle all validation
        return cls(
            iq_server_url=url,  # type: ignore[arg-type]
            iq_username=user,
            iq_password=pwd,
            organization_id=org,
            output_dir=out,
        )


class IQServerClient:
    """Simple IQ Server API client with error handling built-in."""

    def __init__(self, url: str, user: str, pwd: str) -> None:
        self.base_url = url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (user, pwd)
        self.session.headers.update({"Accept": "application/json"})

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make HTTP requests with error handling."""
        url = f"{self.base_url}{endpoint}"
        try:
            r = self.session.request(method, url, **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            logger.error(f"{method} {endpoint} failed: {e}")
            raise IQServerError(f"{method} {endpoint} failed: {e}")

    @ErrorHandler.handle_api_error
    def get_applications(
        self, org_id: Optional[str] = None
    ) -> Optional[List[Application]]:
        """Fetch all applications and return as validated models."""
        ep = (
            f"/api/v2/applications/organization/{org_id}"
            if org_id
            else "/api/v2/applications"
        )
        response = self._request("GET", ep)
        apps_data = response.json().get("applications", [])
        return [Application(**app) for app in apps_data]

    @ErrorHandler.handle_api_error
    def get_latest_report_info(self, app_id: str) -> Optional[ReportInfo]:
        """Get the latest report info for an application."""
        response = self._request("GET", f"/api/v2/reports/applications/{app_id}")
        reports = response.json()
        return ReportInfo(**reports[0]) if reports else None

    @ErrorHandler.handle_api_error
    def get_raw_report(
        self, public_id: str, report_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch raw report data."""
        response = self._request(
            "GET", f"/api/v2/applications/{public_id}/reports/{report_id}/raw"
        )
        return response.json()


class RawReportFetcher:
    """🎯 Fetches and saves IQ Server reports as CSV files."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.iq = IQServerClient(
            str(config.iq_server_url), config.iq_username, config.iq_password
        )
        self.output_path = Path(resolve_path(config.output_dir))
        self.output_path.mkdir(parents=True, exist_ok=True)

    def _extract_report_id(self, info: ReportInfo) -> Optional[str]:
        """Extract report ID from report info."""
        if info.reportDataUrl:
            try:
                return info.reportDataUrl.split("/reports/")[1].split("/")[0]
            except Exception:
                pass
        return info.scanId or info.reportId

    @ErrorHandler.handle_file_error
    def _save_as_csv(
        self, public_id: str, report_id: str, data: Dict[str, Any]
    ) -> bool:
        """Save report data as CSV file."""
        filename = f"report_{public_id}_{report_id}_raw.csv"
        filepath = self.output_path / filename

        components = data.get("components", [])
        if not components:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["No components found"])
            return True

        try:
            # Try pandas first for better handling
            import pandas as pd

            df = pd.json_normalize(components)
            for col in df.columns:
                if df[col].dtype == "object":
                    df[col] = df[col].apply(
                        lambda x: (
                            json.dumps(x)
                            if isinstance(x, (dict, list))
                            else str(x)
                            if x is not None
                            else ""
                        )
                    )
            df.to_csv(filepath, index=False, encoding="utf-8")
        except ImportError:
            # Fallback to manual CSV
            self._save_csv_manual(components, filepath)
        return True

    def _save_csv_manual(
        self, components: List[Dict[str, Any]], filepath: Path
    ) -> None:
        """Manual CSV writing fallback."""
        csv_data = []
        for c in components:
            if len(c) == 1 and not c.get("swid"):
                continue
            security_issues = c.get("securityData", {}).get("securityIssues", [])
            row = {
                "Package URL": c.get("packageUrl", ""),
                "Display Name": c.get("displayName", ""),
                "Security Issues Count": len(security_issues),
                "License Data": (
                    json.dumps(c.get("licenseData", {})) if c.get("licenseData") else ""
                ),
                "Security Issues": (
                    json.dumps(security_issues) if security_issues else ""
                ),
            }
            csv_data.append(row)

        if csv_data:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(csv_data[0].keys()))
                writer.writeheader()
                writer.writerows(csv_data)

    def _fetch_app_report(self, app: Application, idx: int, total: int) -> bool:
        """Fetch and save report for a single application."""
        try:
            logger.info(f"🔍 [{idx}/{total}] Processing {app.name}...")

            info = self.iq.get_latest_report_info(app.id)
            if not info:
                logger.warning(f"⚠️  [{idx}/{total}] No reports found for {app.name}")
                return False

            report_id = self._extract_report_id(info)
            if not report_id:
                logger.warning(f"⚠️  [{idx}/{total}] No report ID for {app.name}")
                return False

            data = self.iq.get_raw_report(app.publicId, report_id)
            if not data:
                logger.warning(f"⚠️  [{idx}/{total}] No report data for {app.name}")
                return False

            if self._save_as_csv(app.publicId, report_id, data):
                logger.info(f"✅ [{idx}/{total}] Successfully saved {app.name}")
                return True
            else:
                logger.warning(f"💾 [{idx}/{total}] Failed to save {app.name}")
                return False

        except Exception as e:
            logger.error(f"❌ [{idx}/{total}] Error processing {app.name}: {e}")
            return False

    def get_applications(self) -> List[Application]:
        """Fetch and display applications."""
        logger.info("🔍 Fetching applications from IQ Server...")
        apps = self.iq.get_applications(self.config.organization_id)

        if not apps:
            logger.error("❌ Failed to fetch applications or no applications found")
            return []

        logger.info(f"🎯 Found {len(apps)} applications!")

        if apps:
            logger.info("📋 Applications preview:")
            for i, app in enumerate(apps[:5], 1):
                logger.info(f"   {i}. {app.name} ({app.publicId})")
            if len(apps) > 5:
                logger.info(f"   ... and {len(apps) - 5} more! 🚀")

        return apps

    def fetch_all_reports(self) -> None:
        """Main method to fetch all reports."""
        logger.info("🚀 Starting raw report fetch process...")
        logger.info(f"📁 Output directory: {self.output_path.absolute()}")

        apps = self.get_applications()
        if not apps:
            logger.warning("😞 No applications to process")
            return

        total = len(apps)
        success_count = 0

        logger.info(f"⚡ Processing {total} applications...")

        for i, app in enumerate(apps, 1):
            if self._fetch_app_report(app, i, total):
                success_count += 1

        # Final summary with emojis
        logger.info("=" * 50)
        logger.info(f"🎉 Processing completed!")
        logger.info(f"✅ Successfully processed: {success_count}/{total}")

        if success_count == total:
            logger.info("🏆 Perfect! All reports fetched successfully! 🎊")
        elif success_count > 0:
            failed = total - success_count
            logger.info(f"⚠️  {failed} reports failed to fetch")
        else:
            logger.error("😞 No reports were successfully fetched")


@ErrorHandler.handle_config_error
def main() -> None:
    """🚀 Main entry point - Let's fetch some reports!"""
    try:
        logger.info("🔧 Loading configuration...")
        config = Config.from_env()

        logger.info("🎯 Initializing report fetcher...")
        fetcher = RawReportFetcher(config)

        fetcher.fetch_all_reports()

    except KeyboardInterrupt:
        logger.warning("⏹️  Cancelled by user - See you next time!")
        sys.exit(0)
    except (ValueError, IQServerError) as e:
        logger.error(f"💥 Configuration/Server error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    logger.info("🚀 Welcome to the Sonatype IQ Server Raw Report Fetcher!")
    logger.info("=" * 60)
    main()
