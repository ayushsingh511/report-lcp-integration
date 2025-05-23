# Flow - Web Performance Analysis and Optimization Tool

## Entire Pipeline

```bash
python run.py pipeline --url https://example.com --device mobile --model gpt-4o
```

This command runs the complete flow:
1. Generates a performance report
2. Downloads website assets
3. Applies all suggested optimizations
4. Tests performance improvements
5. Shows before/after comparison
6. Saves results to CSV and structured suggestions to JSON

## Available Commands

### `pipeline` - Complete Analysis and Optimization (Recommended)
```bash
python run.py pipeline --url <website> --device <device> --model <model>
```

Example:


**Options:**
- `--url`: Website URL to analyze and optimize (required)
- `--device`: Device type - `mobile` or `desktop` (default: mobile)
- `--model`: LLM model to use (default: gpt-4o)
  - Available models: `gpt-4o`
- `--skip-cache`: Skip cached data and fetch fresh results
- `--headless`: Run browser in headless mode (default: true)

### `report` - Generate Performance Report Only
```bash
python run.py report --url <website> --device <device> --model <model>
```

**Options:**
- `--url`: Website URL to analyze (required)
- `--action`: Action type (default: report)
- `--device`: Device type - `mobile` or `desktop` (default: mobile)
- `--model`: LLM model to use
- `--skip-cache`: Skip cached data

### `apply` - Apply Existing Report Suggestions
```bash
python run.py apply --report <report-file> --url <website>
```

**Options:**
- `--report`: Path to report file (required)
- `--url`: Website URL (required)
- `--device`: Device type for testing (default: desktop)
- `--headless`: Run browser in headless mode


## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd flow
   ```

2. **Install JavaScript dependencies:**
   ```bash
   cd report
   npm install
   cd ..
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## ⚙️ Configuration

Create a `.env` file in the root directory:
```env
GOOGLE_CRUX_API_KEY=
GOOGLE_PAGESPEED_INSIGHTS_API_KEY=

# Gemini Models
GOOGLE_APPLICATION_CREDENTIALS=

# OpenAI Models
AZURE_OPENAI_API_DEPLOYMENT_NAME=
AZURE_OPENAI_API_INSTANCE_NAME=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=

AZURE_API_KEY=
AZURE_API_BASE=
AZURE_API_VERSION=

# Claude Models
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
```


Export all the env variables to terminal.
```
export $(cat .env | xargs)
```

## Demo

```bash
# Install Streamlit if needed
pip install streamlit pandas

# Run the demo UI
streamlit run demo_app.py
```

Access the UI at http://localhost:8501 after running the command.

## 📄 Final Output Files

After running the pipeline, all results are saved to `final_output/<folder_name>/`:

**Files include:**
- **`performance_results_<timestamp>.csv`** - LCP scores and improvements
- **`optimization_summary_<timestamp>.json`** - Complete run metadata
- **`parsed_suggestions_<timestamp>.json`** - Structured suggestions
- **`suggestions_<timestamp>.yaml`** - Intermediate YAML format

The modified website assets remain in `output/<folder_name>/` organized in git branches.