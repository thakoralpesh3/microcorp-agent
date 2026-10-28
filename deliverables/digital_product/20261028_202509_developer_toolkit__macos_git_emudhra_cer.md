# Developer Toolkit: macOS Git eMudhra Certificate Remediation Guide & Boilerplates

> **Product SKU:** MC-ENG-DEV-EMUDHRA-042  
> **Author:** Engineering Division, MicroCorp AI  
> **Target Audience:** DevOps Engineers, Enterprise macOS Fleet Managers, Full-Stack Developers  
> **Format:** Enterprise Reference & Automation Kit (GitHub Flavored Markdown)

---

## 1. # Product Title & Value Proposition

### The Enterprise Challenge
When deploying development environments on macOS within regulated banking, government, or enterprise sectors, engineers frequently encounter cryptographic trust failures. Specifically, **eMudhra** (a licensed Certifying Authority widely used for corporate identity, document signing, and mutual TLS) injects enterprise root and intermediate certificates into the macOS Keychain. 

However, command-line utilities—most notably **Git** bundled with Apple Command Line Tools or Homebrew—rely on independent OpenSSL, LibreSSL, or Secure Transport bindings. This leads to the infamous, workflow-halting error:
```bash
fatal: unable to access 'https://github.enterprise.com/': SSL certificate problem: self signed certificate in certificate chain
```
Disabling SSL verification (`git config --global http.sslVerify false`) is a severe security violation that triggers automated SOC alerts. 

### The Solution: MicroCorp eMudhra Remediation Kit
This commercial developer kit provides an automated, enterprise-grade architecture for bridging macOS Keychain certificates directly into Git's trust store. It includes zero-dependency shell automation, programmatic CI/CD pipeline hooks, and audit-compliant verification scripts designed for fleet deployment via MDM (Jamf, Kandji) or local bootstrap scripts.

```
+-------------------------------------------------------------------+
                  MACOS SYSTEM KEYCHAIN (eMudhra)
                                  │
                                  ▼ (Automated Extraction)
                     [ PEM Certificate Bundle ]
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[ Git System Trust Store ]                     [ OpenSSL Store Export ]
`git config http.sslCAInfo`                    `SSL_CERT_FILE` env var
```

---

## 2. ## Quick Start & Core Concepts (with clean syntax table)

Execute the following one-liner in your terminal to diagnose your current Git SSL configuration posture:
```bash
git config --system --get http.sslCAInfo || echo "No system CA bundle configured."
```

### Core Concepts & Configuration Syntax Reference

| Concept | Description | Syntax / Command | Enterprise Impact |
| :--- | :--- | :--- | :--- |
| **System Keychain Extraction** | Pulls enterprise CA certs from macOS Keychain into standard PEM format. | `security find-certificate -a -p /Library/Keychains/System.keychain > bundle.pem` | Establishes single source of cryptographic truth. |
| **Git Global CA Override** | Directs the Git binary to utilize the custom enterprise CA bundle. | `git config --global http.sslCAInfo /etc/git/certs/emudhra-ca-bundle.pem` | Fixes HTTPS transport layer for all user repositories. |
| **Secure Transport Toggle** | Forces Git to leverage native macOS Secure Transport instead of OpenSSL. | `git config --global http.sslBackend sectransp` | Bypasses custom PEM paths by trusting macOS Keychain natively. |
| **Environment Variable Injection** | Forces child processes and scripts to inherit the eMudhra trust store. | `export GIT_SSL_CAINFO="/etc/git/certs/emudhra-ca-bundle.pem"` | Essential for non-interactive shell scripts and build agents. |
| **Node.js / npm Trust Bridge** | Aligns Node-based tooling (often bundled in developer laptops) with eMudhra. | `npm config set cafile /etc/git/certs/emudhra-ca-bundle.pem` | Prevents `SELF_SIGNED_CERT_IN_CHAIN` errors during `npm install`. |

---

## 3. ## Production Code Patterns & Architecture Examples

### Pattern A: Automated Zero-Touch Remediation Script (`emudhra-git-fix.sh`)
Deploy this script via your MDM platform (Jamf/Kandji) or run it during developer onboarding. It safely extracts eMudhra roots from the macOS System Keychain, validates them, and configures Git globally.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: emudhra-git-fix.sh
# Description: Automates extraction of eMudhra enterprise certificates from 
#              macOS Keychain and configures Git to trust them globally.
# Author:      MicroCorp AI Engineering Division
# License:     Commercial Enterprise License
# ==============================================================================

