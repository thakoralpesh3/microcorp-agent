# Databricks: Deployment Strategist
*Developer Reference & Architecture Kit | Engineering Division, The Agency & MicroCorp AI*

---

## 1. Product Title & Value Proposition

### Databricks Deployment Strategist: Enterprise Infrastructure & MLOps Kit
Deploying workloads to Databricks without a standardized, automated strategy leads to cluster sprawl, runaway cloud costs, security vulnerabilities, and brittle ML pipelines. 

**The Value Proposition:**  
This production-grade architecture kit eliminates infrastructure guesswork. It provides Infrastructure-as-Code (Terraform) templates, secure CI/CD pipelines (GitHub Actions), and battle-tested Unity Catalog governance patterns. Designed for Senior DevOps Engineers, Data Platform Architects, and MLOps Leads, this kit reduces Databricks deployment time from days to minutes while ensuring SOC2 compliance and cost predictability.

---

## 2. Quick Start & Core Concepts

Mastering Databricks deployments requires understanding its foundational components, control-plane/data-plane split, and governance boundaries.

| Concept | Definition | Production Recommendation |
| :--- | :--- | :--- |
| **Workspace (Control Plane)** | The managed environment where users write code, manage notebooks, and configure jobs. | Isolate by environment (`dev`, `staging`, `prod`) using Terraform workspaces. |
| **Data Plane** | The compute resources (EC2/VMs, storage) deployed inside your own cloud tenant (VNet/VPC). | Deploy inside a Customer-Managed VPC with private subnets and no public IP addresses. |
| **Unity Catalog** | The fine-grained governance solution for data and AI assets across workspaces. | Use a 3-level namespace (`catalog.schema.table`) tied to enterprise IdP groups. |
| **Databricks Asset Bundles (DABs)** | The native CLI-driven framework for packaging, testing, and deploying Databricks projects. | Use DABs for all job orchestration, pipeline deployments, and model serving endpoints. |
| **Serverless Compute** | Instant-on, auto-scaling compute managed entirely by Databricks. | Default to serverless SQL warehouses and serverless job compute for operational efficiency. |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Terraform Modular Infrastructure Setup
Provision a secure Databricks workspace with customer-managed keys (CMK) and private link configuration.

```hcl
# main.tf - Enterprise Databricks Workspace Module
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">= 1.35.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0"
    }
  }
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
}

resource "databricks_mws_workspaces" "this" {
  provider       = databricks.mws
  account_id     = var.databricks_account_id
  aws_region     = var.aws_region
  workspace_name = "microcorp-${var.environment}-ws"

  storage_configuration_id = databricks_mws_storage_configurations.this.storage_config_id
  credentials_id           = databricks_mws_credentials.this.credentials_id
  network_config_id        = databricks_mws_networks.this.network_id

  token {
    comment = "Terraform Provisioned"
  }
}

output "workspace_url" {
  value = databricks_mws_workspaces.this.workspace_url
}
```

---

### Pattern 2: Databricks Asset Bundle (DAB) Configuration (`databricks.yml`)
Define automated multi-task workflows, Delta Live Tables (DLT), and model training jobs as code.

```yaml
# databricks.yml
bundle:
  name: microcorp-mlops-pipeline

include:
  - resources/*.yml

variables:
  warehouse_id:
    description: "SQL Warehouse ID for reporting tasks"
    default: "a1b2c3d4e5f67890"

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://adb-1234567890123456.16.azuredatabricks.net

  prod:
    mode: production
    workspace:
      host: https://adb-9876543210987654.16.azuredatabricks.net
      root_path: /Shared/bundles/${bundle.name}/${bundle.target}
    permissions:
      - level: CAN_MANAGE
        group_name: "platform-engineers"
```

---

### Pattern 3: Automated CI/CD Pipeline (GitHub Actions)
Validate, test, and deploy Databricks Asset Bundles on every pull request merge to `main`.

