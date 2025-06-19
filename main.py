#!/usr/bin/env python3
"""
🚀 Sonatype IQ Server Raw Report Fetcher
Fetches raw scan reports from all applications in IQ Server and saves them as CSV files.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator, HttpUrl, ValidationInfo
import requests
import logging
import re
from error_handler import ErrorHandler
import pandas as pd


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


class Organization(BaseModel):
    id: str
    name: str
    parentOrganizationId: Optional[str] = None
    tags: List[Dict[str, Any]] = []

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

    #
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
    def get_policy_violations(
        self, public_id: str, report_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch raw report data."""
        response = self._request(
            "GET",
            f"/api/v2/applications/{public_id}/reports/{report_id}/policy?includeViolationTimes=true",
        )
        return response.json()

    @ErrorHandler.handle_api_error
    def get_organizations(self) -> List[Organization]:
        """Fetch all organizations."""
        endpoint = "/api/v2/organizations"
        response = self._request("GET", endpoint)
        organizations_data = response.json().get("organizations", [])
        return [Organization(**org) for org in organizations_data]


class RawReportFetcher:
    """🎯 Fetches and saves IQ Server reports as CSV files and consolidates them."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.iq = IQServerClient(
            str(config.iq_server_url), config.iq_username, config.iq_password
        )
        self.output_path = Path(resolve_path(config.output_dir))
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.organization_id_to_name = self._get_organization_id_to_name_mapping()

    def _get_organization_id_to_name_mapping(self) -> Dict[str, str]:
        """Fetches all organizations and creates a mapping from ID to name."""
        organizations = self.iq.get_organizations()
        return {org.id: org.name for org in organizations}

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
        """Save report data as JSON file (no CSV conversion)."""
        filename = f"report_{public_id}_{report_id}_raw.json"
        filepath = self.output_path / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
            return False

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

            data = self.iq.get_policy_violations(app.publicId, report_id)
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
        """Main method to fetch all reports and consolidate them."""
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
        logger.info("🎉 Processing completed!")
        logger.info(f"✅ Successfully processed: {success_count}/{total}")

        if success_count == total:
            logger.info("🏆 Perfect! All reports fetched successfully! 🎊")
        elif success_count > 0:
            failed = total - success_count
            logger.info(f"⚠️  {failed} reports failed to fetch")
        else:
            logger.error("😞 No reports were successfully fetched")

        # Consolidate all JSON reports into CSV as default output
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        consolidated_csv_filename = f"{timestamp}_consolidated_security_report.csv"
        consolidated_csv = Path(self.output_path.parent) / consolidated_csv_filename
        self.consolidate_reports_to_csv(consolidated_csv)

    def consolidate_reports_to_csv(self, output_csv_path: Path) -> None:
        """Consolidate all JSON reports into a single CSV as specified."""
        json_files = list(self.output_path.glob("report_*_raw.json"))
        if not json_files:
            logger.warning("❌ No JSON files found to consolidate!")
            return
        logger.info(
            f"🔍 Found {len(json_files)} JSON files to process for consolidation."
        )
        # First pass: aggregate all violations per application
        app_severity_counts = {}
        app_rows = []
        for json_file in sorted(json_files):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                app = data.get("application", {})
                app_id = app.get("publicId", "unknown")
                org_id = app.get("organizationId", "unknown")
                components = data.get("components", [])

                # Fetch organization name
                org_name = self.organization_id_to_name.get(org_id, "Unknown Organization")

                if app_id not in app_severity_counts:
                    app_severity_counts[app_id] = {
                        "Critical": 0,
                        "Severe": 0,
                        "Moderate": 0,
                    }
                for c in components:
                    violations = c.get("violations", [])
                    for violation in violations:
                        threat_level = violation.get("policyThreatLevel", 0)
                        if threat_level >= 7:
                            app_severity_counts[app_id]["Critical"] += 1
                        elif threat_level >= 4:
                            app_severity_counts[app_id]["Severe"] += 1
                        elif threat_level >= 1:
                            app_severity_counts[app_id]["Moderate"] += 1
                app_rows.append((app_id, org_id, org_name, components))
            except Exception as e:
                logger.error(f"   ❌ Error processing {json_file.name}: {e}")
        # Second pass: build rows with total counts for each app
        consolidated_data = []
        for app_id, org_id, org_name, components in app_rows:
            for c in components:
                component_name = c.get("displayName", "")
                violations = c.get("violations", [])
                if not violations:
                    continue  # skip rows with no policy violations
                for violation in violations:
                    threat_level = violation.get("policyThreatLevel", 0)

                    # Severity label not used in output, but kept for logic
                    def extract_cve_info(constraints):
                        cve_info = {
                            "cve_id": "",
                            "condition": "",
                            "constraint_name": "",
                        }

                        for constraint in constraints:
                            constraint_name = constraint.get("constraintName", "")
                            conditions = constraint.get("conditions", [])
                            cve_info["constraint_name"] = constraint_name
                            cve_ids = []
                            condition_parts = []
                            for condition in conditions:
                                condition_summary = condition.get(
                                    "conditionSummary", ""
                                )
                                condition_reason = condition.get("conditionReason", "")
                                cve_match = re.search(
                                    r"CVE-\d{4}-\d+",
                                    condition_summary + " " + condition_reason,
                                )
                                if cve_match and cve_match.group(0) not in cve_ids:
                                    cve_ids.append(cve_match.group(0))
                                if condition_reason:
                                    condition_parts.append(condition_reason)
                                elif condition_summary:
                                    condition_parts.append(condition_summary)
                            cve_info["cve_id"] = ", ".join(cve_ids) if cve_ids else ""
                            cve_info["condition"] = (
                                " | ".join(condition_parts) if condition_parts else ""
                            )
                        return cve_info

                    cve_info = extract_cve_info(violation.get("constraints", []))
                    policy_action = ""
                    if violation.get("policyThreatCategory", "").upper() == "SECURITY":
                        if threat_level >= 7:
                            policy_action = "Security-Critical"
                        elif threat_level >= 4:
                            policy_action = "Security-CVSS score than or equals 7"
                        else:
                            policy_action = "Security-Moderate"
                    else:
                        sev = (
                            "Critical"
                            if threat_level >= 7
                            else "Severe"
                            if threat_level >= 4
                            else "Moderate"
                            if threat_level >= 1
                            else "Low"
                        )
                        policy_action = (
                            f"{violation.get('policyThreatCategory', '')}-{sev}"
                            if violation.get("policyThreatCategory", "")
                            else sev
                        )
                    consolidated_row = {
                        "No.": len(consolidated_data) + 1,
                        "Application": app_id,
                        "Organization": org_name,  # Use org_name here
                        "time": "10 hours ago",
                        "Critical (7-10)": app_severity_counts[app_id]["Critical"],
                        "Severe (4-6)": app_severity_counts[app_id]["Severe"],
                        "Moderate (1-3)": app_severity_counts[app_id]["Moderate"],
                        "Policy": violation.get("policyName", ""),
                        "Component": component_name,
                        "Threat": threat_level,
                        "Policy/Action": policy_action,
                        "Constraint Name": cve_info["constraint_name"],
                        "Condition": cve_info["condition"],
                        "CVE": cve_info["cve_id"],
                    }
                    consolidated_data.append(consolidated_row)
        if consolidated_data:
            df_consolidated = pd.DataFrame(consolidated_data)
            output_csv_path.parent.mkdir(parents=True, exist_ok=True)
            df_consolidated.to_csv(output_csv_path, index=False)
            logger.info(f"💾 Consolidated CSV saved to: {output_csv_path}")
            logger.info(f"📊 Generated {len(consolidated_data)} consolidated rows.")
        else:
            logger.warning("❌ No data was consolidated!")


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
