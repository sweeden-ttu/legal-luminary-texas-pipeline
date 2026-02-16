"""
Configuration and environment settings for the Legal Luminary pipeline.

All API keys and tracing config are loaded from environment variables.
"""

import os


# ============================================================================
# LangSmith Tracing (enabled project-wide)
# ============================================================================

os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "Software Validation and Verification")
os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")


# ============================================================================
# API Keys (set via environment variables before running)
# ============================================================================

# Keys are read from environment variables.
# On macOS, set these in ~/.zprofile so they're available to all shells:
#   export OPENAI_API_KEY="sk-..."
#   export LANGSMITH_API_KEY="lsv2_pt_..."
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY", "") or os.environ.get(
    "LANGCHAIN_API_KEY", ""
)

# CourtListener (free API for court documents)
COURTLISTENER_API_KEY = os.environ.get("COURTLISTENER_API_KEY", "")
COURTLISTENER_BASE_URL = "https://www.courtlistener.com/api/rest/v4"

# NewsGuard (media trust ratings)
NEWSGUARD_API_KEY = os.environ.get("NEWSGUARD_API_KEY", "")

# Congress.gov API (free, for federal officials and legislation)
CONGRESS_GOV_API_KEY = os.environ.get("CONGRESS_GOV_API_KEY", "")
CONGRESS_GOV_BASE_URL = "https://api.congress.gov/v3"

# Federal Election Commission (free API)
FEC_API_KEY = os.environ.get("FEC_API_KEY", "")
FEC_BASE_URL = "https://api.open.fec.gov/v1"

# PACER (court electronic filing — requires paid account)
PACER_USERNAME = os.environ.get("PACER_USERNAME", "")
PACER_PASSWORD = os.environ.get("PACER_PASSWORD", "")

# Doctor (Free Law Project document conversion microservice)
# docker run -p 5050:5050 freelawproject/doctor:latest
DOCTOR_BASE_URL = os.environ.get("DOCTOR_BASE_URL", "http://localhost:5050")


# ============================================================================
# Trusted Domain Lists
# ============================================================================

TRUSTED_NEWS_DOMAINS = {
    # Government sources
    "supremecourt.gov",
    "uscourts.gov",
    "congress.gov",
    "whitehouse.gov",
    "justice.gov",
    "ftc.gov",
    "sec.gov",
    "fec.gov",
    # Major legal news
    "law.cornell.edu",
    "scotusblog.com",
    "courtlistener.com",
    "pacer.gov",
    "govinfo.gov",
    # Texas legal resources
    "texaslawhelp.org",
    "texascourthelp.gov",
    "texasbar.com",
    # Texas law blogs
    "edtexweblog.com",
    # Verified news
    "reuters.com",
    "apnews.com",
    "npr.org",
    # Major law firms
    "allenoverry.com",
    "cliffordchance.com",
    "freshfields.com",
    "linklaters.com",
    "slaughterandmay.com",
}

TRUSTED_COURT_DOMAINS = {
    "uscourts.gov",
    "supremecourt.gov",
    "courtlistener.com",
    "pacer.gov",
    "law.cornell.edu",
    "govinfo.gov",
    # Texas courts
    "texascourthelp.gov",
    "txcourts.gov",
    "txcourts.net",
}

TRUSTED_LEGISLATION_DOMAINS = {
    "congress.gov",
    "govinfo.gov",
    "law.cornell.edu",
    "legiscan.com",
    "ncsl.org",
    # Texas legal resources
    "texaslawhelp.org",
    "texasbar.com",
    # Major law firms
    "allenoverry.com",
    "cliffordchance.com",
    "freshfields.com",
    "linklaters.com",
    "slaughterandmay.com",
}


# ============================================================================
# Texas Open Data (Socrata SODA API)
# ============================================================================

TEXAS_DATA_BASE_URL = "https://data.texas.gov"
TEXAS_SODA_BASE = "https://data.texas.gov/resource"
SOCRATA_APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", "")
# Texas Notary Public Commissions (Secretary of State)
# https://data.texas.gov/dataset/Texas-Notary-Public-Commissions/gmd3-bnrd
TEXAS_NOTARY_DATASET_ID = "gmd3-bnrd"
# TDLR All Licenses (for Central Texas professional lookup)
# https://data.texas.gov/dataset/TDLR-All-Licenses/7358-krk7
TDLR_DATASET_ID = "7358-krk7"