```yaml
# .github/workflows/deploy.yml
name: "Databricks DABs CI/CD"

on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: "Deploy Bundle to Production"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Databricks CLI
        run: |
          curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli-cli/main/install.sh | sh
          export PATH="$HOME/.databricks/bin:$PATH"
          databricks --version

      - name: Authenticate and Deploy
        env:
          DATABRICKS_HOST: ${{ secrets.PROD_DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.PROD_DATABRICKS_TOKEN }}
        run: |
          export PATH="$HOME/.databricks/bin:$PATH"
          databricks bundle validate -t prod
          databricks bundle deploy -t prod
          databricks bundle run full_pipeline -t prod
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   ❌ **Hardcoding Secrets in Notebooks:** Embedding API keys or database credentials directly into python notebooks exposes them across workspace users.
    *   *Fix:* Always utilize Databricks Secrets Scopes backed by Azure Key Vault, AWS Secrets Manager, or HashiCorp Vault.
*   ❌ **Over-Provisioning All-Purpose Clusters:** Using interactive clusters for scheduled batch ETL jobs incurs massive financial overhead.
    *   *Fix:* Utilize **Job Compute** (automated, single-run clusters) for production pipelines. They spin up, execute, and terminate automatically, saving up to 50% in compute costs.
*   ❌ **Bypassing Unity Catalog for Flat Object Storage:** Granting direct S3/ADLS bucket access without Unity Catalog results in un-auditable data lakes.
    *   *Fix:* Enforce Unity Catalog external locations and managed storage tables exclusively.
*   ❌ **Ignoring Node Type and Instance Family Limits:** Using general-purpose instances for memory-bound machine learning training or distributed shuffle operations.
    *   *Fix:* Map workload profiles precisely (e.g., `i3en` instances for high IO/local NVMe shuffle; `g5` or `p4d` instances for deep learning GPU tasks).

---

## 5. Performance & Optimization Tips

1.  **Enable Predictive Optimization:** Turn on Databricks Predictive Optimization for Unity Catalog tables. Databricks will automatically run `OPTIMIZE` (compaction) and `VACUUM` commands in the background without locking tables.
2.  **Optimize Delta Lake File Sizes:** Avoid the "small file problem" by tuning write batch sizes. Target optimal parquet file sizes between 1GB to 4GB for large analytical datasets.
3.  **Leverage Photon Acceleration:** Enable the Databricks Photon vectorised query engine on SQL warehouses and standard jobs to accelerate SQL execution and dataframe operations by 2–4x with zero code changes.
4.  **Partition Wisely:** Only partition Delta tables on columns with high cardinality filtering patterns (e.g., `date` or `region`) where queries routinely prune data. Over-partitioning degrades metadata performance.

---

## 6. Commercial License & Attribution Summary

```text
====================================================================
MICROCORP AI COMMERCIAL DIGITAL PRODUCT LICENSE
Product: Databricks: Deployment Strategist (Architecture Kit)
Author: The Engineering Division @ The Agency / MicroCorp AI
====================================================================

1. GRANT OF LICENSE
MicroCorp AI grants the purchasing entity / individual engineer a 
perpetual, non-exclusive, non-transferable license to use, modify, 
and adapt the code patterns, Terraform configurations, and CI/CD 
pipelines contained within this product for internal commercial use 
and client deliverables.

2. RESTRICTIONS
You may NOT resell, sub-license, redistribute, or publicly post 
the raw source files, markdown kits, or architectural templates of 
this product on public code repositories, digital marketplaces 
(e.g., Gumroad, GitHub Marketplace), or training datasets without 
express written consent from MicroCorp AI.

3. DISCLAIMER OF WARRANTY
THIS SOFTWARE AND ARCHITECTURE KIT IS PROVIDED "AS IS", WITHOUT 
WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. MICROCORP AI SHALL NOT BE 
LIABLE FOR ANY CLOUD INFRASTRUCTURE COSTS, DATA LOSS, OR SYSTEM 
DOWNTIME RESULTING FROM THE IMPLEMENTATION OF THESE PATTERNS.
====================================================================
```