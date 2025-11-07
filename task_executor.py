"""
Browser Automation Task Executor

Generalized task executor supporting multiple web applications (Notion, Linear, Jira, Asana, GitHub)
with automatic login, task execution, and UI state capture.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from app_config import AppConfig, detect_app, get_app_config
from browser_use import Agent, Browser
from browser_use.llm import ChatBrowserUse

# Load environment variables
load_dotenv()

# Token pricing (per 1M tokens)
TOKEN_PRICING = {
    "input": 0.50,      # $0.50 per 1M input tokens
    "output": 3.00,     # $3.00 per 1M output tokens
    "cached": 0.10,     # $0.10 per 1M cached tokens
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskExecutor:
    """Execute tasks on any web app with automatic login and screenshot capture"""

    def __init__(self, email: str = "anish.gillella@gmail.com", headless: bool = False):
        self.email = email
        self.headless = headless
        self.password = os.getenv("PASSWORD", "")
        self.screenshots: List[dict] = []
        self.task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f"./outputs/{self.task_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Chrome configuration for persistent cookies
        self.chrome_user_data_dir = Path.home() / ".browser-use-chrome"
        self.chrome_user_data_dir.mkdir(exist_ok=True)
        
        # Token and cost tracking
        self.token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
        }
        self.total_cost = 0.0
    
    def calculate_cost(self, input_tokens: int = 0, output_tokens: int = 0, cached_tokens: int = 0) -> float:
        """Calculate cost based on token usage"""
        cost = (
            (input_tokens / 1_000_000) * TOKEN_PRICING["input"] +
            (output_tokens / 1_000_000) * TOKEN_PRICING["output"] +
            (cached_tokens / 1_000_000) * TOKEN_PRICING["cached"]
        )
        return cost
    
    def update_token_usage(self, history) -> Dict:
        """Extract and update token usage from agent history"""
        token_data = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
        }
        
        try:
            # Try to get usage from history
            if history and hasattr(history, 'usage'):
                usage = history.usage
                if usage:
                    input_tokens = getattr(usage, 'input_tokens', 0)
                    output_tokens = getattr(usage, 'output_tokens', 0)
                    cached_tokens = getattr(usage, 'cache_read_input_tokens', 0)
                    
                    token_data["input_tokens"] = input_tokens
                    token_data["output_tokens"] = output_tokens
                    token_data["cached_tokens"] = cached_tokens
                    token_data["total_tokens"] = input_tokens + output_tokens + cached_tokens
                    token_data["estimated_cost"] = self.calculate_cost(input_tokens, output_tokens, cached_tokens)
                    
                    # Update instance totals
                    self.token_usage["input_tokens"] += input_tokens
                    self.token_usage["output_tokens"] += output_tokens
                    self.token_usage["cached_tokens"] += cached_tokens
                    self.total_cost += token_data["estimated_cost"]
                    
                    logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Cached: {cached_tokens}")
                    logger.info(f"Estimated cost for this run: ${token_data['estimated_cost']:.4f}")
        except Exception as e:
            logger.warning(f"Could not extract token usage: {e}")
        
        return token_data


    async def capture_screenshot(self, page, step_name: str) -> bool:
        """Capture screenshot and store metadata"""
        # Note: Agent history already captures all execution steps
        # Final capture skipped since browser-use returns all screenshots via history.screenshots()
        return True

    def _build_agent_prompt(self, app_config: AppConfig, task: str) -> str:
        """Build the AI agent task prompt with login and execution instructions"""
        return f"""You are an AI agent helping to capture UI states for: {task}

=== LOGIN INSTRUCTIONS ===
1. Navigate to {app_config.url}
2. Click the login button or link
3. When asked for email, ENTER EXACTLY: {self.email}
4. When asked for password, ENTER EXACTLY: {self.password}
5. When prompted for 2FA/authentication code, WAIT UP TO 15 SECONDS for the user to enter it
6. Do NOT try multiple times - wait the full time for user input in the browser
7. Once browser shows workspace (sidebar visible), then proceed with task
8. If login fails after full wait, report failure - DO NOT loop

=== MAIN TASK ===
{task}

