import requests
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from .utils import ErrorHandler, IQServerError, logger


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
    tags: Optional[List[Any]] = None

    class Config:
        extra = "allow"


class IQServerClient:
    """Simple IQ Server API client with error handling built-in."""

    def __init__(self, url: str, user: str, pwd: str) -> None:
        self.base_url = url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (user, pwd)
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make HTTP requests with error handling."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"🌐 Preparing {method} request to: {url}")
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        try:
            r = self.session.request(method, url, **kwargs)
            logger.debug(f"🔄 {method} {url} - Status: {r.status_code}")
            r.raise_for_status()
            logger.debug(f"✅ {method} {endpoint} succeeded.")
            return r
        except requests.RequestException as e:
            logger.error(f"❌ {method} {endpoint} failed: {e}")
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
        logger.info(f"🔍 Fetching applications (org_id={org_id}) ...")
        response = self._request("GET", ep)
        apps_data = response.json().get("applications", [])
        logger.info(f"📦 Retrieved {len(apps_data)} applications from server.")
        logger.debug(
            f"Applications data: {apps_data[:2]}{' ...' if len(apps_data) > 2 else ''}"
        )
        return [Application(**app) for app in apps_data]

    @ErrorHandler.handle_api_error
    def get_latest_report_info(self, app_id: str) -> Optional[ReportInfo]:
        """Get the latest report info for an application."""
        logger.info(f"🔍 Fetching latest report info for app_id={app_id} ...")
        response = self._request("GET", f"/api/v2/reports/applications/{app_id}")
        reports = response.json()
        if reports:
            logger.info(f"📄 Found {len(reports)} reports for app_id={app_id}.")
            logger.debug(f"First report info: {reports[0]}")
        else:
            logger.warning(f"❗ No reports found for app_id={app_id}.")
        return ReportInfo(**reports[0]) if reports else None

    @ErrorHandler.handle_api_error
    def get_policy_violations(
        self, public_id: str, report_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch raw report data."""
        logger.info(
            f"🔍 Fetching policy violations for public_id={public_id}, report_id={report_id} ..."
        )
        response = self._request(
            "GET",
            f"/api/v2/applications/{public_id}/reports/{report_id}/policy?includeViolationTimes=true",
        )
        logger.debug(
            f"Policy violations response: {response.text[:200]}{' ...' if len(response.text) > 200 else ''}"
        )
        return response.json()

    @ErrorHandler.handle_api_error
    def get_organizations(self) -> Optional[List[Organization]]:
        """Fetch all organizations and return as validated models."""
        logger.info("🔍 Fetching organizations ...")
        response = self._request("GET", "/api/v2/organizations")
        orgs_data = response.json().get("organizations", [])
        logger.info(f"🏢 Retrieved {len(orgs_data)} organizations from server.")
        logger.debug(
            f"Organizations data: {orgs_data[:2]}{' ...' if len(orgs_data) > 2 else ''}"
        )
        return [Organization(**org) for org in orgs_data]
