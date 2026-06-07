import base64
from typing import Tuple, Dict, Any, Optional, Type
from pydantic import BaseModel
from langchain_core.tools import BaseTool
from tools.playwright.base import BaseBrowserTool
from tools.playwright.utils import get_current_page, aget_current_page

class CapturePageScreenshotToolInput(BaseModel):
    pass # No specific input needed, captures current page

class WebPageScreenshotTool(BaseBrowserTool):
    name: str = "screenshot"
    description: str = "Captures a screenshot of the current webpage."
    args_schema: Type[BaseModel] = CapturePageScreenshotToolInput
    response_format: str = "content_and_artifact"

    def _run(self, run_manager=None) -> Tuple[str, Dict[str, Any]]:
        if self.sync_browser is None:
            raise ValueError("Sync browser not provided")
        page = get_current_page(self.sync_browser)
        screenshot_bytes = page.screenshot()
        img_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        content = f"Screenshot of {page.url} captured."
        artifact = {"url": page.url, "screenshot_base64": img_base64}
        return content, artifact

    async def _arun(self, run_manager=None) -> Tuple[str, Dict[str, Any]]:
        if self.async_browser is None:
            raise ValueError("Async browser not provided")
        page = await aget_current_page(self.async_browser)
        screenshot_bytes = await page.screenshot()
        img_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        content = f"Screenshot of {page.url} captured."
        artifact = {"url": page.url, "screenshot_base64": img_base64}
        return content, artifact