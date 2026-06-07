"""Playwright Navigate Tool"""
from __future__ import annotations
import base64
from typing import Optional, Type, Tuple, Dict, Any
from urllib.parse import urlparse
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from pydantic import BaseModel, Field, model_validator
from tools.playwright.base import BaseBrowserTool
from tools.playwright.utils import (
    aget_current_page,
    get_current_page,
)


class NavigateToolInput(BaseModel):
    """Input for NavigateToolInput."""
    url: str = Field(..., description="url to navigate to")
    take_screenshot: bool = Field(
        default=False,
        description="Whether to take a screenshot after navigating to the URL",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_url_scheme(cls, values: dict) -> dict:
        """Check that the URL scheme is valid."""
        url = values.get("url")
        if url:
            parsed_url = urlparse(url)
            if parsed_url.scheme not in ("http", "https"):
                raise ValueError("URL scheme must be 'http' or 'https'")
        return values


class NavigateTool(BaseBrowserTool):
    """Tool for navigating a browser to a URL.
    Security Note: This tool provides code to control web-browser navigation.
        This tool can navigate to any URL, including internal network URLs, and
        URLs exposed on the server itself.
        However, if exposing this tool to end-users, consider limiting network
        access to the server that hosts the agent.
        By default, the URL scheme has been limited to 'http' and 'https' to
        prevent navigation to local file system URLs (or other schemes).
        If access to the local file system is required, consider creating a custom
        tool or providing a custom args_schema that allows the desired URL schemes."""

    name: str = "navigate"
    description: str = "Navigate a browser to the specified URL and optionally capture a screenshot."
    args_schema: Type[BaseModel] = NavigateToolInput
    response_format: str = "content_and_artifact"  # Key change

    def _run(
        self,
        url: str,
        take_screenshot: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[str, Dict[str, Any]]: # Return type changed
        if self.sync_browser is None:
            raise ValueError(f"Synchronous browser not provided to {self.name}")
        page = get_current_page(self.sync_browser)
        
        content_summary: str
        artifact: Dict[str, Any] = {}

        try:
            response = page.goto(url)
            status = response.status if response else "unknown"
            new_url = page.url
            
            artifact["url"] = new_url
            artifact["status_code"] = status
            
            content_summary = f"Navigated to {new_url}. Status: {status}."

            if take_screenshot:
                screenshot_bytes = page.screenshot()
                artifact["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode('utf-8')
                content_summary += " Screenshot captured."
            
            # Add current page title as part of the "improved current page"
            page_title = page.title()
            artifact["page_title"] = page_title
            content_summary += f" Page title: '{page_title}'."
        except Exception as e:
            content_summary = f"Failed to navigate to {url}. Error: {str(e)}"
            artifact["error"] = str(e)
        return content_summary, artifact
    async def _arun(
        self,
        url: str,
        take_screenshot: bool = False,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Tuple[str, Dict[str, Any]]: # Return type changed
        if self.async_browser is None:
            raise ValueError(f"Asynchronous browser not provided to {self.name}")
        page = await aget_current_page(self.async_browser)
        
        content_summary: str
        artifact: Dict[str, Any] = {}

        try:
            response = await page.goto(url)
            status = response.status if response else "unknown"
            new_url = page.url
            
            artifact["url"] = new_url
            artifact["status_code"] = status
            
            content_summary = f"Navigated to {new_url}. Status: {status}."

            if take_screenshot:
                screenshot_bytes = await page.screenshot()
                artifact["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode('utf-8')
                content_summary += " Screenshot captured."
            
            # Add current page title as part of the "improved current page"
            page_title = await page.title()
            artifact["page_title"] = page_title
            content_summary += f" Page title: '{page_title}'."
        except Exception as e:
            content_summary = f"Failed to navigate to {url}. Error: {str(e)}"
            artifact["error"] = str(e)
        return content_summary, artifact