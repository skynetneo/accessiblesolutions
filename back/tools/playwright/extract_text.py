"""Playwright ExtractText Tool"""
from __future__ import annotations
from typing import Any, Optional, Type, Tuple

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


class ExtractTextToolInput(BaseModel):
    """Input for ExtractTextTool."""
    max_chars_for_content: int = Field(
        default=500, description="Maximum characters of extracted text to include in the 'content' string for the LLM."
    )

class ExtractTextTool(BaseBrowserTool):
    name: str = "extract_text"
    description: str = "Extract all the text on the current webpage."
    args_schema: Type[BaseModel] = ExtractTextToolInput
    response_format: str = "content_and_artifact" 

    @model_validator(mode="before")
    @classmethod
    def check_bs_import(cls, values: dict) -> Any: 
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "The 'beautifulsoup4' package is required to use this tool."
                " Please install it with 'pip install beautifulsoup4'."
            )
        return values

    def _run(
        self,
        max_chars_for_content: int = 500,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Tuple[str, str]: 
        from bs4 import BeautifulSoup
        if self.sync_browser is None:
            raise ValueError(f"Synchronous browser not provided to {self.name}")

        page = get_current_page(self.sync_browser)
        html_content = page.content()
        soup = BeautifulSoup(html_content, "lxml")
        full_text = " ".join(text for text in soup.stripped_strings)

        content_summary = f"Extracted {len(full_text)} characters. Preview: {full_text[:max_chars_for_content]}"
        if len(full_text) > max_chars_for_content:
            content_summary += "..."
        
        return content_summary, full_text

    async def _arun(
        self,
        max_chars_for_content: int = 500,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> Tuple[str, str]: 
        from bs4 import BeautifulSoup
        if self.async_browser is None:
            raise ValueError(f"Asynchronous browser not provided to {self.name}")

        page = await aget_current_page(self.async_browser)
        html_content = await page.content()
        soup = BeautifulSoup(html_content, "lxml")
        full_text = " ".join(text for text in soup.stripped_strings)
        
        content_summary = f"Extracted {len(full_text)} characters. Preview: {full_text[:max_chars_for_content]}"
        if len(full_text) > max_chars_for_content:
            content_summary += "..."

        return content_summary, full_text
