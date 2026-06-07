from __future__ import annotations
import json
from typing import TYPE_CHECKING, Any, Optional, Type, Tuple, List
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
if TYPE_CHECKING:
    pass 


class ExtractHyperlinksToolInput(BaseModel):
    """Input for ExtractHyperlinksTool."""
    absolute_urls: bool = Field(
        default=False,
        description="Return absolute URLs instead of relative URLs",
    )
    max_links_for_content: int = Field(
        default=5,
        description="Maximum number of links to include in the 'content' string for the LLM. Set to 0 to omit links from content."
    )


class ExtractHyperlinksTool(BaseBrowserTool):
    """Extract all hyperlinks on the page."""
    name: str = "extract_hyperlinks"
    description: str = "Extract all hyperlinks on the current webpage. Returns a summary for the LLM and a list of all unique links as an artifact."
    args_schema: Type[BaseModel] = ExtractHyperlinksToolInput
    response_format: str = "content_and_artifact"

    @model_validator(mode="before")
    @classmethod
    def check_bs_import(cls, values: dict) -> Any:
        """Check that the arguments are valid."""
        try:
            from bs4 import BeautifulSoup  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'beautifulsoup4' package is required to use this tool."
                " Please install it with 'pip install beautifulsoup4'."
            )
        return values


    @staticmethod
    def scrape_page(page_url: str, html_content: str, absolute_urls: bool) -> List[str]:
        """Helper to scrape links. Returns a list of strings."""
        from urllib.parse import urljoin
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "lxml")
        anchors = soup.find_all("a")
        
        links = []
        for anchor in anchors:
            href = anchor.get("href")
            if href: 
                if absolute_urls:
                    links.append(urljoin(page_url, href))
                else:
                    links.append(href)
        
        return list(set(links)) # Return unique links as a list

    def _run(
        self,
        absolute_urls: bool = False,
        max_links_for_content: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[str, List[str]]:
        """Use the tool."""
        if self.sync_browser is None:
            raise ValueError(f"Synchronous browser not provided to {self.name}")
        
        page = get_current_page(self.sync_browser)
        html_content = page.content()
        page_url = page.url # Pass current page URL for urljoin
        
        all_links = self.scrape_page(page_url, html_content, absolute_urls)
        
        content_summary = f"Extracted {len(all_links)} unique hyperlinks."
        if max_links_for_content > 0 and all_links:
            content_summary += " Top links: " + ", ".join(all_links[:max_links_for_content])
            if len(all_links) > max_links_for_content:
                content_summary += "..."
        elif not all_links:
            content_summary += " No links found."

        return content_summary, all_links # Return content string and list of links

    async def _arun(
        self,
        absolute_urls: bool = False,
        max_links_for_content: int = 5,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Tuple[str, List[str]]: 
        """Use the tool asynchronously."""
        if self.async_browser is None:
            raise ValueError(f"Asynchronous browser not provided to {self.name}")
        
        page = await aget_current_page(self.async_browser)
        html_content = await page.content()
        page_url = page.url
        
        all_links = self.scrape_page(page_url, html_content, absolute_urls) # scrape_page is sync
        
        content_summary = f"Extracted {len(all_links)} unique hyperlinks."
        if max_links_for_content > 0 and all_links:
            content_summary += " Top links: " + ", ".join(all_links[:max_links_for_content])
            if len(all_links) > max_links_for_content:
                content_summary += "..."
        elif not all_links:
            content_summary += " No links found."

        return content_summary, all_links # Return content string and list of links