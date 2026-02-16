"""
Experiment 5: Texas Data Pipeline - Ground Truth Discovery

Tests the crawler against data.texas.gov and other Texas government sources.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

import pytest

os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "Legal Luminary - Exp5")

from langsmith import traceable


# ============================================================
# TEST FIXTURES
# ============================================================


@pytest.fixture
def texas_sources():
    """List of Texas data sources to test"""
    return [
        "data.texas.gov",
        "capitol.texas.gov",
        "statutes.capitol.texas.gov",
        "www.texasattorneygeneral.gov",
        "txcourts.gov",
        "lrl.texas.gov",
        "sll.texas.gov",
        "comptroller.texas.gov",
    ]


@pytest.fixture
def legal_keywords():
    """Legal-related keywords for filtering"""
    return [
        "legal",
        "law",
        "court",
        "attorney",
        "license",
        "permit",
        "regulation",
        "crime",
        "criminal",
        "justice",
        "violation",
        "tdcj",
        "tdi",
        "tdlr",
        "insurance",
        "prison",
    ]


# ============================================================
# TESTS
# ============================================================


@traceable(name="exp5-test-socrata-api")
def test_socrata_api_reachable():
    """Test that Socrata API is reachable"""
    import requests

    url = "https://data.texas.gov/api/views.json?limit=5"
    response = requests.get(url, timeout=10)

    assert response.status_code == 200, "Socrata API should return 200"
    data = response.json()
    assert isinstance(data, list), "Should return a list"
    assert len(data) > 0, "Should return at least one dataset"


@traceable(name="exp5-test-source-reachability")
def test_source_reachability(texas_sources):
    """Test that all Texas sources are reachable"""
    import requests

    results = {}

    for source in texas_sources:
        url = f"https://{source}"
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            results[source] = response.status_code == 200
        except Exception:
            results[source] = False

    # At least 80% should be reachable
    reachable = sum(results.values())
    total = len(results)
    rate = reachable / total

    assert rate >= 0.8, f"Only {rate * 100:.0f}% sources reachable (expected ≥80%)"
    print(f"\nReachability: {reachable}/{total} ({rate * 100:.0f}%)")


@traceable(name="exp5-test-discover-datasets")
def test_discover_datasets():
    """Test dataset discovery from data.texas.gov"""
    import requests

    url = "https://data.texas.gov/api/views.json?limit=50"
    response = requests.get(url, timeout=10)
    data = response.json()

    assert len(data) > 0, "Should discover datasets"

    # Check dataset structure
    for ds in data[:5]:
        assert "id" in ds, "Dataset should have ID"
        assert "name" in ds, "Dataset should have name"


@traceable(name="exp5-test-filter-legal")
def test_filter_legal_datasets(legal_keywords):
    """Test filtering for legal-related datasets"""
    import requests

    url = "https://data.texas.gov/api/views.json?limit=100"
    response = requests.get(url, timeout=10)
    datasets = response.json()

    legal = []
    for ds in datasets:
        text = f"{ds.get('name', '')} {ds.get('description', '')}".lower()
        if any(kw in text for kw in legal_keywords):
            legal.append(ds)

    assert len(legal) > 0, "Should find at least one legal dataset"
    print(f"\nFound {len(legal)} legal datasets out of {len(datasets)}")


@traceable(name="exp5-test-classification")
def test_dataset_classification():
    """Test classification of datasets into categories"""
    import requests

    url = "https://data.texas.gov/api/views.json?limit=50"
    response = requests.get(url, timeout=10)
    datasets = response.json()

    categories = {"LAW_VERIFICATION": [], "NEWS": [], "ATTORNEY_RESOURCE": []}

    for ds in datasets:
        text = f"{ds.get('name', '')} {ds.get('description', '')}".lower()

        if any(
            kw in text for kw in ["court", "case", "criminal", "prison", "dps", "crime"]
        ):
            categories["LAW_VERIFICATION"].append(ds["id"])
        elif any(kw in text for kw in ["news", "report", "press"]):
            categories["NEWS"].append(ds["id"])
        elif any(kw in text for kw in ["attorney", "license", "bar", "permit"]):
            categories["ATTORNEY_RESOURCE"].append(ds["id"])

    total = sum(len(v) for v in categories.values())
    assert total > 0, "Should classify at least some datasets"

    print(
        f"\nClassification: {json.dumps({k: len(v) for k, v in categories.items()}, indent=2)}"
    )


@traceable(name="exp5-test-quality-score")
def test_quality_scoring():
    """Test quality score generation for datasets"""
    import requests

    url = "https://data.texas.gov/api/views.json?limit=20"
    response = requests.get(url, timeout=10)
    datasets = response.json()

    scores = []
    for ds in datasets:
        score = 50  # base

        if ds.get("description") and len(ds["description"]) > 100:
            score += 15
        if ds.get("viewCount", 0) > 100:
            score += 10
        if ds.get("downloadCount", 0) > 50:
            score += 10
        if ds.get("tags") and len(ds["tags"]) > 0:
            score += 5

        scores.append(min(100, score))

    avg = sum(scores) / len(scores)
    assert avg > 0, "Should have positive average quality score"
    print(f"\nAverage quality score: {avg:.1f}")


@traceable(name="exp5-test-api-latency")
def test_api_latency():
    """Test API response time"""
    import requests
    import time

    url = "https://data.texas.gov/api/views.json?limit=10"

    times = []
    for _ in range(5):
        start = time.time()
        response = requests.get(url, timeout=10)
        elapsed = time.time() - start
        times.append(elapsed)

    avg = sum(times) / len(times)
    assert avg < 5.0, f"API too slow: {avg:.2f}s average"
    print(f"\nAverage API latency: {avg:.3f}s")


# ============================================================
# RUNNER
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