# Texas Comptroller Tax Forms
COMPTROLLER_BASE_URL = "https://comptroller.texas.gov"
COMPTROLLER_TAX_FORMS_URL = "https://comptroller.texas.gov/taxforms/"


# Texas Data Pipeline Configuration (Experiment 5)
TEXAS_DATA_PIPELINE = {
    "sources": [
        {
            "name": "data.texas.gov",
            "type": "socrata",
            "api": "https://data.texas.gov/api/views.json",
        },
        {"name": "capitol.texas.gov", "type": "scrape", "api": None},
        {"name": "statutes.capitol.texas.gov", "type": "scrape", "api": None},
        {"name": "www.texasattorneygeneral.gov", "type": "scrape", "api": None},
        {
            "name": "txcourts.gov",
            "type": "api",
            "api": "https://search.txcourts.gov/api",
        },
        {"name": "lrl.texas.gov", "type": "scrape", "api": None},
        {"name": "sll.texas.gov", "type": "scrape", "api": None},
        {
            "name": "comptroller.texas.gov",
            "type": "scrape",
            "api": "https://comptroller.texas.gov/taxforms/",
        },
    ],
    "legal_keywords": [
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
        "tax",
    ],
    "categories": ["LAW_VERIFICATION", "NEWS", "ATTORNEY_RESOURCE"],
    "min_quality_score": 50,
    "max_results_per_source": 100,
}

# Document Doctor Configuration (PDF processing)
DOCUMENT_DOCTOR_URL = os.environ.get("DOCTOR_BASE_URL", "http://localhost:5050")

TRUSTED_NEWS_DOMAINS.update(
    {
        # Texas state agencies — all verified HTTPS 200 on 2026-02-15
        "data.texas.gov",  # Texas Open Data Portal
        "capitol.texas.gov",  # Texas Capitol / Legislature
        "statutes.capitol.texas.gov",  # Texas Statutes
        "txcourts.gov",  # Texas Judicial Branch
        "www.texasattorneygeneral.gov",  # TX Attorney General
        "sll.texas.gov",  # State Law Library
        "www.legis.texas.gov",  # Texas Legislature Online / TLO
        "lrl.texas.gov",  # TX Legislative Reference Library
        "efiletexas.gov",  # Texas eFiling portal
        "gov.texas.gov",  # Texas Governor
        "comptroller.texas.gov",  # TX Comptroller
        "www.sos.state.tx.us",  # TX Secretary of State (TX Register, TX Admin Code)
        "www.lbb.texas.gov",  # TX Legislative Budget Board
        "www.sunset.texas.gov",  # TX Sunset Advisory Commission
        "tidc.texas.gov",  # TX Indigent Defense Commission
        "scjc.texas.gov",  # State Commission on Judicial Conduct
        "ble.texas.gov",  # TX Board of Law Examiners
        "spa.texas.gov",  # State Prosecuting Attorney
        "texaschildrenscommission.gov",  # TX Children's Commission
        "texasjcmh.gov",  # TX Judicial Commission on Mental Health
        # Bell County local government — verified HTTPS 200
        "www.bellcountytx.com",  # Bell County official site
        "www.killeentexas.gov",  # City of Killeen
        "www.templetx.gov",  # City of Temple
        "www.beltontexas.gov",  # City of Belton
        # Local news — verified HTTPS 200
        "kdhnews.com",  # Killeen Daily Herald
        "www.kwtx.com",  # KWTX News (Waco/Temple/Killeen)
        "www.tdtnews.com",  # Temple Daily Telegram
        "www.statesman.com",  # Austin American-Statesman
    }
)

