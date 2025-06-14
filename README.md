# Sonatype IQ Server Raw Report Fetcher

🚀 A powerful tool to fetch raw scan reports from all applications in Sonatype IQ Server and export them as CSV files.

## Quick Start with Executable

### 1. Download the Latest Release

- Go to the [Releases](../../releases) page
- Download `release.zip`
- Extract the contents to your desired directory

### 2. Configure Environment

Create a `.env` file in the same directory as the executable:

```env
IQ_SERVER_URL=https://your-iq-server.com
IQ_USERNAME=your-username
IQ_PASSWORD=your-password
```

### 3. Run the Executable

```bash
# macOS/Linux
./main

# Windows
main.exe
```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export IQ_SERVER_URL="https://your-iq-server.com"
export IQ_USERNAME="your-username"
export IQ_PASSWORD="your-password"
```

### 3. Run from Source

```bash
python main.py
```

## Configuration Options

### Required Settings

- `IQ_SERVER_URL` - Your IQ Server base URL (e.g., `https://iq.company.com`)
- `IQ_USERNAME` - IQ Server username with appropriate permissions
- `IQ_PASSWORD` - IQ Server password

### Optional Settings

- `ORGANIZATION_ID` - Filter by specific organization ID (default: fetch from all organizations)
- `OUTPUT_DIR` - Output directory for CSV files (default: `raw_reports`)

### Configuration Methods

**Option 1: .env File (Recommended)**

```env
IQ_SERVER_URL=https://your-iq-server.com
IQ_USERNAME=your-username
IQ_PASSWORD=your-password
ORGANIZATION_ID=your-org-id
OUTPUT_DIR=custom_output_folder
```

**Option 2: Environment Variables**

```bash
export IQ_SERVER_URL="https://your-iq-server.com"
export IQ_USERNAME="your-username"
export IQ_PASSWORD="your-password"
export ORGANIZATION_ID="your-org-id"
export OUTPUT_DIR="custom_output_folder"
```

## Output Structure

The tool creates CSV files in the specified output directory with the following naming convention:

```
report_{application_public_id}_{report_id}_raw.csv
```

Each CSV contains:

- **Package URL** - Component package identifier
- **Display Name** - Human-readable component name
- **Security Issues Count** - Number of security vulnerabilities
- **License Data** - License information (JSON format)
- **Security Issues** - Detailed vulnerability data (JSON format)

## Customization Guide

### 🎯 Filter Applications

To process only specific applications, modify the `get_applications()` method in `main.py`:

```python
def get_applications(self) -> List[Application]:
    """Fetch and display applications."""
    apps = self.iq.get_applications(self.config.organization_id)

    # Example filters:

    # Filter by name pattern
    filtered_apps = [app for app in apps if "prod" in app.name.lower()]

    # Filter by specific app IDs
    target_ids = ["app1", "app2", "app3"]
    filtered_apps = [app for app in apps if app.publicId in target_ids]

    # Filter by regex pattern
    import re
    pattern = re.compile(r"(web|api|service)", re.IGNORECASE)
    filtered_apps = [app for app in apps if pattern.search(app.name)]

    return filtered_apps  # Return filtered list instead of apps
```

### 📊 Customize CSV Output

Modify the `_save_csv_manual()` method to change CSV structure:

```python
def _save_csv_manual(self, components: List[Dict[str, Any]], filepath: Path) -> None:
    """Custom CSV structure."""
    csv_data = []
    for c in components:
        # Add custom fields
        row = {
            "Package URL": c.get("packageUrl", ""),
            "Display Name": c.get("displayName", ""),
            "Component Hash": c.get("hash", ""),
            "Policy Violations": len(c.get("policyData", {}).get("policyViolations", [])),
            "Security Issues Count": len(c.get("securityData", {}).get("securityIssues", [])),
            "License Name": c.get("licenseData", {}).get("declaredLicenses", [{}])[0].get("licenseName", ""),
            "Custom Field": c.get("customAttribute", ""),  # Add any custom fields
        }
        csv_data.append(row)
    # ... rest of the method
```

### 🎨 Custom File Naming

Modify the `_save_as_csv()` method for custom filenames:

```python
def _save_as_csv(self, public_id: str, report_id: str, data: Dict[str, Any]) -> bool:
    """Save with custom filename pattern."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    app_name = data.get("applicationName", public_id).replace(" ", "_")

    # Custom filename patterns:
    filename = f"{app_name}_{timestamp}.csv"                    # Name + timestamp
    # filename = f"security_report_{public_id}.csv"            # Simple format
    # filename = f"{public_id}_scan_{report_id}.csv"           # Original format

    filepath = self.output_path / filename
    # ... rest of the method
```

### ⚡ Add Progress Bars

Install `tqdm` and modify `fetch_all_reports()`:

```python
# Add to requirements.txt: tqdm>=4.64.0

from tqdm import tqdm

def fetch_all_reports(self) -> None:
    """Fetch all reports with progress bar."""
    apps = self.get_applications()

    with tqdm(total=len(apps), desc="Processing apps", unit="app") as pbar:
        for i, app in enumerate(apps, 1):
            pbar.set_description(f"Processing {app.name[:20]}...")
            if self._fetch_app_report(app, i, len(apps)):
                success_count += 1
            pbar.update(1)
```

