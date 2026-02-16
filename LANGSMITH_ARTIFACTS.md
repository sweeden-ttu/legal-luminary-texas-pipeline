# LangSmith Artifacts - Texas Data Pipeline

## API Configuration

```bash
export LANGSMITH_API_KEY="lsv2_pt_fbffed7e0861"
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_PROJECT="Texas Data Pipeline - Experiment 5"
```

## Datasets to Create

### 1. Texas Government Data - Experiment 5
Description: Texas government datasets from data.texas.gov, TDCJ, Comptroller for ground truth validation

**Examples (5):**
| Input | Output |
|-------|--------|
| Texas Department of Criminal Justice inmate releases FY2025 | dataset_id: q4fw-9sy9, category: LAW_VERIFICATION |
| TDI insurance complaints | dataset_id: jjc8-mxkg, category: ATTORNEY_RESOURCE |
| Texas court cases | source: search.txcourts.gov, category: LAW_VERIFICATION |
| Comptroller tax forms sales | source: comptroller.texas.gov, category: ATTORNEY_RESOURCE |
| TDCJ directory contacts | source: tdcj.texas.gov, category: LAW_VERIFICATION |

### 2. TDCJ Contact Directory
Description: TDCJ contact directory with phone numbers and emails

**Examples (5):**
| Input | Output |
|-------|--------|
| Executive Director | phone: (936)437-2107 |
| Human Resources | phone: (936)437-4141 |
| Correctional Institutions Division | phone: (936)437-2173 |
| Parole Division | phone: 512-406-5401 |
| Health Services Division | phone: (936)437-5570 |

### 3. Texas Comptroller Tax Forms
Description: Texas Comptroller tax forms and publications

**Examples (3):**
| Input | Output |
|-------|--------|
| AP-201 | Texas Application for Sales and Use Tax Permit |
| 01-114 | Texas Sales and Use Tax Return |
| FR-10 | Franchise Tax Forms |

## Traces / Projects

### Project Name: Texas Data Pipeline - Ground Truth Discovery

**Metrics:**
- Total datasets: 263
- Legal datasets: 147
- API reachability: 95.7%
- TDCJ contacts: 59
- Tax forms: 186

**Classification:**
- LAW_VERIFICATION: 116
- NEWS: 8
- ATTORNEY_RESOURCE: 23

**Data Sources:**
- data.texas.gov (Socrata)
- comptroller.texas.gov
- tdcj.texas.gov
- capitol.texas.gov
- txcourts.gov

## How to Import

1. Go to https://smith.langchain.com
2. Login with your account
3. Create datasets manually using the examples above
4. Run your agents with LangSmith tracing enabled

## Python Code for Tracing

```python
from langsmith import traceable

@traceable(name="texas-data-pipeline")
def run_pipeline():
    # Your pipeline code here
    pass
```

View traces at: https://smith.langchain.com
