"""
Comptroller Crawler Agent - LangGraph ReAct Agent

Crawls Texas Comptroller website for tax forms using the ReAct pattern.
Traced with LangSmith.
"""

import os
import re
import json
import hashlib
import time
from pathlib import Path
from typing import TypedDict, List, Optional, Dict, Any, Annotated
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "Legal Luminary - Comptroller Agent")

from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from langgraph.prebuilt import ToolNode
from langsmith import traceable

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_ollama import ChatOllama


# ============================================================
# STATE DEFINITIONS
# ============================================================


@dataclass
class InputState:
    """Input state - messages from user"""

    messages: Annotated[list[AnyMessage], add_messages] = field(default_factory=list)


@dataclass
class State(InputState):
    """Full agent state"""

    is_last_step: IsLastStep = field(default=False)
    # Comptroller-specific state
    forms_discovered: List[Dict[str, Any]] = field(default_factory=list)
    forms_downloaded: List[Dict[str, Any]] = field(default_factory=list)
    summaries: List[Dict[str, Any]] = field(default_factory=list)
    indexed_count: int = 0
    errors: List[str] = field(default_factory=list)


# ============================================================
# TOOLS
# ============================================================


class ComptrollerTools:
    """Tools for the Comptroller crawler agent"""

    def __init__(self):
        self.base_url = "https://comptroller.texas.gov"
        self.session = None

    async def search_comptroller(self, query: str) -> str:
        """Search the Comptroller website for tax forms"""
        import requests
        from bs4 import BeautifulSoup

        try:
            # Try to search the tax forms page
            url = f"{self.base_url}/taxforms/"
            response = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Legal-Luminary/1.0)"},
            )

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract form links
            forms = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)

                if "form" in text.lower() or ".pdf" in href.lower():
                    if href.startswith("/"):
                        href = self.base_url + href
                    forms.append(f"{text}: {href}")

            return f"Found {len(forms)} form links. First 10: {forms[:10]}"

        except Exception as e:
            return f"Search error: {str(e)}"

    async def discover_tax_forms(self, category: str = "sales") -> str:
        """Discover tax forms by category"""
        import requests
        from bs4 import BeautifulSoup

        forms = []

        try:
            # Try different category pages
            url = f"{self.base_url}/taxforms/{category}/"
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                # Try main page
                url = f"{self.base_url}/taxforms/"
                response = requests.get(url, timeout=30)

            soup = BeautifulSoup(response.text, "html.parser")

            # Find all form links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)

                # Look for PDF forms
                if ".pdf" in href.lower() and "form" in text.lower():
                    if href.startswith("/"):
                        href = self.base_url + href

                    form_num = re.search(r"(\d{2}-\d{3,4})", text + href)
                    form_number = form_num.group(1) if form_num else "Unknown"

                    forms.append(
                        {
                            "form_number": form_number,
                            "title": text[:100],
                            "url": href,
                            "category": category,
                        }
                    )

            return json.dumps(forms[:20], indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    async def download_form(self, url: str, form_number: str) -> str:
        """Download a tax form PDF"""
        import requests

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            # Save to temp
            output_dir = Path("./tax_forms")
            output_dir.mkdir(exist_ok=True)

            safe_name = re.sub(r"[^\w\-]", "_", form_number)
            filepath = output_dir / f"{safe_name}.pdf"

            with open(filepath, "wb") as f:
                f.write(response.content)

            # Calculate hash
            sha256 = hashlib.sha256(response.content).hexdigest()

            return json.dumps(
                {
                    "success": True,
                    "form_number": form_number,
                    "filepath": str(filepath),
                    "size": len(response.content),
                    "sha256": sha256,
                }
            )

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    async def summarize_form(self, form_number: str, content: str) -> str:
        """Summarize a tax form using LLM"""
        try:
            llm = ChatOllama(
                model="llama3.2:1b", base_url="http://localhost:11434", temperature=0.3
            )

            prompt = f"""Summarize this tax form in simple terms:
            
Form Number: {form_number}
Content: {content[:2000]}

Provide:
1. What type of tax this form is for
2. Who needs to file it
3. Key deadlines
4. Any important notes
"""
            response = llm.invoke([{"role": "user", "content": prompt}])

            return response.content

        except Exception as e:
            return f"Summary error: {str(e)}"


# Create tools instance
comptroller_tools = ComptrollerTools()
TOOLS = [
    comptroller_tools.search_comptroller,
    comptroller_tools.discover_tax_forms,
    comptroller_tools.download_form,
    comptroller_tools.summarize_form,
]


# ============================================================
# LANGGRAPH COMPONENTS
# ============================================================


def create_comptroller_agent():
    """Create the Comptroller crawler agent graph"""
    from langgraph.graph import StateGraph
    from langgraph.runtime import Runtime
    from react_agent.context import Context
    from react_agent.utils import load_chat_model

    builder = StateGraph(State, input_schema=InputState)

    async def call_model(state: State, runtime: Runtime) -> dict:
        """Call the LLM with tools"""
        model = load_chat_model(runtime.context.model).bind_tools(TOOLS)

        system_prompt = """You are a Texas Comptroller Tax Forms research assistant.
Your job is to:
1. Discover tax forms on the Comptroller website
2. Download relevant PDF forms
3. Summarize each form for legal/business use

Use the available tools to search and download forms."""

        response = await model.ainvoke(
            [{"role": "system", "content": system_prompt}, *state.messages]
        )

        return {"messages": [response]}

    def route_output(state: State) -> str:
        """Route based on model output"""
        last_msg = state.messages[-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"
        return "__end__"

    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(TOOLS))

    builder.add_edge("__start__", "agent")
    builder.add_conditional_edges("agent", route_output)
    builder.add_edge("tools", "agent")

    return builder.compile(name="ComptrollerCrawler")


# ============================================================
# STANDALONE FUNCTIONS (for direct use)
# ============================================================


@traceable(name="comptroller-discover-forms")
def discover_forms(category: str = "sales") -> Dict[str, Any]:
    """Discover tax forms from Comptroller website"""
    import requests
    from bs4 import BeautifulSoup

    base_url = "https://comptroller.texas.gov"
    forms = []

    try:
        response = requests.get(
            f"{base_url}/taxforms/", timeout=30, headers={"User-Agent": "Mozilla/5.0"}
        )
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            if ".pdf" in href.lower():
                if href.startswith("/"):
                    href = base_url + href

                form_num = re.search(r"(\d{2}-\d{3,4})", text + href)
                form_number = form_num.group(1) if form_num else "Unknown"

                forms.append(
                    {
                        "form_number": form_number,
                        "title": text[:100],
                        "url": href,
                        "category": category,
                    }
                )

        return {"success": True, "count": len(forms), "forms": forms[:50]}

    except Exception as e:
        return {"success": False, "error": str(e)}


@traceable(name="comptroller-download-form")
def download_form(url: str, form_number: str) -> Dict[str, Any]:
    """Download a single tax form"""
    import requests

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        output_dir = Path("./tax_forms")
        output_dir.mkdir(exist_ok=True)

        safe_name = re.sub(r"[^\w\-]", "_", form_number)
        filepath = output_dir / f"{safe_name}.pdf"

        with open(filepath, "wb") as f:
            f.write(response.content)

        sha256 = hashlib.sha256(response.content).hexdigest()

        return {
            "success": True,
            "form_number": form_number,
            "filepath": str(filepath),
            "size": len(response.content),
            "sha256": sha256,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@traceable(name="comptroller-summarize-form")
def summarize_form(form_info: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize a tax form using LLM"""
    try:
        llm = ChatOllama(
            model="llama3.2:1b", base_url="http://localhost:11434", temperature=0.3
        )

        prompt = f"""Summarize this Texas tax form:

Form Number: {form_info.get("form_number", "Unknown")}
Title: {form_info.get("title", "N/A")}
URL: {form_info.get("url", "N/A")}

Provide a brief summary covering:
1. What tax type this is for
2. Who must file
3. Key deadlines
"""
        response = llm.invoke([{"role": "user", "content": prompt}])

        return {
            "success": True,
            "form_number": form_info.get("form_number"),
            "summary": response.content,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# MAIN RUNNER
# ============================================================


def run_crawler(max_forms: int = 20):
    """Run the full crawler pipeline"""
    print("=== Texas Comptroller Tax Forms Crawler ===\n")

    # Discover forms
    print("Discovering tax forms...")
    result = discover_forms()

    if not result.get("success"):
        print(f"Error: {result.get('error')}")
        return

    forms = result.get("forms", [])[:max_forms]
    print(f"Found {len(forms)} forms\n")

    downloaded = []
    summaries = []

    for form in forms:
        form_num = form.get("form_number", "Unknown")
        url = form.get("url", "")

        print(f"Processing: {form_num} - {form.get('title', '')[:40]}...")

        # Download
        dl_result = download_form(url, form_num)

        if dl_result.get("success"):
            print(f"  ✓ Downloaded: {dl_result.get('filepath')}")
            downloaded.append(dl_result)

            # Summarize
            sum_result = summarize_form(form)
            if sum_result.get("success"):
                print(f"  ✓ Summarized")
                summaries.append(sum_result)
            else:
                print(f"  ✗ Summary failed: {sum_result.get('error')}")
        else:
            print(f"  ✗ Download failed: {dl_result.get('error')}")

        time.sleep(0.5)

    # Save index
    index = {
        "source": "Texas Comptroller Tax Forms",
        "crawled_at": json.dumps({"$date": "2026-02-16T00:00:00Z"}),
        "total_discovered": len(forms),
        "total_downloaded": len(downloaded),
        "forms": [
            {
                "form_number": f.get("form_number"),
                "title": f.get("title"),
                "url": f.get("url"),
                "sha256": d.get("sha256"),
                "filepath": d.get("filepath"),
            }
            for f, d in zip(forms, downloaded)
        ],
    }

    index_path = Path("./tax_forms_index.json")
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"\n=== Complete ===")
    print(f"Discovered: {len(forms)}")
    print(f"Downloaded: {len(downloaded)}")
    print(f"Index saved to: {index_path}")

    return index


if __name__ == "__main__":
    run_crawler(max_forms=10)
