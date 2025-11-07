# UI State Capture System

A generalized AI-powered system that automatically navigates web applications, handles login flows, and captures UI states for any user-requested task across different web apps.

## Features

**Generalized Task Execution**
- Works with any web app (Notion, Linear, Asana, GitHub, etc.)
- Automatically detects which app from task input
- No hardcoded workflows per app

**Smart Login Handling**
- Enters email automatically
- Waits 15 seconds for user to enter 2FA code
- Periodically checks if login form is fully filled
- Continues execution after successful login

**UI State Capture**
- Captures screenshots at each step
- Stores screenshots with metadata
- Generates JSON manifest with task details
- Organized output directory per task

**Powered by Browser Use & LLM**
- Uses browser-use 0.9.5 for AI-driven browser automation
- ChatBrowserUse LLM for intelligent task execution
- Parallel execution potential (ready for future enhancements)

## Architecture

```
User Task Input: "Create a database in Notion"
        ↓
App Detection (notion → notion.so)
        ↓
Initialize Browser + Agent
        ↓
Login Flow:
  - Navigate to login
  - Enter email
  - Wait 15s for 2FA
  - Check form fields filled
        ↓
Execute Task (via Agent)
        ↓
Capture Screenshots
        ↓
Generate Manifest + Dataset
```

## Installation

### 1. Clone the repository
```bash
git clone <repo_url>
cd edinburgh
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
EMAIL=your-email@example.com
PASSWORD=your-secure-password
BROWSER_USE_API_KEY=your_api_key_here (optional)
HEADLESS=false (optional, default: false)
```

### 4. Install Playwright browsers
```bash
playwright install
```

## Configuration

### Supported Apps

The system currently supports:

| App | URL | Config |
|-----|-----|--------|
| Notion | https://www.notion.so | AppConfig in app_config.py |
| Linear | https://linear.app | AppConfig in app_config.py |
| Jira | https://atlassian.net | AppConfig in app_config.py |
| Monday.com | https://monday.com | AppConfig in app_config.py |

### Customizing App Config

Edit `app_config.py` to add new apps or modify existing ones:

```python
APPS: Dict[str, AppConfig] = {
    "your_app": AppConfig(
        name="Your App",
        url="https://app.example.com",
        login_url="https://app.example.com/login",
        login_email_field="input[type='email']",  # CSS selector
        login_password_field="input[type='password']",  # CSS selector
        login_button="button[type='submit']",  # CSS selector
        mfa_wait_time=15,  # Seconds
    ),
}
```

## Usage

### Command Line Mode

Run a task directly:

```bash
python task_executor.py "Create a database in Notion"
```

### Example Tasks

```bash
# Notion
"Create a database called Projects in Notion"
"Filter a database by status in Notion"

# Linear
"Create a new project in Linear"
"Filter issues by high priority in Linear"

# Jira
"Create a task with summary and priority in Jira"

# Monday.com
"Create a bug with status and priority in Monday"
```

### Programmatic Usage

```python
import asyncio
from task_executor import run_task

async def main():
    result = await run_task(
        task_input="Create a database in Notion",
        headless=False  # Set True to run headless
    )
    print(f"Task result: {result}")

asyncio.run(main())
```

## Output Structure

Each task generates an output directory:

```
outputs/
├── 20251106_143022/
│   ├── 01_step_1.png
│   ├── 02_step_2.png
│   ├── 03_step_3.png
│   └── manifest.json
```

### manifest.json

```json
{
  "task": "Create a database in Notion",
  "app": "Notion",
  "executed_at": "2025-11-06T14:30:22.123456",
  "screenshots_count": 5,
  "screenshots": [
    {
      "step": 1,
      "file": "01_step_1.png"
    },
    {
      "step": 2,
      "file": "02_step_2.png"
    }
  ],
  "token_usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "cached_tokens": 0
  },
  "cost": {
    "estimated_cost_usd": 0.0
  },
  "cookies_stored_in": "/Users/you/.browser-use-chrome"
}
```

## How It Works

### 1. App Detection
The system scans your task input for known app names (notion, linear, jira, monday).

### 2. Login Flow
- **Navigate**: Goes to the app's login page
- **Email Entry**: Fills in email from environment variable
- **Password Entry**: Fills in password from environment variable
- **2FA Wait**: Waits up to 15 seconds for user to enter 2FA code
- **Cookie Persistence**: Saves browser profile for future logins

### 3. Task Execution
- The browser-use Agent reads your task
- Uses the ChatBrowserUse LLM to understand the task
- Executes a sequence of browser actions (click, type, scroll, etc.)
- Captures the UI state at each step

### 4. Screenshot Capture
- Captures screenshots during task execution
- Extracts all steps from agent history
- Generates manifest.json with metadata
- Supports 100+ non-URL UI states (modals, forms, dropdowns)

### 5. Cookie Management
- Browser profiles stored in: `~/.browser-use-chrome/`
- Automatic cookie persistence across runs
- No re-login required for subsequent tasks
- Session data preserved between executions

## Troubleshooting

### "Email must be provided via EMAIL environment variable"
- Make sure you have EMAIL set in .env file
- Run: `echo $EMAIL` to verify it's exported

### "No app detected in task"
- Make sure your task mentions an app name (notion, linear, jira, monday)
- Example: "Create a database in Notion" (correct)
- Example: "Create a database" (incorrect - missing app name)

### Login fails
- Check that EMAIL and PASSWORD are correct in .env
- Make sure you're entering the 2FA code within 15 seconds
- Verify network connection if timeout occurs
- Try clearing browser cache: `rm -rf ~/.browser-use-chrome/`

### Screenshots are blank or missing
- Increase wait time if page is slow to load
- Check browser console for JavaScript errors
- Verify task is complex enough to generate multiple states

## Environment Variables

Create a `.env` file with:

```
# Required
EMAIL=your-email@example.com
PASSWORD=your-password

# Optional
BROWSER_USE_API_KEY=your-api-key
HEADLESS=false
LOG_LEVEL=INFO
```

**Security Note**: Never commit `.env` to git. The file is already in `.gitignore`.

## Dataset & Demonstration

See `DATASET.md` for:
- 5 complete task examples with 100+ screenshots
- Problem statement alignment for each task
- Non-URL state capture demonstrations
- Cross-app generalization proof

## Next Steps

- Test on additional apps (Asana, GitHub, Slack)
- Add support for more complex interactions
- Implement parallel execution for multiple tasks
- Expand to API-based automation

## Contributing

To add a new app:
1. Add configuration to `app_config.py`
2. Verify login selectors are correct
3. Test with a sample task
4. Update this README

## License

MIT
