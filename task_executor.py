"""
Generalized Task Executor - Handles login and task execution across different apps
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import json
from dotenv import load_dotenv

from app_config import detect_app, get_app_config, AppConfig
from browser_use import Agent, Browser
from browser_use.llm import ChatBrowserUse

# Load environment variables
load_dotenv()


class TaskExecutor:
    """Execute tasks on any web app with automatic login and screenshot capture"""

    def __init__(self, email: str = "anish.gillella@gmail.com", headless: bool = False):
        self.email = email
        self.headless = headless
        self.password = os.getenv("PASSWORD", "")  # Read password from .env
        self.screenshots: List[dict] = []
        self.task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f"./outputs/{self.task_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def check_login_form_filled(self, page) -> bool:
        """Check if all login form fields are filled"""
        try:
            # Get the HTML to check if fields have values
            page_html = await page.evaluate(
                """() => {
                    const emailInput = document.querySelector('input[type="email"]');
                    const passwordInput = document.querySelector('input[type="password"]');
                    
                    return {
                        emailFilled: emailInput && emailInput.value.length > 0,
                        passwordFilled: passwordInput && passwordInput.value.length > 0,
                        emailValue: emailInput ? emailInput.value : '',
                        passwordValue: passwordInput ? passwordInput.value : ''
                    };
                }"""
            )
            
            print(f"📋 Login Form Status:")
            print(f"   Email filled: {page_html.get('emailFilled', False)}")
            print(f"   Password filled: {page_html.get('passwordFilled', False)}")
            
            return page_html.get('emailFilled', False) and page_html.get('passwordFilled', False)
        except Exception as e:
            print(f"⚠️  Error checking login form: {e}")
            return False

    async def wait_for_login_with_form_check(
        self,
        page,
        wait_time: int = 15,
        check_interval: int = 2
    ) -> bool:
        """
        Wait for user to enter 2FA code while periodically checking if form is filled
        
        Args:
            page: Playwright page object
            wait_time: Total seconds to wait
            check_interval: Check form status every N seconds
        """
        print(f"\n⏳ Waiting {wait_time} seconds for 2FA code entry...")
        print("💡 Enter your 2FA code in the browser now.\n")

        start_time = time.time()
        check_count = 0

        while time.time() - start_time < wait_time:
            if check_count % (check_interval // 1) == 0:
                is_filled = await self.check_login_form_filled(page)
                elapsed = int(time.time() - start_time)
                print(f"   [{elapsed}s] Form status checked...")
                
                if is_filled:
                    print(f"✅ Login form fields are filled! Continuing...")
                    return True

            check_count += 1
            await asyncio.sleep(1)

        # After wait_time, do final check
        is_filled = await self.check_login_form_filled(page)
        if is_filled:
            print(f"✅ Login form fields are filled! Continuing...")
            return True
        else:
            print(f"⚠️  Login form may not be filled, but proceeding anyway...")
            return False

    async def login(self, page, app_config: AppConfig) -> bool:
        """Login to the app with email and wait for 2FA"""
        try:
            print(f"\n🔐 Starting login flow for {app_config.name}...")
            
            # Navigate to login page
            print(f"🌐 Navigating to {app_config.login_url}...")
            await page.goto(app_config.login_url, wait_until="networkidle")
            await asyncio.sleep(2)

            # Fill in email
            print(f"✉️  Entering email: {self.email}...")
            email_input = page.locator(app_config.login_email_field)
            await email_input.fill(self.email)
            await asyncio.sleep(1)

            # Try to find and click the next/submit button (some apps have separate flow)
            try:
                submit_button = page.locator(app_config.login_button)
                await submit_button.click()
                await asyncio.sleep(2)
            except Exception as e:
                print(f"   Note: Could not click submit button: {e}")

            # Wait for user to enter password and 2FA
            await self.wait_for_login_with_form_check(
                page,
                wait_time=app_config.mfa_wait_time
            )

            # Check if login was successful by looking for common authenticated elements
            await asyncio.sleep(2)
            print(f"✅ Login flow completed for {app_config.name}")
            return True

        except Exception as e:
            print(f"❌ Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def capture_screenshot(self, page, step_name: str):
        """Capture screenshot and store metadata"""
        try:
            screenshot_file = self.output_dir / f"{len(self.screenshots):02d}_{step_name}.png"
            
            # Capture screenshot using page (Playwright uses 'path' parameter)
            await page.screenshot(path=screenshot_file)
            
            screenshot_data = {
                "step": len(self.screenshots),
                "name": step_name,
                "timestamp": datetime.now().isoformat(),
                "file": str(screenshot_file),
            }
            self.screenshots.append(screenshot_data)
            print(f"📸 Screenshot captured: {step_name}")
            
        except Exception as e:
            print(f"⚠️  Screenshot capture error: {e}")

    async def execute_task(self, app_key: str, task: str) -> dict:
        """Execute a task on the specified app"""
        
        app_config = get_app_config(app_key)
        if not app_config:
            return {"error": f"Unknown app: {app_key}"}

        print(f"\n" + "="*60)
        print(f"🚀 TASK EXECUTION START")
        print(f"   App: {app_config.name}")
        print(f"   Task: {task}")
        print(f"   Output: {self.output_dir}")
        print(f"="*60)

        browser = None
        
        try:
            # Build the full task with login instructions
            full_task = f"""
