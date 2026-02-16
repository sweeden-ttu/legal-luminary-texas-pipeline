# Legal Luminary - Texas Data Pipeline

LangGraph agents for crawling and indexing Texas government data.

## Overview

This project implements Experiment 5 (Texas Data Pipeline) from the CS5374 Software Verification and Validation course at Texas Tech University.

## Components

- **Comptroller Agent** - Crawls Texas Comptroller website for tax forms
- **Texas Data Crawler** - Crawls data.texas.gov via Socrata SODA API
- **Multi-Source Crawler** - Crawls all Texas government sources

## Files

```
├── agents/
│   ├── comptroller_agent.py      # LangGraph ReAct agent
│   └── comptroller_crawler.py    # Standalone crawler
├── experiments/
│   └── test_exp5_texas_data.py   # Experiment 5 tests
├── config/
│   └── settings.py               # Configuration
├── data/
│   ├── texas_multi_source_data.json
│   ├── texas_legal_datasets.csv
│   └── comptroller_tax_forms.json
└── texas_data_crawler.js         # Node.js crawler
```

## Usage

```bash
# Run crawler
node texas_data_crawler.js

# Run tests
python -m pytest experiments/
```

## Sources Crawled

- data.texas.gov (Socrata)
- capitol.texas.gov
- comptroller.texas.gov
- txcourts.gov
- lrl.texas.gov
- And more...

## LangSmith Tracing

All agents are traced with LangSmith for observability.