## Building Your Own Executable

### 🔨 Build Locally

1. **Install PyInstaller**

   ```bash
   pip install pyinstaller
   ```

2. **Create Executable**

   ```bash
   # Basic build
   pyinstaller --onefile main.py

   # Build with custom name and icon (if you have one)
   pyinstaller --onefile --name "iq-report-fetcher" main.py

   # Build with additional data files
   pyinstaller --onefile --add-data ".env.example:." main.py
   ```

3. **Find Your Executable**
   ```bash
   # Executable will be in:
   ./dist/main              # macOS/Linux
   ./dist/main.exe          # Windows
   ```

### 🚀 Automated Builds with GitHub Actions

The project includes automated building via GitHub Actions:

1. **Create a Release**

   ```bash
   # Tag your code
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Automatic Build Process**

   - GitHub Actions automatically builds executable
   - Creates release with `release.zip` containing:
     - `main` (executable)
     - `main.py` (source)
     - `README.md`
     - `error_handler.py`
     - `requirements.txt`

3. **Manual Trigger**
   - Go to Actions tab in GitHub
   - Select "Build and Release"
   - Click "Run workflow"

### 📦 Distribution

**For End Users:**

- Provide the executable + `.env.example`
- Include setup instructions
- No Python installation required

**For Developers:**

- Provide source code
- Include `requirements.txt`
- Python installation required

## Development Guide

### 🏗️ Project Structure

```
CTBC_raw_report_fetch/
├── main.py              # Main application logic
├── error_handler.py     # Centralized error handling
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── .env.example        # Environment template
├── .github/workflows/  # CI/CD automation
└── main.spec          # PyInstaller configuration
```

### 🔧 Key Components

**main.py:**

- `Config` - Environment configuration management
- `IQServerClient` - API client with error handling
- `RawReportFetcher` - Main processing logic
- `PrettyFormatter` - Colorized logging

**error_handler.py:**

- `ErrorHandler` - Decorator-based error handling
- Handles API, file, and configuration errors
- Provides graceful failure modes

### 🧪 Adding New Features

#### 1. Add New Configuration Options

```python
# In Config class
class Config(BaseModel):
    # ...existing fields...
    new_option: Optional[str] = None
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        # ...existing code...
        new_opt = os.getenv("NEW_OPTION")
        retries = int(os.getenv("MAX_RETRIES", "3"))

        return cls(
            # ...existing params...
            new_option=new_opt,
            max_retries=retries,
        )
```

#### 2. Add New API Endpoints

```python
# In IQServerClient class
@ErrorHandler.handle_api_error
def get_policy_violations(self, app_id: str) -> Optional[Dict[str, Any]]:
    """Fetch policy violations for an application."""
    response = self._request("GET", f"/api/v2/applications/{app_id}/policyViolations")
    return response.json()
```

#### 3. Add New Output Formats

```python
# In RawReportFetcher class
@ErrorHandler.handle_file_error
def _save_as_json(self, public_id: str, report_id: str, data: Dict[str, Any]) -> bool:
    """Save report data as JSON file."""
    filename = f"report_{public_id}_{report_id}_raw.json"
    filepath = self.output_path / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True
```

#### 4. Add New Filters

```python
# Example: Filter by last scan date
def filter_by_recent_scans(self, apps: List[Application], days: int = 30) -> List[Application]:
    """Filter applications by recent scan activity."""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=days)

    filtered = []
    for app in apps:
        info = self.iq.get_latest_report_info(app.id)
        if info and info.scanDate and datetime.fromisoformat(info.scanDate) > cutoff:
            filtered.append(app)
    return filtered
```

### 🐛 Debugging Tips

1. **Enable Debug Logging**

   ```python
   # In main.py, change logging level
   logger.setLevel(logging.DEBUG)
   ```

2. **Test API Connectivity**

   ```python
   # Add to main() function for testing
   client = IQServerClient(str(config.iq_server_url), config.iq_username, config.iq_password)
   apps = client.get_applications()
   print(f"Connected! Found {len(apps or [])} applications")
   ```

3. **Handle Rate Limiting**

   ```python
   # Add delays between requests
   import time

   def _fetch_app_report(self, app: Application, idx: int, total: int) -> bool:
       time.sleep(0.5)  # 500ms delay between requests
       # ...rest of method...
   ```

### 🔄 Future Enhancements

**Potential Features:**

- Multiple output formats (JSON, Excel, XML)
- Incremental updates (only fetch new reports)
- Parallel processing for faster execution
- Web dashboard for report visualization
- Email notifications
- Integration with external systems
- Report scheduling
- Data filtering and aggregation

**Performance Optimizations:**

- Async HTTP requests
- Database caching
- Incremental processing
- Memory optimization for large datasets

### 📝 Contributing

1. **Fork the repository**
2. **Create feature branch:** `git checkout -b feature/new-feature`
3. **Make changes and test thoroughly**
4. **Update documentation**
5. **Submit pull request**

**Code Style:**

- Follow PEP 8
- Use type hints
- Add docstrings for new functions
- Include error handling
- Write tests for new features