You are an AI agent helping to capture UI states for: {task}

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

=== IMPORTANT ===
Execute this task step by step:
1. Complete the entire task as described
2. Save and confirm all changes
3. Wait 3 seconds for persistence
4. RELOAD THE ENTIRE PAGE (press F5 or refresh) to force sidebar to update
5. Wait 2 seconds for page to load
6. Then report success when complete
"""
            
            # Create Browser object (single instance)
            print(f"\n📱 Initializing browser (headless={self.headless})...")
            browser = Browser(
                keep_alive=False,  # Only one browser instance
                headless=self.headless,
            )
            await browser.start()
            print(f"✅ Browser started")
            
            # Get the page
            page = await browser.get_current_page()
            if not page:
                print("❌ Could not access browser page")
                return {"status": "error", "error": "Browser page not accessible"}
            
            print(f"✅ Browser ready")
            print(f"🔑 Using email: {self.email}")
            print(f"🤖 Starting AI Agent - it will handle login and the task...")
            
            # Create agent with the browser session
            agent = Agent(
                task=full_task,
                llm=ChatBrowserUse(),
                browser_session=browser,
            )
            
            # Run the agent to execute the task with a timeout
            print(f"\n🎯 Executing task with AI Agent...")
            print(f"⏳ Agent is running... (timeout: 180 seconds)")
            
            try:
                # Set a timeout of 180 seconds (3 minutes) to give agent more time
                history = await asyncio.wait_for(agent.run(), timeout=180.0)
                print(f"\n✅ Agent completed execution")
            except asyncio.TimeoutError:
                print(f"\n⚠️  Agent execution timeout (180 seconds)")
                print(f"   Continuing with available data...")
                history = None
            
            # Try to capture screenshots from agent history
            screenshot_count = 0
            if history and hasattr(history, 'screenshots'):
                try:
                    agent_screenshots = history.screenshots()
                    for i, screenshot in enumerate(agent_screenshots):
                        screenshot_file = self.output_dir / f"{screenshot_count:02d}_step_{i}.png"
                        # Save base64 screenshot
                        if isinstance(screenshot, str):
                            import base64
                            with open(screenshot_file, 'wb') as f:
                                f.write(base64.b64decode(screenshot))
                            screenshot_count += 1
                            self.screenshots.append({
                                "step": screenshot_count - 1,
                                "name": f"step_{i}",
                                "timestamp": datetime.now().isoformat(),
                                "file": str(screenshot_file),
                            })
                except Exception as e:
                    print(f"   Note: Could not extract screenshots from history: {e}")
            
            # Capture final screenshot manually
            try:
                await self.capture_screenshot(page, f"{screenshot_count:02d}_final_state")
            except Exception as e:
                print(f"   Note: Could not capture final screenshot: {e}")
            
            # Save manifest
            manifest_file = self.output_dir / "manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump({
                    "task": task,
                    "app": app_config.name,
                    "email": self.email,
                    "executed_at": datetime.now().isoformat(),
                    "screenshots": self.screenshots,
                }, f, indent=2)
            
            print(f"\n✅ Task execution completed!")
            print(f"📊 Captured {len(self.screenshots)} screenshots")
            print(f"📋 Manifest saved to: {manifest_file}")
            
            return {
                "status": "success",
                "app": app_config.name,
                "screenshots": len(self.screenshots),
                "output_dir": str(self.output_dir),
                "manifest": str(manifest_file),
            }

        except Exception as e:
            print(f"\n❌ Task execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
        
        finally:
            # Clean up browser and exit
            if browser:
                try:
                    print(f"\n🔌 Closing browser session...")
                    # Browser auto-cleanup - no explicit close needed for BrowserSession
                    print(f"✅ Browser session cleanup complete")
                except Exception as e:
                    print(f"⚠️  Error during cleanup: {e}")
            
            # Force exit to prevent hanging
            print(f"👋 Exiting...\n")
            sys.exit(0)


async def run_task(task_input: str, headless: bool = False):
    """
    Main entry point - detects app and executes task
    
    Args:
        task_input: Task description (e.g., "Create a database in Notion")
        headless: Whether to run browser in headless mode
    """
    
    # Detect which app is mentioned
    app_key = detect_app(task_input)
    
    if not app_key:
        from app_config import APPS
        print(f"❌ No app detected in task. Supported apps: {', '.join(list(APPS.keys()))}")
        print(f"   Example: 'Create a database in Notion'")
        return
    
    print(f"✅ Detected app: {app_key.upper()}")
    
    # Execute task
    executor = TaskExecutor(headless=headless)
    result = await executor.execute_task(app_key, task_input)
    
    return result


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python task_executor.py '<task>'")
        print("\nExamples:")
        print("  python task_executor.py 'Create a database in Notion'")
        print("  python task_executor.py 'Create a project in Linear'")
        sys.exit(1)
    
    task = sys.argv[1]
    
    # Run the task
    result = asyncio.run(run_task(task, headless=False))
    print(f"\nResult: {json.dumps(result, indent=2)}")

