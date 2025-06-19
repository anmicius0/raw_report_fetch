# CTBC IQ Server Raw Report Fetcher

## 📦 What Does This Tool Do?

This tool connects to your Sonatype IQ Server, fetches security scan reports for all your applications, and saves them as CSV files. You can use these CSVs for analysis, compliance, or sharing with your team.

---

## 🚀 Getting Started: Step-by-Step

### 1. **Download or Clone the Program**

- Download the latest release from the Releases page, **or**
- Clone the repository:
  ```sh
  git clone <repo-url>
  cd raw-report-fetch
  ```

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

> **Tip:** If you don't know your organization ID, leave it blank to fetch all applications you have access to.

### 3. **Install Dependencies**

- Install [uv](https://github.com/astral-sh/uv) (recommended):
  ```sh
  uv pip install -r pyproject.toml
  ```

### 4. **Run the Tool**

- **From source:**
  ```sh
  python main.py
  ```
- **Or, if you built an executable:**
  ```sh
  ./raw-report-fetch
  ```

The tool will connect to your IQ Server, fetch reports, and save CSV files in the `raw_reports` folder (or the folder you set in `.env`).

---

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

---

## 🏗️ Project Structure

```
raw-report-fetch/
├── iq_fetcher/
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management
│   ├── client.py            # IQ Server API client
│   ├── fetcher.py           # Core report fetching logic
│   └── utils.py             # Utilities, logging, error handling
├── config/
│   ├── .env.example         # Configuration template
│   └── .env                 # Your configuration (not in git)
├── main.py                  # Main entry point
├── pyproject.toml           # Project dependencies (uv)
├── uv.lock                  # Locked dependencies
├── README.md                # This file
└── scripts/
    └── build_macos.sh       # Build script for macOS
```

---

## 🧑‍💻 For Developers: Running from Source

1. **Install dependencies:**
   ```sh
   uv pip install -r pyproject.toml
   ```
2. **Copy and edit the `.env` file** as above.
3. **Run the tool:**
   ```sh
   python main.py
   ```

---

## 🏗️ Building an Executable (For Distribution)

1. **Install PyInstaller:**
   ```sh
   uv pip install pyinstaller
   ```
2. **Build the executable:**
   ```sh
   ./scripts/build_macos.sh
   # or manually:
   pyinstaller --onefile main.py --name raw-report-fetch
   ```
   - The output will be in the `dist/` folder.

---

## 🛠️ Customizing the Tool (For Advanced Users)

- **Filter which applications are fetched:** Edit `get_applications()` in `iq_fetcher/fetcher.py`.
- **Change what data goes into the CSV:** Edit the consolidation logic in `iq_fetcher/fetcher.py`.
- **Change the CSV file name:** Edit the relevant code in `iq_fetcher/fetcher.py`.
- **Add progress bars:** Install `tqdm` and wrap your loop as shown in the code comments.