=== EXECUTION STEPS ===
1. Complete the entire task as described
2. Save and confirm all changes
3. Wait 3 seconds for persistence
4. RELOAD THE ENTIRE PAGE (press F5 or refresh)
5. Wait 2 seconds for page to load
6. Report success when complete"""

    async def execute_task(self, app_key: str, task: str) -> Dict:
        """Execute a task on the specified app"""
        app_config = get_app_config(app_key)
        if not app_config:
            return {"status": "error", "error": f"Unknown app: {app_key}"}

        logger.info(f"Starting task execution on {app_config.name}")

        browser = None
        try:
            # Initialize Chrome with persistent user data directory (cookies saved automatically)
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            browser = Browser(
                executable_path=chrome_path,
                user_data_dir=str(self.chrome_user_data_dir),
                headless=self.headless,
            )
            await browser.start()
            
            # Get page
            page = await browser.get_current_page()
            if not page:
                return {"status": "error", "error": "Browser page not accessible"}
            
            logger.info(f"Browser initialized (Chrome profile: {self.chrome_user_data_dir})")
            
            # Build agent prompt (Chrome handles cookies automatically)
            agent_prompt = self._build_agent_prompt(app_config, task)
            
            # Create and run agent with cost tracking enabled
            agent = Agent(
                task=agent_prompt,
                llm=ChatBrowserUse(),
                browser_session=browser,
                calculate_cost=True  # Enable cost tracking
            )
            
            # Set timeout based on app complexity
            timeout_seconds = 300.0 if app_key in ["monday"] else 180.0
            logger.info(f"Starting AI Agent execution (timeout: {timeout_seconds}s)")
            history = None
            try:
                history = await asyncio.wait_for(agent.run(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Agent execution timeout ({timeout_seconds} seconds)")
            
            # Extract token usage and calculate cost
            token_data = self.update_token_usage(history)
            
            # Extract and save screenshots from agent history (even on timeout)
            if history and hasattr(history, 'screenshots'):
                try:
                    import base64
                    agent_screenshots = history.screenshots()
                    for i, screenshot_b64 in enumerate(agent_screenshots):
                        screenshot_file = self.output_dir / f"{i:02d}_step_{i}.png"
                        
                        if isinstance(screenshot_b64, str):
                            # Decode base64 to PNG
                            with open(screenshot_file, 'wb') as f:
                                f.write(base64.b64decode(screenshot_b64))
                            
                            self.screenshots.append({
                                "step": len(self.screenshots),
                                "name": f"step_{i}",
                                "timestamp": datetime.now().isoformat(),
                                "file": str(screenshot_file),
                            })
                    logger.info(f"Extracted {len(agent_screenshots)} screenshots from agent history")
                except Exception as e:
                    logger.warning(f"Could not extract screenshots from history: {e}")
            else:
                # Capture final screenshot if no history available (timeout case)
                if page:
                    try:
                        import base64
                        screenshot_data = await page.screenshot()
                        screenshot_file = self.output_dir / "00_final_state.png"
                        with open(screenshot_file, 'wb') as f:
                            f.write(screenshot_data)
                        self.screenshots.append({
                            "step": 0,
                            "name": "final_state",
                            "timestamp": datetime.now().isoformat(),
                            "file": str(screenshot_file),
                        })
                        logger.info("Captured final screenshot from browser")
                    except Exception as e:
                        logger.warning(f"Could not capture final screenshot: {e}")
            
            # Capture final screenshot (Chrome automatically saves cookies to user_data_dir)
            await self.capture_screenshot(page, "final_state")
            
            # Save manifest with token usage and cost
            manifest_file = self.output_dir / "manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump({
                    "task": task,
                    "app": app_config.name,
                    "executed_at": datetime.now().isoformat(),
                    "screenshots_count": len(self.screenshots),
                    "screenshots": self.screenshots,
                    "token_usage": {
                        "input_tokens": token_data.get("input_tokens", 0),
                        "output_tokens": token_data.get("output_tokens", 0),
                        "cached_tokens": token_data.get("cached_tokens", 0),
                        "total_tokens": token_data.get("total_tokens", 0),
                    },
                    "cost": {
                        "estimated_cost_usd": round(token_data.get("estimated_cost", 0.0), 4),
                        "pricing": TOKEN_PRICING,
                    },
                    "cookies_stored_in": str(self.chrome_user_data_dir),
                }, f, indent=2)
            
            logger.info(f"Task completed. Captured {len(self.screenshots)} screenshots")
            logger.info(f"Cookies automatically saved to: {self.chrome_user_data_dir}")
            logger.info(f"💰 Cost Summary: ${token_data.get('estimated_cost', 0.0):.4f} USD")
            logger.info(f"   Input tokens: {token_data.get('input_tokens', 0)}")
            logger.info(f"   Output tokens: {token_data.get('output_tokens', 0)}")
            logger.info(f"   Cached tokens: {token_data.get('cached_tokens', 0)}")
            
            return {
                "status": "success",
                "app": app_config.name,
                "screenshots": len(self.screenshots),
                "output_dir": str(self.output_dir),
                "manifest": str(manifest_file),
                "chrome_profile": str(self.chrome_user_data_dir),
                "token_usage": token_data,
                "estimated_cost_usd": round(token_data.get("estimated_cost", 0.0), 4),
            }

        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
        
        finally:
            if browser:
                try:
                    logger.info("Closing browser session")
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
            sys.exit(0)


async def run_task(task_input: str, headless: bool = False) -> Dict:
    """
    Main entry point - detects app and executes task
    
    Args:
        task_input: Task description (e.g., "Create a database in Notion")
        headless: Whether to run browser in headless mode
    
    Returns:
        Execution result dictionary with status and details
    """
    app_key = detect_app(task_input)
    
    if not app_key:
        from app_config import APPS
        supported = ', '.join(list(APPS.keys()))
        logger.error(f"No app detected in task. Supported: {supported}")
        return {"status": "error", "error": f"App not detected. Supported apps: {supported}"}
    
    logger.info(f"Detected app: {app_key.upper()}")
    
    executor = TaskExecutor(headless=headless)
    return await executor.execute_task(app_key, task_input)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("No task provided")
        print("Usage: python task_executor.py '<task>'")
        print("Example: python task_executor.py 'Create a database in Notion'")
        sys.exit(1)
    
    task = sys.argv[1]
    result = asyncio.run(run_task(task, headless=False))
    print(json.dumps(result, indent=2))

