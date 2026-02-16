"""
Texas Comptroller Tax Forms Crawler Agent

Crawls the Texas Comptroller website for tax forms (PDFs),
downloads them, and prepares them for indexing.
"""

import os
import re
import json
import time
import hashlib
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# LangSmith tracing
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "Legal Luminary - Comptroller Agent")

from langsmith import traceable


class TaxForm(TypedDict):
    """Tax form data structure"""

    form_number: str
    title: str
    url: str
    pdf_url: Optional[str]
    category: str
    downloaded: bool
    sha256: Optional[str]
    error: Optional[str]


class ComptrollerCrawlerAgent:
    """Agent that crawls Texas Comptroller for tax forms"""

    BASE_URL = "https://comptroller.texas.gov"
    TAX_FORMS_URL = "https://comptroller.texas.gov/taxforms/"

    # Known tax form categories
    CATEGORIES = [
        "sales",
        "franchise",
        "motor fuel",
        "natural gas",
        "property",
        "inheritance",
        "miscellaneous",
    ]

    def __init__(self, output_dir: str = "./tax_forms"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; Legal-Luminary/1.0)"}
        )
        self.forms: List[TaxForm] = []

    @traceable(name="comptroller-crawl-forms")
    def discover_tax_forms(self) -> List[TaxForm]:
        """Discover all tax forms on the Comptroller website"""
        print("\n=== Discovering Tax Forms ===")

        try:
            response = self.session.get(self.TAX_FORMS_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Find all form links
            forms: List[TaxForm] = []

            # Look for PDF links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)

                # Check if it's a PDF link
                if ".pdf" in href.lower() or "form" in href.lower():
                    # Normalize URL
                    if href.startswith("/"):
                        full_url = self.BASE_URL + href
                    elif not href.startswith("http"):
                        full_url = self.TAX_FORMS_URL + href
                    else:
                        full_url = href

                    # Extract form number from text or URL
                    form_number_match = re.search(r"(\d{2}-\d{3,4})", text + href)
                    form_number = (
                        form_number_match.group(1) if form_number_match else "Unknown"
                    )

                    # Determine category
                    category = "miscellaneous"
                    for cat in self.CATEGORIES:
                        if cat in text.lower() or cat in href.lower():
                            category = cat
                            break

                    form: TaxForm = {
                        "form_number": form_number,
                        "title": text[:200] if text else f"Form {form_number}",
                        "url": full_url,
                        "pdf_url": full_url if ".pdf" in full_url.lower() else None,
                        "category": category,
                        "downloaded": False,
                        "sha256": None,
                        "error": None,
                    }
                    forms.append(form)

            # Remove duplicates based on URL
            seen = set()
            unique_forms = []
            for form in forms:
                if form["url"] not in seen:
                    seen.add(form["url"])
                    unique_forms.append(form)

            self.forms = unique_forms
            print(f"Found {len(self.forms)} tax forms")
            return self.forms

        except Exception as e:
            print(f"Error discovering forms: {e}")
            return []

    @traceable(name="comptroller-download-forms")
    def download_forms(self, max_forms: int = 50) -> List[TaxForm]:
        """Download tax form PDFs"""
        print(f"\n=== Downloading Tax Forms (max {max_forms}) ===")

        downloaded = 0
        for form in self.forms[:max_forms]:
            if not form.get("pdf_url"):
                # Try to find PDF link
                continue

            try:
                pdf_url = form["pdf_url"]
                print(f"Downloading: {form['form_number']} - {form['title'][:40]}...")

                response = self.session.get(pdf_url, timeout=60)
                response.raise_for_status()

                # Generate filename
                safe_name = re.sub(r"[^\w\-]", "_", form["form_number"])
                filename = self.output_dir / f"{safe_name}.pdf"

                # Save PDF
                with open(filename, "wb") as f:
                    f.write(response.content)

                # Calculate SHA256
                sha256_hash = hashlib.sha256(response.content).hexdigest()

                form["downloaded"] = True
                form["sha256"] = sha256_hash
                downloaded += 1

                print(f"  ✓ Saved: {filename.name} ({len(response.content)} bytes)")

            except Exception as e:
                form["error"] = str(e)
                print(f"  ✗ Error: {e}")

            time.sleep(0.5)  # Rate limiting

        print(f"\nDownloaded {downloaded}/{len(self.forms[:max_forms])} forms")
        return self.forms

    @traceable(name="comptroller-summarize")
    def summarize_forms(self) -> Dict[str, Any]:
        """Summarize the downloaded forms"""
        print("\n=== Form Summary ===")

        summary = {
            "timestamp": datetime.now().isoformat(),
            "source": "Texas Comptroller",
            "total_discovered": len(self.forms),
            "total_downloaded": sum(1 for f in self.forms if f["downloaded"]),
            "total_errors": sum(1 for f in self.forms if f["error"]),
            "by_category": {},
            "forms": [],
        }

        # Group by category
        for form in self.forms:
            cat = form["category"]
            if cat not in summary["by_category"]:
                summary["by_category"][cat] = 0
            summary["by_category"][cat] += 1

            # Add to forms list if downloaded
            if form["downloaded"]:
                summary["forms"].append(
                    {
                        "form_number": form["form_number"],
                        "title": form["title"],
                        "category": form["category"],
                        "sha256": form["sha256"],
                        "url": form["url"],
                    }
                )

        print(f"Total discovered: {summary['total_discovered']}")
        print(f"Total downloaded: {summary['total_downloaded']}")
        print(f"Categories: {summary['by_category']}")

        return summary

    def export_index(self, filename: str = "tax_forms_index.json"):
        """Export form index for database agent"""
        index = {
            "source": "Texas Comptroller Tax Forms",
            "crawled_at": datetime.now().isoformat(),
            "count": len(self.forms),
            "forms": [
                {
                    "form_number": f["form_number"],
                    "title": f["title"],
                    "category": f["category"],
                    "url": f["url"],
                    "downloaded": f["downloaded"],
                    "sha256": f["sha256"],
                    "error": f["error"],
                }
                for f in self.forms
            ],
        }

        output_path = self.output_dir / filename
        with open(output_path, "w") as f:
            json.dump(index, f, indent=2)

        print(f"Index exported to {output_path}")
        return output_path

    def run(self, max_download: int = 50):
        """Run the full crawler pipeline"""
        # Discover forms
        self.discover_tax_forms()

        # Download forms
        self.download_forms(max_download)

        # Summarize
        summary = self.summarize_forms()

        # Export index
        self.export_index()

        return summary


if __name__ == "__main__":
    agent = ComptrollerCrawlerAgent()
    result = agent.run(max_download=30)
    print("\n=== Complete ===")
    print(json.dumps(result, indent=2))
