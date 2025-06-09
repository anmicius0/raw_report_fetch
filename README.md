# Sonatype IQ Server Raw Report Fetcher

Fetches raw scan reports from all applications in IQ Server and exports them as CSV files.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:

   ```bash
   export IQ_SERVER_URL="https://your-iq-server.com"
   export IQ_USERNAME="your-username"
   export IQ_PASSWORD="your-password"
   ```

3. Run:
   ```bash
   python main.py
   ```

## Configuration

**Required:**

- `IQ_SERVER_URL` - IQ Server base URL
- `IQ_USERNAME` - IQ Server username
- `IQ_PASSWORD` - IQ Server password

**Optional:**

- `ORGANIZATION_ID` - Filter by organization (default: all apps)
- `OUTPUT_DIR` - Output directory (default: `raw_reports`)

Create `.env` file:

```env
IQ_SERVER_URL=https://your-iq-server.com
IQ_USERNAME=your-username
IQ_PASSWORD=your-password
```

## Customization

**Filter applications** - Edit `get_applications()` method:

```python
filtered = [app for app in applications if "prod" in app["name"].lower()]
```

**Change CSV format** - Edit `_save_raw_report_as_csv_manual()` method:

```python
row["Custom Field"] = component.get("customField", "")
```

**Custom filename** - Edit `_save_report_data()` method:

```python
filename = f"{app_public_id}_{timestamp}.csv"
```
