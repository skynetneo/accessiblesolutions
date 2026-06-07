"""Playwright GetElement Tool"""
from __future__ import annotations
import json
from typing import TYPE_CHECKING, List, Optional, Sequence, Type, Tuple, Dict, Any
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from pydantic import BaseModel, Field
from tools.playwright.base import BaseBrowserTool
from tools.playwright.utils import (
    aget_current_page,
    get_current_page,
)

if TYPE_CHECKING:
    from playwright.async_api import Page as AsyncPage
    from playwright.sync_api import Page as SyncPage


class GetElementsToolInput(BaseModel):
    """Input for GetElementsTool."""
    selector: str = Field(
        ...,
        description="CSS selector, such as '*', 'div', 'p', 'a', #id, .classname",
    )
    attributes: List[str] = Field(
        default_factory=lambda: ["innerText"],
        description="List of attributes to retrieve for each element (e.g., 'innerText', 'href', 'id', 'class')."
    )
    max_elements_for_content: int = Field(
        default=3,
        description="Maximum number of elements to summarize in the 'content' string for the LLM. Set to 0 to omit elements from content."
    )


async def _aget_elements(
    page: AsyncPage, selector: str, attributes: Sequence[str]
) -> List[Dict[str, str]]: 
    """Get elements matching the given CSS selector."""
    elements = await page.query_selector_all(selector)
    results = []
    for element in elements:
        result: Dict[str, str] = {} 
        for attribute in attributes:
            val: Optional[str] = None
            if attribute == "innerText":
                val = await element.inner_text()
            elif attribute == "textContent": 
                val = await element.text_content()
            elif attribute == "outerHTML": 
                val = await element.outer_html()
            else:
                val = await element.get_attribute(attribute)
            
            if val is not None and val.strip() != "":
                result[attribute] = val
        if result:
            results.append(result)
    return results


def _get_elements(
    page: SyncPage, selector: str, attributes: Sequence[str]
) -> List[Dict[str, str]]: 
    """Get elements matching the given CSS selector."""
    elements = page.query_selector_all(selector)
    results = []
    for element in elements:
        result: Dict[str, str] = {} 
        for attribute in attributes:
            val: Optional[str] = None
            if attribute == "innerText":
                val = element.inner_text()
            elif attribute == "textContent":
                val = element.text_content()
            elif attribute == "outerHTML":
                val = element.outer_html()
            else:
                val = element.get_attribute(attribute)
            
            if val is not None and val.strip() != "":
                result[attribute] = val
        if result:
            results.append(result)
    return results
    

class GetElementsTool(BaseBrowserTool):
    """Tool for getting elements in the current web page matching a CSS selector. Returns a summary for the LLM and a list of element data as an artifact."""
    name: str = "get_elements"
    description: str = (
        "Retrieve elements in the current web page matching the given CSS selector. Returns a summary for the LLM and a list of element data as an artifact."
    )
    args_schema: Type[BaseModel] = GetElementsToolInput
    response_format: str = "content_and_artifact" 

    def _run(
        self,
        selector: str,
        attributes: Sequence[str] = ["innerText"],
        max_elements_for_content: int = 3,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[str, List[Dict[str, str]]]: 
        """Use the tool."""
        if self.sync_browser is None:
            raise ValueError(f"Synchronous browser not provided to {self.name}")
        page = get_current_page(self.sync_browser)
        
        all_elements = _get_elements(page, selector, attributes)
        
        content_summary = f"Found {len(all_elements)} elements matching selector '{selector}'."
        if max_elements_for_content > 0 and all_elements:
            summary_elements = all_elements[:max_elements_for_content]
            formatted_summary = "\n".join([json.dumps(el, ensure_ascii=False) for el in summary_elements])
            content_summary += f" Top {len(summary_elements)} elements:\n{formatted_summary}"
            if len(all_elements) > max_elements_for_content:
                content_summary += "\n..."
        elif not all_elements:
            content_summary += " No elements found."

        return content_summary, all_elements # Return content string and list of element data

    async def _arun(
        self,
        selector: str,
        attributes: Sequence[str] = ["innerText"],
        max_elements_for_content: int = 3,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Tuple[str, List[Dict[str, str]]]: 
        """Use the tool."""
        if self.async_browser is None:
            raise ValueError(f"Asynchronous browser not provided to {self.name}")
        page = await aget_current_page(self.async_browser)
        
        all_elements = await _aget_elements(page, selector, attributes) # await the async helper
        
        content_summary = f"Found {len(all_elements)} elements matching selector '{selector}'."
        if max_elements_for_content > 0 and all_elements:
            summary_elements = all_elements[:max_elements_for_content]
            formatted_summary = "\n".join([json.dumps(el, ensure_ascii=False) for el in summary_elements])
            content_summary += f" Top {len(summary_elements)} elements:\n{formatted_summary}"
            if len(all_elements) > max_elements_for_content:
                content_summary += "\n..."
        elif not all_elements:
            content_summary += " No elements found."

        return content_summary, all_elements