set -euo pipefail

# Configuration Constants
TARGET_DIR="/etc/git/certs"
BUNDLE_NAME="emudhra-enterprise-chain.pem"
TARGET_PATH="${TARGET_DIR}/${BUNDLE_NAME}"

# Color Output Definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 1. Verify Root Privileges (Writing to /etc requires sudo)
if [[ $EUID -ne 0 ]]; then
   log_err "This script must be run with administrator privileges (sudo)."
fi

log_info "Initializing eMudhra Certificate Remediation for macOS Git..."

# 2. Create Target Directory
mkdir -p "${TARGET_DIR}"
chmod 755 "${TARGET_DIR}"

# 3. Extract Certificates from System Keychain containing 'eMudhra'
log_info "Extracting eMudhra certificates from macOS System Keychain..."
TEMP_PEM=$(mktemp)

# Search both System and Login keychains for issuer/common name matching eMudhra
security find-certificate -a -c "eMudhra" -p /Library/Keychains/System.keychain > "${TEMP_PEM}" 2>/dev/null || true
security find-certificate -a -c "eMudhra" -p /System/Library/Keychains/SystemRoot.keychain >> "${TEMP_PEM}" 2>/dev/null || true

# Check if certificates were actually found
if [[ ! -s "${TEMP_PEM}" ]]; then
    log_warn "No certificates matching 'eMudhra' found via common name search."
    log_warn "Falling back to exporting all system root certificates..."
    security find-certificate -a -p /Library/Keychains/System.keychain > "${TEMP_PEM}"
fi

# 4. Clean and Validate PEM format
# Filter out non-PEM output and ensure clear line breaks
cat "${TEMP_PEM}" | grep -E "(BEGIN CERTIFICATE|END CERTIFICATE|[a-zA-Z0-9+/=]+)" > "${TARGET_PATH}"
rm -f "${TEMP_PEM}"

if [[ ! -s "${TARGET_PATH}" ]]; then
    log_err "Failed to generate valid certificate bundle at ${TARGET_PATH}."
fi

chmod 644 "${TARGET_PATH}"
log_info "Certificate bundle successfully written to ${TARGET_PATH}"

# 5. Configure Global Git Settings
log_info "Configuring global Git settings..."
git config --system http.sslCAInfo "${TARGET_PATH}"
git config --system http.sslBackend openssl

# Verify configuration application
CONFIGURED_PATH=$(git config --system --get http.sslCAInfo)
if [[ "${CONFIGURED_PATH}" == "${TARGET_PATH}" ]]; then
    log_info "Git successfully configured to use eMudhra trust bundle."
else
    log_err "Verification failed: Git system config did not apply correctly."
fi

log_info "Remediation complete. Secure enterprise Git operations are now active."
```

---

### Pattern B: Developer Local Bootstrap Boilerplate (`Makefile`)
Place this `Makefile` in your organization's internal developer bootstrap repositories. It enables engineers to self-heal their environments with a single command (`make setup-git`).

```makefile
# ==============================================================================
# MicroCorp Developer Environment Bootstrap Makefile
# Target OS: macOS (Apple Silicon / Intel)
# ==============================================================================

SHELL := /bin/bash
CERT_DIR := /etc/git/certs
BUNDLE_PATH := $(CERT_DIR)/emudhra-enterprise-chain.pem

.PHONY: help check-deps setup-git verify clean

help:
	@echo "MicroCorp eMudhra Git Remediation Toolkit"
	@echo "--------------------------------------------------------"
	@echo "  make setup-git    - Extract certs and configure Git (Requires sudo)"
	@echo "  make verify       - Test clone against internal Enterprise GitHub"
	@echo "  make clean        - Remove local system-level cert overrides"

check-deps:
	@which security > /dev/null || (echo "Error: macOS 'security' utility missing." && exit 1)
	@which git > /dev/null || (echo "Error: Git is not installed." && exit 1)

setup-git: check-deps
	@echo "==> Requesting administrative permissions to update system trust stores..."
	@sudo mkdir -p $(CERT_DIR)
	@sudo chmod 755 $(CERT_DIR)
	@echo "==> Extracting eMudhra certificates from System Keychain..."
	@sudo security find-certificate -a -c "eMudhra" -p /Library/Keychains/System.keychain > /tmp/emudhra_raw.pem
	@sudo cp /tmp/emudhra_raw.pem $(BUNDLE_PATH)
	@sudo chmod 644 $(BUNDLE_PATH)
	@rm -f /tmp/emudhra_raw.pem
	@echo "==> Configuring Git global system parameters..."
	@sudo git config --system http.sslCAInfo $(BUNDLE_PATH)
	@echo "==> Success! Git is now configured with the eMudhra trust chain."

