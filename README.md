# UI State Capture System

A generalized AI-powered system that automatically navigates web applications, handles login flows, and captures UI states for any user-requested task across different web apps.

## Features

✨ **Generalized Task Execution**
- Works with any web app (Notion, Linear, Asana, GitHub, etc.)
- Automatically detects which app from task input
- No hardcoded workflows per app

🔐 **Smart Login Handling**
- Enters email automatically
- Waits 15 seconds for user to enter 2FA code
- Periodically checks if login form is fully filled
- Continues execution after successful login

📸 **UI State Capture**
- Captures screenshots at each step
- Stores screenshots with metadata
- Generates JSON manifest with task details
- Organized output directory per task

🤖 **Powered by Browser Use & LLM**
- Uses browser-use 0.8.0 for AI-driven browser automation
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

### 3. Set up Browser Use API key

Create a `.env` file in the project root:
```bash
BROWSER_USE_API_KEY=your_api_key_here
```

Get your API key from: https://cloud.browser-use.com

### 4. Install Playwright browsers
```bash
playwright install
```

## Configuration

### Supported Apps

The system currently supports:

| App | URL | Login URL |
|-----|-----|-----------|
| Notion | https://www.notion.so | https://www.notion.so/login |
| Linear | https://linear.app | https://linear.app/login |
| Asana | https://app.asana.com | https://app.asana.com/-/login |
| GitHub | https://github.com | https://github.com/login |

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

### Interactive Mode (Recommended)

Run the interactive orchestrator:

```bash
python main.py
```

This launches an interactive interface where you can:
- Enter tasks one by one
- View task history
- Execute multiple tasks sequentially
- See results and captured screenshots

### Example Workflow

```
🎯 UI STATE CAPTURE SYSTEM
Enter Your Task
👉 Enter task (or 'quit' to exit): Create a database in Notion

[Browser opens and logs in automatically]
[15 seconds for you to enter 2FA code]
[Task executes and captures UI states]

📊 TASK RESULT
✅ Status: SUCCESS
📸 Screenshots: 4
📁 Output Directory: ./outputs/20241106_143022/
📋 Manifest: ./outputs/20241106_143022/manifest.json

What next?
  [1] Run another task
  [2] View history
  [3] Exit
```

### Command Line Mode

Run a single task directly:

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
"Create an issue with high priority in Linear"

# Asana
"Add a new task to my project in Asana"

# GitHub
"Create a new issue in the browser-use repository"
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
├── 20241106_143022/
│   ├── 00_logged_in.png
│   ├── 01_task_step_0.png
│   ├── 02_task_step_1.png
│   ├── 03_final_state.png
│   └── manifest.json
```

### manifest.json

```json
{
  "task": "Create a database in Notion",
  "app": "Notion",
  "email": "anishgillella@gmail.com",
  "executed_at": "2024-11-06T14:30:22.123456",
  "screenshots": [
    {
      "step": 0,
      "name": "logged_in",
      "timestamp": "2024-11-06T14:30:22.123456",
      "file": "outputs/20241106_143022/00_logged_in.png"
    },
    {
      "step": 1,
      "name": "task_step_0",
      "timestamp": "2024-11-06T14:30:25.234567",
      "file": "outputs/20241106_143022/01_task_step_0.png"
    }
  ]
}
```

## How It Works

### 1. App Detection
The system scans your task input for known app names (notion, linear, asana, github).

### 2. Login Flow
- **Navigate**: Goes to the app's login page
- **Email Entry**: Fills in the email field automatically
- **Form Validation**: Periodically checks if password field is filled
- **2FA Wait**: Waits up to 15 seconds for user to enter 2FA code
- **Continuation**: Automatically continues once form is complete

### 3. Task Execution
- The browser-use Agent reads your task
- Uses the ChatBrowserUse LLM to understand the task
- Executes a sequence of browser actions (click, type, scroll, etc.)
- Captures the UI state at each step

### 4. Screenshot Capture
- Captures screenshots before login
- Captures screenshots during task execution
- Captures final state screenshot
- Stores all with metadata in manifest

## Troubleshooting

### "Browser page not accessible"
- Make sure BROWSER_USE_API_KEY is set in .env
- Try increasing the `await asyncio.sleep(2)` in execute_task method

### "No app detected in task"
- Make sure your task mentions an app name (notion, linear, asana, github)
- Example: ✅ "Create a database in Notion"
- Example: ❌ "Create a database"

### Login fails
- Check that email is correct in task_executor.py: `TaskExecutor(email="...")`
- Make sure you're entering the correct 2FA code
- Some apps may have different login flows - update selectors in app_config.py

### Screenshots are blank
- The app might require additional wait time
- Try clicking a button first to ensure page is interactive
- Check if the page selector `.screenshot()` is working

## Architecture Design

See `ARCHITECTURE.md` for details on:
- Current v1 architecture (sequential)
- Proposed v2 architecture (parallel planning + execution)
- Why this approach is generalizable
- Implementation roadmap

## Next Steps

- [ ] Test on 5+ different tasks
- [ ] Create Loom demonstration video
- [ ] Add caching for repeated tasks
- [ ] Implement parallel LLM planner (v2 architecture)
- [ ] Support more apps (Jira, Trello, Slack, etc.)

## Contributing

To add a new app:
1. Add configuration to `app_config.py`
2. Verify login selectors are correct
3. Test with a sample task
4. Update this README

## License

MIT

