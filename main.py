#!/usr/bin/env python3
"""
Main Orchestrator - Entry point for the UI State Capture System

This script is the main interface for executing tasks across different web apps.
It handles user input, app detection, and coordinates the task execution.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from app_config import detect_app, get_app_config, APPS
from task_executor import TaskExecutor


class UIStateCaptureOrchestrator:
    """Main orchestrator for the UI state capture system"""

    def __init__(self):
        self.task_history = []
        self.output_base_dir = Path("./outputs")
        self.output_base_dir.mkdir(exist_ok=True)

    def print_header(self, title: str):
        """Print a formatted header"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_section(self, title: str):
        """Print a formatted section header"""
        print(f"\n📌 {title}")
        print("-" * 70)

    async def get_user_input(self) -> Optional[str]:
        """Get task input from user"""
        self.print_section("Enter Your Task")
        
        print("\n💡 Examples:")
        print("  • Create a database in Notion")
        print("  • Create a project in Linear")
        print("  • Add a task in Asana")
        print("  • Create an issue in GitHub")
        
        print("\n🔧 Supported Apps:", ", ".join(APPS.keys()))
        
        task_input = input("\n👉 Enter task (or 'quit' to exit): ").strip()
        
        if task_input.lower() == "quit":
            return None
        
        if not task_input:
            print("❌ Task cannot be empty")
            return await self.get_user_input()
        
        return task_input

    def validate_task(self, task: str) -> bool:
        """Validate that task contains a supported app mention"""
        app_key = detect_app(task)
        
        if not app_key:
            print(f"\n❌ No supported app detected in your task")
            print(f"   Supported apps: {', '.join(APPS.keys())}")
            print(f"\n   ✅ Make sure to mention the app name, e.g.:")
            print(f"      'Create a database in NOTION'")
            return False
        
        return True

    async def execute_task(self, task: str) -> dict:
        """Execute the task and capture UI states"""
        
        # Validate task
        if not self.validate_task(task):
            return {"status": "error", "error": "Invalid task"}
        
        # Detect app
        app_key = detect_app(task)
        app_config = get_app_config(app_key)
        
        self.print_header(f"🚀 EXECUTING TASK ON {app_config.name.upper()}")
        
        print(f"\n📋 Task: {task}")
        print(f"🔑 Email: anish.gillella@gmail.com")
        print(f"⏱️  MFA Wait: {app_config.mfa_wait_time} seconds")
        
        # Create executor
        executor = TaskExecutor(
            email="anish.gillella@gmail.com",
            headless=False  # Always show browser
        )
        
        # Execute task
        result = await executor.execute_task(app_key, task)
        
        # Store in history
        self.task_history.append({
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "app": app_config.name,
            "result": result,
        })
        
        return result

    def display_result(self, result: dict):
        """Display task execution result"""
        
        self.print_section("📊 TASK RESULT")
        
        if result.get("status") == "success":
            print(f"✅ Status: SUCCESS")
            print(f"📸 Screenshots: {result.get('screenshots', 0)}")
            print(f"📁 Output Directory: {result.get('output_dir', 'N/A')}")
            print(f"📋 Manifest: {result.get('manifest', 'N/A')}")
            
            # Show manifest content
            manifest_path = Path(result.get("manifest", ""))
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                print(f"\n📄 Captured UI States:")
                for screenshot in manifest["screenshots"]:
                    print(f"   • [{screenshot['step']}] {screenshot['name']}")
        
        else:
            print(f"❌ Status: FAILED")
            error_msg = result.get("error", "Unknown error")
            print(f"   Error: {error_msg}")

    async def show_history(self):
        """Show task execution history"""
        
        if not self.task_history:
            print("\n📭 No tasks executed yet")
            return
        
        self.print_section("📜 TASK HISTORY")
        
        for i, entry in enumerate(self.task_history, 1):
            timestamp = entry.get("timestamp", "N/A")
            task = entry.get("task", "N/A")
            app = entry.get("app", "N/A")
            status = entry.get("result", {}).get("status", "unknown")
            
            status_icon = "✅" if status == "success" else "❌"
            print(f"\n{i}. {status_icon} [{app}] {task}")
            print(f"   📅 {timestamp}")
            print(f"   📊 Status: {status}")

    async def interactive_loop(self):
        """Main interactive loop"""
        
        self.print_header("🎯 UI STATE CAPTURE SYSTEM")
        
        print("\n" + """
This system automatically navigates web applications and captures UI states
for any task you request. It works across Notion, Linear, Asana, GitHub, and more.

Key Features:
  ✨ Generalizable - Works with any app
  🔐 Smart Login - Handles 2FA automatically  
  📸 UI Capture - Screenshots + manifest at each step
  🤖 AI-Powered - Uses Browser Use + ChatBrowserUse LLM
        """)
        
        while True:
            # Get user input
            task = await self.get_user_input()
            if task is None:
                break
            
            # Execute task
            result = await self.execute_task(task)
            
            # Display result
            self.display_result(result)
            
            # Ask what to do next
            print("\n" + "-" * 70)
            print("What next?")
            print("  [1] Run another task")
            print("  [2] View history")
            print("  [3] Exit")
            
            choice = input("\n👉 Enter choice (1-3): ").strip()
            
            if choice == "2":
                await self.show_history()
            elif choice == "3":
                break

    async def run(self):
        """Run the orchestrator"""
        try:
            await self.interactive_loop()
            
            self.print_section("👋 GOODBYE")
            print(f"Total tasks executed: {len(self.task_history)}")
            
            if self.task_history:
                print(f"✅ Successful: {sum(1 for h in self.task_history if h['result'].get('status') == 'success')}")
                print(f"❌ Failed: {sum(1 for h in self.task_history if h['result'].get('status') != 'success')}")
            
            print("\n📁 All outputs saved to: ./outputs/")
            print()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Orchestrator error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


async def main():
    """Main entry point"""
    orchestrator = UIStateCaptureOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())