TRUSTED_COURT_DOMAINS.update(
    {
        # Texas judicial domains — all verified HTTPS 200 on 2026-02-15
        "search.txcourts.gov",  # TX Court case search
        "card.txcourts.gov",  # TX Court Activity Database
        "bail.txcourts.gov",  # TX Public Safety Report System
        "efiletexas.gov",  # Texas eFiling portal
        "ocfw.texas.gov",  # Office of Capital and Forensic Writs
        "www.txwd.uscourts.gov",  # US District Court Western District of TX
    }
)

TRUSTED_LEGISLATION_DOMAINS.update(
    {
        # Texas legislation — all verified HTTPS 200 on 2026-02-15
        "capitol.texas.gov",  # Texas Capitol / Legislature
        "statutes.capitol.texas.gov",  # Texas Statutes
        "sll.texas.gov",  # State Law Library
        "www.legis.texas.gov",  # Texas Legislature Online / TLO
        "lrl.texas.gov",  # TX Legislative Reference Library
        "lrlcatalog.lrl.texas.gov",  # TX LRL Library Catalog
        "www.lbb.texas.gov",  # TX Legislative Budget Board
        "www.sunset.texas.gov",  # TX Sunset Advisory Commission
        "www.sos.state.tx.us",  # TX Secretary of State (TX Register)
    }
)


# ============================================================================
# legalluminary.com Site Verification (submodule: legal-luminary-site)
# ============================================================================

# Path to the legal-luminary-site submodule relative to project root
LEGAL_LUMINARY_SITE_SUBMODULE = "legal-luminary-site"

# Content directories within the submodule to verify
SITE_CONTENT_DIRS = ["_pages", "_posts"]

# Pages with legal claims that need statute/source verification
SITE_PAGES_WITH_SOURCES = {
    "_pages/texas-law.md": {
        "source_urls": [
            "https://statutes.capitol.texas.gov/Docs/CR/htm/CR.55A.htm",
            "https://statutes.capitol.texas.gov/Docs/CR/htm/CR.32.htm",
        ],
        "claims": ["Chapter 55A governs expunctions", "felony 5-99 years or life"],
    },
    "_pages/defense.md": {
        "source_urls": [
            "https://statutes.capitol.texas.gov/Docs/PE/htm/PE.22.htm",
        ],
        "claims": ["Penal Code Chapter 22 defines assault offenses"],
    },
    "_pages/legal-news.md": {
        "source_urls": [
            "https://www.bellcountytx.com/",
            "https://capitol.texas.gov/",
            "https://www.texasattorneygeneral.gov/",
        ],
        "claims": ["aggregates legal news from official sources"],
    },
    "_pages/bell-county.md": {
        "source_urls": ["https://www.bellcountytx.com/"],
        "claims": [
            "Four District Courts (27th, 146th, 169th, and 426th)",
            "Three County Courts at Law",
        ],
    },
    "_pages/resources.md": {
        "source_urls": [
            "https://www.bellcountytx.com/",
            "https://sll.texas.gov",
            "https://statutes.capitol.texas.gov",
        ],
        "claims": ["District Clerk (254) 933-5197", "County Clerk (254) 933-5160"],
    },
}

# LRL (Texas Legislative Reference Library) — key resource for the pipeline
LRL_CONFIG = {
    "base_url": "https://lrl.texas.gov/",
    "bill_search": "https://lrl.texas.gov/legis/billsearch/lrlhome.cfm",
    "member_search": "https://lrl.texas.gov/legeLeaders/members/membersearch.cfm",
    "committee_calendar": "https://lrl.texas.gov/committees/cmteCalendars/cmteMeetings.cfm",
    "session_dates": "https://lrl.texas.gov/sessions/sessionYears.cfm",
    "catalog": "https://lrlcatalog.lrl.texas.gov",
    "current_session": "89th Legislature",
    "latest_news_categories": [
        "New & Noteworthy Books and Reports",
        "Current Articles & Research Resources",
        "Interim Hearings",
    ],
}


# ============================================================================
# Validation Thresholds
# ============================================================================

# Minimum confidence for a source to be considered verified
MIN_CONFIDENCE_THRESHOLD = 0.7

# Maximum retries for a validator node before escalating
MAX_VALIDATOR_RETRIES = 3

# Hallucination rate threshold for pipeline acceptance
HALLUCINATION_RATE_THRESHOLD = 0.05  # 5%
