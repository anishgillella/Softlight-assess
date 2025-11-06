"""
App Configuration - Define login flows and URLs for different apps
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AppConfig:
    """Configuration for each supported app"""
    name: str
    url: str
    login_url: str
    login_email_field: str  # CSS selector for email field
    login_password_field: str  # CSS selector for password field
    login_button: str  # CSS selector for login button
    mfa_wait_time: int = 15  # Seconds to wait for 2FA


# App configurations
APPS: Dict[str, AppConfig] = {
    "notion": AppConfig(
        name="Notion",
        url="https://www.notion.so",
        login_url="https://www.notion.so/login",
        login_email_field="input[type='email']",
        login_password_field="input[type='password']",
        login_button="button[type='submit']",
        mfa_wait_time=15,
    ),
    "linear": AppConfig(
        name="Linear",
        url="https://linear.app",
        login_url="https://linear.app/login",
        login_email_field="input[type='email']",
        login_password_field="input[type='password']",
        login_button="button[type='submit']",
        mfa_wait_time=15,
    ),
    "asana": AppConfig(
        name="Asana",
        url="https://app.asana.com",
        login_url="https://app.asana.com/-/login",
        login_email_field="input[type='email']",
        login_password_field="input[type='password']",
        login_button="button[type='submit']",
        mfa_wait_time=15,
    ),
    "github": AppConfig(
        name="GitHub",
        url="https://github.com",
        login_url="https://github.com/login",
        login_email_field="input[name='login']",
        login_password_field="input[name='password']",
        login_button="input[type='submit']",
        mfa_wait_time=15,
    ),
    "jira": AppConfig(
        name="Jira",
        url="https://www.atlassian.com/software/jira",
        login_url="https://id.atlassian.com/login",
        login_email_field="input[name='email']",
        login_password_field="input[name='password']",
        login_button="button[type='submit']",
        mfa_wait_time=15,
    ),
}


def detect_app(task: str) -> str:
    """Detect which app is mentioned in the task"""
    task_lower = task.lower()
    for app_key in APPS.keys():
        if app_key in task_lower:
            return app_key
    return None


def get_app_config(app_key: str) -> AppConfig:
    """Get config for an app"""
    return APPS.get(app_key.lower())

