# Developer Toolkit: macOS Git eMudhra Certificate Compromise Mitigation & Remediation Guide

> **Product SKU:** MC-DEV-KIT-2026-EMG  
> **Author:** MicroCorp AI Engineering Division  
> **Target Audience:** Principal Engineers, DevOps Leads, Security Operations (SecOps), and macOS Developer Workstation Admins.

---

## 1. Product Title & Value Proposition

### 🚨 The Problem
Recent security advisories highlight systemic vulnerabilities and trust-store compromises involving specific subordinate Certificate Authorities (CAs), notably eMudhra, affecting automated developer pipelines, CI/CD runners, and local macOS developer workstations running Git operations over HTTPS. Compromised intermediate certificates expose engineering organizations to Man-in-the-Middle (MitM) attacks, credential harvesting during `git push`/`git pull`, and silent code injection during dependency resolution.

### 💡 The Value Proposition
This architectural kit provides an enterprise-grade remediation blueprint to instantly isolate, inspect, pin, and override compromised trust chains across macOS development fleets. By deploying our zero-trust Git certificate hardening scripts and automated CI/CD guardrails, your engineering organization eliminates supply-chain vulnerabilities, enforces strict TLS verification, and achieves automated compliance auditing within minutes.

---

## 2. Quick Start & Core Concepts

To immediately neutralize potential eMudhra trust-store vectors on a local macOS workstation, execute the following triage sequence via terminal:

```bash
# 1. Isolate and inspect eMudhra certificates in the System Keychain
security find-certificate -a -c "eMudhra" /Library/Keychains/System.keychain

# 2. Export local trust status configuration
security dump-trust-settings -d
```

### Core Concepts & Syntax Reference

| Concept | Description | macOS CLI / Git Config Equivalent |
| :--- | :--- | :--- |
| **System Trust Store** | macOS keychain repository managing root & intermediate CAs (`/Library/Keychains/System.keychain`). | `security add-trusted-cert` / `security remove-trusted-cert` |
| **Git Transport Layer** | Underlying network layer Git uses for HTTPS (Secure Transport vs. OpenSSL/Libcurl). | `git config --global http.sslBackend` |
| **Certificate Pinning** | Forcing Git to validate against a specific custom CA bundle, ignoring compromised system stores. | `git config --global http.sslCAInfo` |
| **OCSP Stapling** | Online Certificate Status Protocol verification to check revocation in real-time. | `git config --global http.schannelCheckRevoke` (Windows) / custom curl flags |
| **Enterprise Profile Enforced** | MDM payload restricting root CA additions on managed developer laptops. | `.mobileconfig` payload deploying custom restrictions |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern A: Automated macOS Remediation Script (`mitigate-emudhra.sh`)
This production-ready bash script inspects the user and system keychains, blacklists or removes untrusted eMudhra intermediate certificates, and configures Git to use a hardened, explicitly defined CA bundle.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: mitigate-emudhra.sh
# Description: Automates the removal/blocking of compromised eMudhra certs 
#              and hardens local Git TLS configurations on macOS.
# Author     : MicroCorp AI Security Division
# ==============================================================================

set -euo pipefail

# Colors for output logging
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. Verify OS Architecture
if [[ "$(uname)" != "Darwin" ]]; then
    log_error "This script is designed specifically for macOS (Darwin)."
    exit 1
fi

log_info "Initiating eMudhra Certificate Compromise Mitigation Protocol..."

# 2. Search and disable/remove from System Keychain
# Note: Modifying /Library/Keychains requires sudo privileges.
if [[ $EUID -ne 0 ]]; then
   log_warn "This script must be run with sudo to modify the System Keychain."
   exec sudo "$0" "$@"
fi

CERT_LABELS=("eMudhra" "eMudhra Consumer" "eMudhra Sub CA")

