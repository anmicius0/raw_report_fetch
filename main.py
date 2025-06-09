#!/usr/bin/env python3
"""
Sonatype IQ Server Raw Report Fetcher
Fetches raw scan reports from all applications in IQ Server and saves them as JSON files.
"""

import requests
import logging
import json
import os
import sys
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


# Colors for terminal output
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


# Custom formatter for prettier output
class PrettyFormatter(logging.Formatter):
    def format(self, record):
        if record.levelname == "INFO":
            if "✓" in record.getMessage():
                return f"{Colors.GREEN}{record.getMessage()}{Colors.END}"
            elif "✗" in record.getMessage():
                return f"{Colors.RED}{record.getMessage()}{Colors.END}"
            elif "Found" in record.getMessage() or "Starting" in record.getMessage():
                return f"{Colors.CYAN}{Colors.BOLD}{record.getMessage()}{Colors.END}"
            elif "completed" in record.getMessage():
                return f"{Colors.PURPLE}{Colors.BOLD}{record.getMessage()}{Colors.END}"
            else:
                return f"{Colors.BLUE}{record.getMessage()}{Colors.END}"
        elif record.levelname == "ERROR":
            return f"{Colors.RED}{Colors.BOLD}ERROR: {record.getMessage()}{Colors.END}"
        elif record.levelname == "WARNING":
            return f"{Colors.YELLOW}{Colors.BOLD}WARNING: {record.getMessage()}{Colors.END}"
        return record.getMessage()


# Setup logging with pretty formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(PrettyFormatter())
logger.addHandler(handler)
logger.propagate = False


class IQServerError(Exception):
    """Custom exception for IQ Server API errors"""

    pass


@dataclass
class Config:
    """Configuration for the raw report fetcher"""

    iq_server_url: str
    iq_username: str
    iq_password: str
    organization_id: Optional[str] = None
    output_dir: str = "raw_reports"

    @classmethod
    def from_environment(cls) -> "Config":
        """Load configuration from environment variables"""
        iq_server_url = os.getenv("IQ_SERVER_URL", "").rstrip("/")
        iq_username = os.getenv("IQ_USERNAME", "")
        iq_password = os.getenv("IQ_PASSWORD", "")
        organization_id = os.getenv("ORGANIZATION_ID")
        output_dir = os.getenv("OUTPUT_DIR", "raw_reports")

        required_vars = {
            "IQ_SERVER_URL": iq_server_url,
            "IQ_USERNAME": iq_username,
            "IQ_PASSWORD": iq_password,
        }

        missing = [k for k, v in required_vars.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            iq_server_url=iq_server_url,
            iq_username=iq_username,
            iq_password=iq_password,
            organization_id=organization_id,
            output_dir=output_dir,
        )


