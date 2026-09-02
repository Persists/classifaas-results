# ClassiFaaS Benchmark Results

This repository contains benchmark results for [ClassiFaaS](https://github.com/persists/ClassiFaaS-Benchmark), a framework for investigating hardware heterogeneity effects on FaaS performance variability across major serverless platforms.

## Overview

The experiments span four serverless platforms:
- **[AWS Lambda](https://aws.amazon.com/lambda/)**
- **[Azure Functions (Flex Consumption Plan)](https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan)**
- **[Google Cloud Functions (gen 1)](https://cloud.google.com/functions)**
- **[Alibaba Function Compute](https://www.alibabacloud.com/product/function-compute)**

We added five different benchmark workloads to evaluate performance across various computational patterns:

| Benchmark | Description |
|-----------|-------------|
| `matmul` | Matrix multiplication (compute-bound) |
| `sha256` | SHA-256 hashing (benefits from SHA-NI) |
| `aesCtr` | AES-CTR encryption (benefits from AES-NI/VAES) |
| `gzip` | Gzip compression (memory/compute mixed) |
| `json` | JSON parsing (general-purpose) |

## Experimental Stages


**Log file naming:** `{platform}-{benchmark}-{memory}.log`  
Example: `aws-matmul-128.log`

**Billed Information:** Each  stage also includes billing data.

### Stage A: Regional Baseline Survey

Broad survey across all platforms and regions to establish CPU heterogeneity baselines.

**Configuration:** 512 MB memory, Matrix Multiplication
**Regions:** This [file](data/stage_a/README.md) includes additional information about the regions we examined for each platform.
**Goal:** Investigating how CPU assignment diversity varies by region

```
data/stage_a/
├── {timestamp}/
│   ├── alibaba/{region}/
│   ├── aws/{region}/
│   ├── azure/{region}/
│   └── gcp/{region}/
```



### Stage B: In-Depth Regional Analysis

Focused analysis of high-diversity regions with multiple memory configurations.
We ran the experiments 12 times in 2 hour intervals to broaden the sampling of CPU assignments.

**Configuration:** 128, 512, 2048 MB memory; Matrix Multiplication
**Regions:** US East (AWS, GCF, Alibaba) and Germany West Central (Azure)  
**Goal:** Examine interaction between memory allocation and CPU assignment, and how the relative performance differences between CPU types changes across memory tiers.

```
data/stage_b/
├── {timestamp}/
│   ├── alibaba/{region}/
│   ├── aws/{region}/
│   ├── azure/{region}/
│   └── gcp/{region}/
```


### Stage C: Longitudinal Monitoring

7-day temporal study monitoring CPU assignment stability and performance trends.

**Configuration:** 512 MB memory, experiments run every 6 hours  
**Regions:** US East (AWS, GCF, Alibaba) and Germany West Central (Azure)  
**Goal:** Assess temporal stability of the hardware lottery effect

```
data/stage_c/
├── {timestamp}/
│   ├── alibaba/us-east-1/
│   ├── aws/us-east-1/
│   ├── azure/germanywestcentral/
│   └── gcp/us-east1/
```
## Analysis Notebooks

| Notebook | Description |
|----------|-------------|
| `stage_a.ipynb` | Regional baseline analysis and CPU diversity assessment |
| `stage_b.ipynb` | Memory-tier analysis and variance decomposition |
| `stage_c.ipynb` | Temporal dynamics and CPU assignment stability |

## Generated Plots

```
plots/
├── stage_a/           # Regional CPU distributions, ECDF comparisons
├── stage_b/           # Memory-tier effects, CV heatmaps, deviation analysis
└── stage_c/           # Temporal trends, CPU composition over time, η² analysis
```

## Helper Modules

The `helpers/` directory contains platform-specific data loaders and analysis utilities:

- `benchmark.py` — Common benchmark metrics and filtering
- `cpus.py` — CPU identification and color palettes
- `aws.py`, `azure.py`, `gcp.py`, `alibaba.py` — platform-specific parsing
- `cost.py` — Cost calculations, currently unused

## Setup

Requires Python 3.12.

```bash
# Install dependencies with pipenv
pipenv install

# Or with pip
pip install pandas matplotlib seaborn jupyter ipykernel pyarrow pingouin scikit-posthocs colorcet
```
