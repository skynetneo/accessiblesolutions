from __future__ import annotations
import json
import base64
from typing import List, Optional, Type, Tuple, Dict, Any
from urllib.parse import quote_plus
from pydantic import BaseModel, Field
from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from tools.playwright.base import BaseBrowserTool
from tools.playwright.utils import get_current_page, aget_current_page
from bs4 import BeautifulSoup 

class WebSearchToolInput(BaseModel):
    query: str = Field(..., description="The search query.")
    engine: str = Field(
        default="duckduckgo", 
        description="Search engine to use ('duckduckgo' or 'brave')."
    )
    num_results: int = Field(
        default=2, description="Number of top results to extract details for."
    )
    take_screenshot: bool = Field(
        default=False, description="Whether to take a screenshot of the search results page."
    )

class WebSearchTool(BaseBrowserTool):
    name: str = "search_web"
    description: str = (
        "Performs a web search using DuckDuckGo or Brave and extracts top results."
    )
    args_schema: Type[BaseModel] = WebSearchToolInput
    response_format: str = "content_and_artifact"

    def _extract_duckduckgo_results(self, page_content: str, num_results: int) -> List[Dict[str, str]]:
        soup = BeautifulSoup(page_content, "lxml")
        results = []
        # This selector is specific to DuckDuckGo and might change. Robust parsing is complex.
        for article in soup.select("article[data-testid='result']", limit=num_results):
            title_tag = article.select_one("h2 a span")
            link_tag = article.select_one("div a[data-testid='result-title-a']")
            snippet_tag = article.select_one("div[data-testid='result-extras-body'] span") # May vary

            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else "N/A"
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else "N/A"
            
            if title != "N/A" and link != "N/A":
                 results.append({"title": title, "link": link, "snippet": snippet})
        return results

    def _extract_brave_results(self, page_content: str, num_results: int) -> List[Dict[str, str]]:
        soup = BeautifulSoup(page_content, "lxml")
        results = []
        # Selector for Brave Search - highly likely to change.
        # Inspect Brave Search results page for current selectors.
        # Example (very brittle):
        for result_div in soup.select("div.snippet", limit=num_results): # This is a guess
            title_tag = result_div.select_one("span.snippet-title")
            link_tag = result_div.select_one("a.result-header")
            snippet_tag = result_div.select_one("p.snippet-description")

            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else "N/A"
            # Brave might require resolving relative links if 'href' is not absolute
            if link_tag and link_tag.has_attr('href') and not link.startswith('http'):
                link = f"https://search.brave.com{link}" # Or resolve properly
            
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else "N/A"

            if title != "N/A" and link != "N/A":
                results.append({"title": title, "link": link, "snippet": snippet})
        return results


    def _run(
        self,
        query: str,
        engine: str = "duckduckgo",
        num_results: int = 2,
        take_screenshot: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        if self.sync_browser is None:
            raise ValueError(f"Synchronous browser not provided to {self.name}")
        page = get_current_page(self.sync_browser)

        search_url: str
        if engine.lower() == "brave":
            search_url = f"https://search.brave.com/search?q={quote_plus(query)}"
        else:  # Default to duckduckgo
            search_url = f"https://duckduckgo.com/?q={quote_plus(query)}&ia=web"
        
        artifact: Dict[str, Any] = {"search_engine": engine, "query": query, "search_url": search_url}
        content_summary: str

        try:
            page.goto(search_url)
            page_content = page.content()
            
            extracted_results: List[Dict[str, str]]
            if engine.lower() == "brave":
                extracted_results = self._extract_brave_results(page_content, num_results)
            else:
                extracted_results = self._extract_duckduckgo_results(page_content, num_results)
            
            artifact["results"] = extracted_results
            content_summary = f"Search for '{query}' on {engine} yielded {len(extracted_results)} results. "
            if extracted_results:
                content_summary += "Top result: " + extracted_results[0].get('title', '')

            if take_screenshot:
                screenshot_bytes = page.screenshot()
                artifact["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode('utf-8')
                content_summary += " Screenshot of results page captured."
            
            artifact["page_title"] = page.title()

        except Exception as e:
            content_summary = f"Error during web search for '{query}' on {engine}: {str(e)}"
            artifact["error"] = str(e)

        return content_summary, artifact

    async def _arun(
        self,
        query: str,
        engine: str = "duckduckgo",
        num_results: int = 2,
        take_screenshot: bool = False,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Perform a web search using DuckDuckGo or Brave and extract top results."""
        if self.async_browser is None:
            raise ValueError(f"Asynchronous browser not provided to {self.name}")
        page = await aget_current_page(self.async_browser)

        search_url: str
        if engine.lower() == "brave":
            search_url = f"https://search.brave.com/search?q={quote_plus(query)}"
        else:
            search_url = f"https://duckduckgo.com/?q={quote_plus(query)}&ia=web"
        
        artifact: Dict[str, Any] = {"search_engine": engine, "query": query, "search_url": search_url}
        content_summary: str

        try:
            await page.goto(search_url)
            page_content = await page.content()
            
            extracted_results: List[Dict[str, str]]
            if engine.lower() == "brave":
                extracted_results = self._extract_brave_results(page_content, num_results) # Note: _extract methods are sync
            else:
                extracted_results = self._extract_duckduckgo_results(page_content, num_results) # Note: _extract methods are sync
            
            artifact["results"] = extracted_results
            content_summary = f"Search for '{query}' on {engine} yielded {len(extracted_results)} results. "
            if extracted_results:
                content_summary += "Top result: " + extracted_results[0].get('title', '')


            if take_screenshot:
                screenshot_bytes = await page.screenshot()
                artifact["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode('utf-8')
                content_summary += " Screenshot of results page captured."
            
            artifact["page_title"] = await page.title()

        except Exception as e:
            content_summary = f"Error during web search for '{query}' on {engine}: {str(e)}"
            artifact["error"] = str(e)

        return content_summary, artifact