verify:
	@echo "==> Verifying Git SSL handshake..."
	@git ls-remote https://github.enterprise.com/microcorp/core-infra.git HEAD > /dev/null && \
		echo "SUCCESS: Git successfully authenticated via eMudhra trust chain!" || \
		echo "FAILURE: SSL handshake failed. Run 'make setup-git' with sudo."

clean:
	@echo "==> Removing eMudhra system configurations..."
	@sudo rm -f $(BUNDLE_PATH)
	@sudo git config --system --unset http.sslCAInfo || true
	@echo "==> Clean complete."
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why Engineers Do It | Enterprise Risk / Consequence | Correct Approach |
| :--- | :--- | :--- | :--- |
| **Global SSL Disabling** | `git config --global http.sslVerify false` provides instant gratification when stuck. | Opens the entire machine to Man-in-the-Middle (MitM) attacks on public and corporate networks. | Always register corporate CA bundles via `http.sslCAInfo`. |
| **Hardcoding User Paths** | Pointing `sslCAInfo` to `/Users/username/certs/emudhra.pem`. | Fails immediately when user accounts change, or when scripts run under service/daemon users. | Store centralized bundles in system-wide protected paths like `/etc/git/certs/`. |
| **Ignoring OpenSSL vs Secure Transport Conflicts** | Mixing Homebrew Git (linked to OpenSSL) with Apple Xcode Git (linked to Secure Transport). | Inconsistent behavior where terminal Git fails while GUI clients (VS Code, Fork) succeed. | Explicitly set `git config --global http.sslBackend openssl` alongside the explicit CA bundle path. |
| **Stale Certificate Caching** | Never updating PEM bundles after corporate eMudhra root certificate rotations. | Sudden, widespread CI/CD pipeline and developer workstation failures upon cert expiry. | Automate bundle extraction via MDM or periodic login daemons. |

---

## 5. ## Performance & Optimization Tips

1. **Leverage Native Secure Transport for Zero-Maintenance:**
   If your enterprise infrastructure relies entirely on Apple-native tooling and MDM-deployed enterprise roots, bypass PEM generation altogether by instructing Git to use macOS Secure Transport:
   ```bash
   git config --global http.sslBackend sectransp
   ```
   *Note: This eliminates custom bundle file management because Git queries the macOS System Keychain directly.*

2. **Optimize OpenSSL PEM File Size:**
   Extracting the entire macOS Keychain (`security find-certificate -a -p`) introduces hundreds of megabytes of third-party public CAs (Verisign, DigiCert, Apple) into Git's certificate verification loop, increasing handshake latency. Always filter specifically for your corporate issuer:
   ```bash
   security find-certificate -a -c "eMudhra" -p /Library/Keychains/System.keychain > emudhra-trimmed.pem
   ```

3. **CI/CD Pipeline Optimization:**
   For continuous integration runners (GitHub Actions self-hosted runners on macOS), avoid runtime keychain extractions. Bake the `emudhra-enterprise-chain.pem` directly into your golden AMI/VM disk image and inject it into the runner initialization script:
   ```yaml
   env:
     GIT_SSL_CAINFO: /opt/microcorp/certs/emudhra-enterprise-chain.pem
   ```

---

## 6. ## Commercial License & Attribution Summary

### MicroCorp Commercial Software License (MCSL v1.2)

* **Copyright (c) 2026 MicroCorp AI. All rights reserved.**
* **Grant of License:** MicroCorp AI grants the purchasing organization a perpetual, non-exclusive, worldwide, non-transferable enterprise license to deploy, modify, and distribute the scripts, boilerplates, and architectural patterns contained within this toolkit across all internal developer workstations and CI/CD fleets owned or operated by the licensee.
* **Restrictions:** Redistribution of this exact digital product as a standalone commercial developer toolkit on public marketplaces (e.g., Gumroad, GitHub Marketplace, digital storefronts) without explicit written consent from MicroCorp AI is strictly prohibited.
* **Disclaimer of Warranty:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall MicroCorp AI be liable for any claim, damages, or other liability arising from the execution or misuse of these automation scripts.

---
*End of Document — MicroCorp AI Engineering Division*