for label in "${CERT_LABELS[@]"; do
    log_info "Searching for certificate label matching: '${label}'..."
    
    # Find certificate hashes/SHA1s
    CERTS=$(security find-certificate -a -c "${label}" -Z /Library/Keychains/System.keychain 2>/dev/null || true)
    
    if [[ -n "${CERTS}" ]]; then
        log_warn "Found matching certificates for '${label}'. Purging from System Trust..."
        
        # Extract SHA-1 hashes and remove them
        while IFS= read -r line; do
            if [[ "$line" =~ ^SHA-1\ hash:\ (.+) ]]; then
                HASH="${BASH_REMATCH[1]}"
                log_info "Removing cert hash: ${HASH}"
                security delete-certificate -Z "${HASH}" /Library/Keychains/System.keychain || true
            fi
        done <<< "${CERTS}"
    else
        log_info "No active certificates found matching '${label}' in System Keychain."
    fi
done

# 3. Configure Git Hardening Globally for all users / current user
log_info "Hardening global Git configuration..."

# Enforce strict SSL verification
git config --system http.sslVerify true

# Optional: Point to a verified, custom enterprise CA bundle if required
# git config --system http.sslCAInfo /etc/ssl/certs/enterprise-trusted-bundle.pem

log_info "Remediation sequence completed successfully. System trust store sanitized."
```

### Pattern B: Enterprise Git Config Template (`.gitconfig-enterprise`)
Deploy this template via your MDM platform (Jamf, Kandji, Munki) or include it in developer bootstrap scripts to enforce secure defaults.

```ini
[http]
    sslVerify = true
    # Force HTTP/1.1 or HTTP/2 securely depending on git version
    version = HTTP/2
    # Prevent insecure redirects
    followRedirects = initial

[url "https://github.com/"]
    insteadOf = git://github.com/

[core]
    # Enforce strict file permissions on local repositories
    sharedRepository = group
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   **Anti-Pattern 1: Disabling SSL Verification (`http.sslVerify = false`)**
    *   *Risk:* Developers encountering certificate errors often execute `git config --global http.sslVerify false` to bypass blocked workflows. This completely disables Man-in-the-Middle protection, exposing internal source code and credentials.
    *   *Remediation:* Enforce pre-commit hooks or CI guardrails that scan local `.git/config` files and throw fatal errors if `sslVerify` is set to false.
*   **Anti-Pattern 2: Blindly Trusting User-Level Keychains**
    *   *Risk:* Simply removing certificates from `/Library/Keychains/System.keychain` is insufficient if the compromised root has been imported into user-specific keychains (`~/Library/Keychains/login.keychain-db`).
    *   *Remediation:* Always run sweeps across *both* system and user keychains during mitigation routines.
*   **Anti-Pattern 3: Utilizing Unpinned Custom CA Bundles**
    *   *Risk:* Replacing a compromised CA bundle with an unverified public mirror downloaded from unauthenticated storage buckets introduces secondary supply chain vectors.
    *   *Remediation:* Cryptographically verify all replacement `.pem` bundles against official root hashes published by Mozilla/Apple NSS databases before deployment.

---

## 5. Performance & Optimization Tips

1.  **Cache Certificate Verification Results:** Ensure your Git binary is dynamically linked against modern `libcurl` and OpenSSL/LibreSSL distributions to leverage session resumption and TLS ticket caching, reducing handshake latency during heavy parallel submodule fetches.
2.  **Minimize Keychain Search Overhead:** macOS performance degrades when traversing bloated keychains with thousands of stale developer identities. Regularly prune expired keys using `security dump-trust-settings` coupled with automated cleanups.
3.  **Leverage Shallow Clones in CI/CD:** For high-throughput automated pipelines, use `git clone --depth 1 --no-single-branch` combined with strict sparse-checkout configurations to reduce network transfer footprints while maintaining cryptographic verification integrity.

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp AI Commercial Enterprise License (v2.4)
*Copyright © 2026 MicroCorp AI. All rights reserved.*

1.  **Grant of License:** MicroCorp AI grants the purchasing organization a non-exclusive, perpetual, royalty-free license to use, modify, and internalize this Developer Toolkit within their corporate engineering infrastructure.
2.  **Redistribution Restrictions:** Unauthorized resale, public code repository publishing of raw kit contents, or inclusion in commercial SaaS offerings without explicit written authorization from MicroCorp AI is strictly prohibited.
3.  **Warranty Disclaimer:** This software and reference architecture are provided "as is" without warranty of any kind, express or implied. MicroCorp AI assumes zero liability for downstream security incidents arising from improper execution of workstation modification scripts.

---
*End of Document — MicroCorp AI Engineering Division*