@dataclass
class ApplicationResult:
    """Result of processing a single application"""

    app_name: str
    app_public_id: str
    raw_report_file: Optional[str] = None
    error: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Check if the application processing was successful"""
        return self.error is None


@dataclass
class FetchStatistics:
    """Statistics for the fetch operation"""

    processed: int = 0
    successful: int = 0
    errors: int = 0

    def increment_processed(self):
        """Increment processed count"""
        self.processed += 1

    def increment_successful(self):
        """Increment successful count"""
        self.successful += 1

    def increment_errors(self):
        """Increment error count"""
        self.errors += 1


class IQServerClient:
    """Simplified IQ Server API client"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({"Accept": "application/json"})

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise IQServerError(f"{method} {endpoint} failed: {e}")

    def get_applications(self, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all applications or applications for a specific organization"""
        endpoint = (
            f"/api/v2/applications/organization/{org_id}"
            if org_id
            else "/api/v2/applications"
        )
        response = self._request("GET", endpoint)
        data = response.json()
        return data.get("applications", data)

    def get_latest_report_info(self, app_internal_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest report information for an application"""
        response = self._request(
            "GET", f"/api/v2/reports/applications/{app_internal_id}"
        )
        reports = response.json()
        return reports[0] if reports else None

    def get_raw_report(self, app_public_id: str, report_id: str) -> Dict[str, Any]:
        """Fetch the raw report data"""
        response = self._request(
            "GET", f"/api/v2/applications/{app_public_id}/reports/{report_id}/raw"
        )
        return response.json()


class RawReportFetcher:
    """Main class for fetching raw reports from all applications"""

    def __init__(self, config: Config):
        self.config = config
        self.iq_client = IQServerClient(
            config.iq_server_url, config.iq_username, config.iq_password
        )
        self.output_path = Path(config.output_dir)

    def _setup_output_directory(self) -> None:
        """Create output directory if it doesn't exist"""
        self.output_path.mkdir(parents=True, exist_ok=True)
        print(
            f"{Colors.BLUE}📁 Output directory: {Colors.BOLD}{self.output_path.absolute()}{Colors.END}"
        )

    def _extract_report_id(self, report_info: Dict[str, Any]) -> Optional[str]:
        """Extract report ID from report information"""
        if "reportDataUrl" in report_info:
            try:
                return report_info["reportDataUrl"].split("/reports/")[1].split("/")[0]
            except (IndexError, AttributeError):
                pass
        return report_info.get("scanId")

    def _save_report_data(
        self, app_public_id: str, report_id: str, data: Dict[str, Any]
    ) -> str:
        """Save raw report data to CSV file"""
        filename = f"report_{app_public_id}_{report_id}_raw.csv"
        filepath = self.output_path / filename
        self._save_raw_report_as_csv(data, filepath)
        return str(filepath)

    def _save_raw_report_as_csv(self, data: Dict[str, Any], filepath: Path) -> None:
        """Convert raw report JSON data to CSV format using pandas"""
        try:
            import pandas as pd

            components = data.get("components", [])

            if not components:
                # Create empty CSV
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(["No components found"])
                return

            # Use pandas to automatically flatten the nested JSON structure
            df = pd.json_normalize(components)

            # Handle array fields by joining them with semicolons
            for col in df.columns:
                if df[col].dtype == "object":
                    df[col] = df[col].apply(
                        lambda x: (
                            "; ".join(str(item) for item in x)
                            if isinstance(x, list)
                            else (
                                json.dumps(x, ensure_ascii=False)
                                if isinstance(x, dict)
                                else str(x) if x is not None else ""
                            )
                        )
                    )

            # Save to CSV
            df.to_csv(filepath, index=False, encoding="utf-8")

        except ImportError:
            # Fallback if pandas not available
            self._save_raw_report_as_csv_manual(data, filepath)

    def _save_raw_report_as_csv_manual(
        self, data: Dict[str, Any], filepath: Path
    ) -> None:
        """Manual CSV conversion fallback when pandas is not available"""
        components = data.get("components", [])

        if not components:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["No components found"])
            return

        # Prepare CSV data by flattening the component structure
        csv_data = []
        for component in components:
            # Skip components that are just {"swid": null}
            if len(component) == 1 and component.get("swid") is None:
                continue

            row = {
                "Package URL": component.get("packageUrl", ""),
                "Hash": component.get("hash", ""),
                "Display Name": component.get("displayName", ""),
                "Proprietary": component.get("proprietary", ""),
                "Match State": component.get("matchState", ""),
                "Identification Source": component.get("identificationSource", ""),
                "Pathnames": "; ".join(component.get("pathnames", [])),
                "Filenames": "; ".join(component.get("filenames", [])),
                "CPE": component.get("cpe", ""),
                "SWID": component.get("swid", ""),
            }

            # Add license data
            license_data = component.get("licenseData", {})
            row["License Data"] = json.dumps(license_data) if license_data else ""

            # Add security issues
            security_data = component.get("securityData", {})
            security_issues = security_data.get("securityIssues", [])
            row["Security Issues Count"] = len(security_issues)
            row["Security Issues"] = (
                json.dumps(security_issues) if security_issues else ""
            )

            # Add dependency data
            dependency_data = component.get("dependencyData", {})
            row["Inner Source"] = dependency_data.get("innerSource", "")
            row["Dependency Data"] = (
                json.dumps(dependency_data) if dependency_data else ""
            )

            csv_data.append(row)

        # Write CSV file
        if csv_data:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)

    def _fetch_application_reports(
        self, app: Dict[str, Any], index: int, total: int
    ) -> ApplicationResult:
        """Fetch raw report for a single application"""
        app_id = app["id"]
        app_public_id = app["publicId"]
        app_name = app["name"]

        result = ApplicationResult(app_name=app_name, app_public_id=app_public_id)

        try:
            # Get latest report info
            report_info = self.iq_client.get_latest_report_info(app_id)
            if not report_info:
                result.error = "No reports found"
                print(
                    f"{Colors.YELLOW}⚠ [{index}/{total}] No reports: {Colors.BOLD}{app_name}{Colors.END}"
                )
                return result

            # Extract report ID
            report_id = self._extract_report_id(report_info)
            if not report_id:
                result.error = "No report ID"
                print(
                    f"{Colors.YELLOW}⚠ [{index}/{total}] No report ID: {Colors.BOLD}{app_name}{Colors.END}"
                )
                return result

            # Fetch raw report
            raw_report_data = self.iq_client.get_raw_report(app_public_id, report_id)
            result.raw_report_file = self._save_report_data(
                app_public_id, report_id, raw_report_data
            )

            print(
                f"{Colors.GREEN}✓ [{index}/{total}] Fetched: {Colors.BOLD}{app_name}{Colors.END}"
            )

        except Exception as e:
            result.error = str(e)
            print(
                f"{Colors.RED}✗ [{index}/{total}] Failed: {Colors.BOLD}{app_name}{Colors.END} - {e}"
            )

        return result

    def get_applications(self) -> List[Dict[str, Any]]:
        """Get applications from IQ Server"""
        print(
            f"\n{Colors.CYAN}{Colors.BOLD}🔍 Fetching applications from IQ Server...{Colors.END}"
        )

        applications = self.iq_client.get_applications(self.config.organization_id)
        logger.info(f"Found {len(applications)} applications")

        # Display found applications
        if applications:
            print(f"{Colors.BLUE}📋 Applications found:{Colors.END}")
            for i, app in enumerate(applications[:5], 1):  # Show first 5
                print(
                    f"    • {Colors.WHITE}{app['name']}{Colors.END} ({app['publicId']})"
                )
            if len(applications) > 5:
                print(f"    ... and {len(applications) - 5} more")

        return applications

    def fetch_all_reports(self) -> Dict[str, int]:
        """Main function to fetch all raw reports"""
        print(
            f"\n{Colors.PURPLE}{Colors.BOLD}📊 IQ Server Raw Report Fetcher{Colors.END}"
        )
        print(f"{Colors.PURPLE}{'=' * 50}{Colors.END}")
        logger.info("Starting raw report fetch process...")

        self._setup_output_directory()

        # Get all applications
        applications = self.get_applications()
        if not applications:
            print(f"\n{Colors.YELLOW}⚠️  No applications found{Colors.END}")
            return {"processed": 0, "successful": 0, "errors": 0}

        # Process each application
        stats = FetchStatistics()
        total = len(applications)

        print(
            f"\n{Colors.CYAN}{Colors.BOLD}📊 Processing {total} applications:{Colors.END}"
        )
        print(f"{Colors.CYAN}{'─' * 50}{Colors.END}")

        for i, app in enumerate(applications, 1):
            result = self._fetch_application_reports(app, i, total)
            stats.increment_processed()

            if result.is_successful:
                stats.increment_successful()
            else:
                stats.increment_errors()

        # Display summary
        print(f"\n{Colors.PURPLE}{Colors.BOLD}📈 Fetch Summary{Colors.END}")
        print(f"{Colors.PURPLE}{'=' * 30}{Colors.END}")
        print(
            f"{Colors.GREEN}✅ Reports fetched: {Colors.BOLD}{stats.successful}{Colors.END}"
        )
        print(
            f"{Colors.BLUE}📊 Total processed: {Colors.BOLD}{stats.processed}{Colors.END}"
        )
        if stats.errors > 0:
            print(f"{Colors.RED}❌ Errors: {Colors.BOLD}{stats.errors}{Colors.END}")
        else:
            print(f"{Colors.GREEN}❌ Errors: {Colors.BOLD}0{Colors.END}")

        print(
            f"\n{Colors.GREEN}{Colors.BOLD}🎉 Fetch completed successfully!{Colors.END}"
        )

        return {
            "processed": stats.processed,
            "successful": stats.successful,
            "errors": stats.errors,
        }


def main():
    """Main function"""
    try:
        config = Config.from_environment()
        fetcher = RawReportFetcher(config)
        return fetcher.fetch_all_reports()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Cancelled by user{Colors.END}")
        sys.exit(0)
    except (ValueError, IQServerError) as e:
        print(f"\n{Colors.RED}{Colors.BOLD}💥 Error: {e}{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}{Colors.BOLD}💥 Unexpected error: {e}{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()
