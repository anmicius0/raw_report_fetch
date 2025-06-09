# IQ Server Raw Report Fetcher

This tool connects to your Sonatype IQ Server, fetches security scan reports for all your applications, and saves them as CSV files. You can use these CSVs for analysis, compliance, or sharing with your team.

## 🚀 Getting Started: Step-by-Step

### 1. **Download or Clone the Program**

- Download the latest release from the Releases page

### 2. **Configure Your Settings**

- Go to the `config` folder in the project directory.
- Copy `.env.example` to `.env`:
  ```sh
  cp config/.env.example config/.env
  ```
- Open `config/.env` in a text editor and fill in your actual Sonatype IQ Server details:

  - `IQ_SERVER_URL`: The address of your IQ Server
  - `IQ_USERNAME`: Your username
  - `IQ_PASSWORD`: Your password
  - `OUTPUT_DIR`: (Optional) Where CSV files will be saved. Default is `raw_reports`.
  - `NUM_WORKERS`: (Optional) Number of concurrent workers. Default is 8.
  - `LOG_LEVEL`: (Optional) Set to DEBUG, INFO, WARNING, or ERROR.

### 4. **Run the Tool**

```sh
./report-fetch
```

- On Windows, run: `report-fetch.exe`

## 📝 Configuration Reference

You can set configuration in two ways:

1. **Edit the `config/.env` file** (recommended for most users).
2. **Set environment variables** in your shell or system (for advanced users or automation).

**Example `.env` file:**

```
IQ_SERVER_URL=https://your-iq-server.com
IQ_USERNAME=your-username
IQ_PASSWORD=your-password
OUTPUT_DIR=raw_reports
NUM_WORKERS=8
LOG_LEVEL=INFO
```

## 🏗️ Project Structure

```
iqserver_report_fetch/
├── src/
│   └── iq_fetcher/
│       ├── __init__.py          # Package initialization
│       ├── config.py            # Configuration management
│       ├── client.py            # IQ Server API client
│       ├── fetcher.py           # Core report fetching logic
│       └── utils.py             # Utilities, logging, error handling
├── config/
│   ├── .env.example         # Configuration template
│   └── .env                 # Your configuration (not in git)
├── pyproject.toml           # Project dependencies (uv)
├── uv.lock                  # Locked dependencies
├── README.md                # This file
└── scripts/
    └── build_macos.sh       # Build script for macOS
```
