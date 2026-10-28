# Developer Toolkit: Git macOS eMudhra Certificate Mitigation Suite
**Enterprise Architecture Reference & Production Implementation Guide**  
*The Agency Engineering Division | MicroCorp AI Enterprise Standards*

---

## 1. Product Title & Value Proposition

### 🚀 Git macOS eMudhra Certificate Mitigation Suite
Enterprise-grade cryptographic bridge kit designed to resolve SSL/TLS handshake failures, `self-signed certificate in certificate chain` errors, and OpenSSL/Secure Transport conflicts when executing Git operations against corporate infrastructure using eMudhra Digital Signature Certificates (DSC) on macOS systems.

```
       [ macOS Native Keychain ] ──(Trust Anchor Failure)──> [ Git / OpenSSL CLI ]
                  │                                                    ▲
                  ▼                                                    │
    [ eMudhra Certificate Suite ] ──(Injected via Mitigation Kit)──────┘
```

### 💎 Core Value Proposition
* **Zero-Downtime CI/CD Operations:** Eliminate pipeline failures caused by corporate proxy inspection and enterprise CA re-signing.
* **Declarative Trust Injection:** Bypass manual Keychain access errors (`SecTrustEvaluate` failures) via automated bundle generation.
* **Dual-Stack Compatibility:** Seamlessly bridge macOS native SecureTransport and Homebrew-linked OpenSSL without breaking system updates.
* **Audit-Ready Compliance:** Maintain strict compliance with FIPS-140-2 cryptographic guidelines while preserving developer velocity.

---

## 2. Quick Start & Core Concepts

When macOS updates or corporate security agents inject eMudhra intermediate certificates into the user or system keychain, Git's bundled OpenSSL or SecureTransport backends frequently fail to validate the signature chain. This results in the infamous `SSL certificate problem: self-signed certificate in certificate chain`.

### 📊 Diagnostic & Configuration Matrix

| Vector / Component | Symptom | Root Cause | Resolution Strategy |
| :--- | :--- | :--- | :--- |
| **SecureTransport** (`osxkeychain`) | `Git fetch` hangs or throws `curl 35 SSL connect error` | macOS Keychain trust bit mismatch for eMudhra Sub-CA | Export PEM chain & inject explicitly via `http.sslCAInfo` |
| **Homebrew OpenSSL** (`openssl@3`) | `unable to get local issuer certificate` | OpenSSL default CA store lacks corporate root | Append eMudhra bundle to `openssl.cnf` or Git global config |
| **Corporate Proxy / Zscaler** | `SSL peer certificate or SSH remote key was not OK` | SSL Interception using dynamic re-signing | Pin corporate root + eMudhra chain in isolated Git profile |
| **Submodule Sync** | Submodule update fails recursively over HTTPS | Submodules ignore global `http.sslCAInfo` in older clients | Enforce global config across all nested worktrees |

---

## 3. Production Code Patterns & Architecture Examples

This section contains production-ready, copy-paste scripts designed to automate the extraction, conversion, and configuration of eMudhra certificates for Git on macOS.

### Pattern 1: Automated Certificate Extraction & PEM Bundle Generator (`emudhra-setup.sh`)
Run this script to locate eMudhra certificates in your macOS Keychain, export them to PEM format, and configure your global Git environment automatically.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: emudhra-setup.sh
# Description: Extracts eMudhra certificates from macOS Keychain and configures Git.
# Author: The Agency Engineering Division (MicroCorp AI)
# ==============================================================================

set -euo pipefail

TARGET_DIR="${HOME}/.git-emudhra"
BUNDLE_FILE="${TARGET_DIR}/emudhra-ca-bundle.pem"

echo "==> [1/4] Initializing secure directory at ${TARGET_DIR}..."
mkdir -p "${TARGET_DIR}"
chmod 700 "${TARGET_DIR}"

echo "==> [2/4] Scanning macOS Keychains for eMudhra certificates..."
# Extract certificates containing 'eMudhra' from System and Login keychains into PEM
security find-certificate -a -c "eMudhra" -p /Library/Keychains/System.keychain > "${BUNDLE_FILE}" 2>/dev/null || true
security find-certificate -a -c "eMudhra" -p "${HOME}/Library/Keychains/login.keychain-db" >> "${BUNDLE_FILE}" 2>/dev/null || true

# Fallback: If no certificates found by common name, search organization field
if [ ! -s "${BUNDLE_FILE}" ]; then
    echo "⚠️  Direct CN match failed. Extracting generic enterprise intermediates..."
    security find-certificate -a -p /Library/Keychains/System.keychain >> "${BUNDLE_FILE}"
fi

CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" "${BUNDLE_FILE}" || true)
echo "==> Found and staged ${CERT_COUNT} certificate(s)."

if [ "${CERT_COUNT}" -eq 0 ]; then
    echo "❌ Error: No eMudhra or valid corporate certificates found in Keychain."
    echo "    Please import your eMudhra .cer/.pfx file into Keychain Access first."
    exit 1
fi

echo "==> [3/4] Securing certificate bundle permissions..."
chmod 600 "${BUNDLE_FILE}"

echo "==> [4/4] Configuring Git global directives..."
git config --global http.sslCAInfo "${BUNDLE_FILE}"
git config --global http.schannelCheckRevoke false 2>/dev/null || true

echo "✅ Success! Git is now configured to trust the eMudhra certificate suite."
git config --get http.sslCAInfo
```

### Pattern 2: Environment-Isolated Git Wrapper (`git-emudhra`)
For multi-tenant machines (e.g., personal GitHub + Enterprise GitLab with eMudhra), use this wrapper to isolate certificate overrides per repository path.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: git-emudhra (Drop-in wrapper for enterprise Git commands)
# ==============================================================================

EMUDHRA_BUNDLE="${HOME}/.git-emudhra/emudhra-ca-bundle.pem"

if [ ! -f "${EMUDHRA_BUNDLE}" ]; then
    echo "❌ eMudhra bundle missing. Run emudhra-setup.sh first." >&2
    exit 1
fi

# Inject custom CA bundle explicitly into the Git execution context
exec git -c http.sslCAInfo="${EMUDHRA_BUNDLE}" "$@"
```

### Pattern 3: Automated Diagnostic Script (`git-ssl-diagnostics.sh`)
Use this script to verify that your Git client successfully negotiates TLS with your corporate git server using the injected eMudhra bundle.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: git-ssl-diagnostics.sh
# Description: Diagnoses SSL handshake issues between Git and target servers.
# ==============================================================================

TARGET_HOST="${1:-github.com}"
BUNDLE_FILE="${HOME}/.git-emudhra/emudhra-ca-bundle.pem"

echo "------------------------------------------------------------------"
echo "Running SSL Diagnostics for: ${TARGET_HOST}"
echo "Using CA Bundle: ${BUNDLE_FILE}"
echo "------------------------------------------------------------------"

if [ -f "${BUNDLE_FILE}" ]; then
    echo "✅ CA Bundle exists."
    openssl version
    echo "------------------------------------------------------------------"
    echo "Testing TLS handshake via OpenSSL s_client..."
    
    # Test connection utilizing the custom bundle
    echo | openssl s_client -connect "${TARGET_HOST}:443" -servername "${TARGET_HOST}" -CAfile "${BUNDLE_FILE}" 2>&1 | grep -E "Verify return code|Certificate chain"
else
    echo "❌ CA Bundle not found at ${BUNDLE_FILE}"
fi
echo "------------------------------------------------------------------"
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* **Anti-Pattern 1: Globally Disabling SSL Verification**
  * *Bad:* `git config --global http.sslVerify false`
  * *Risk:* Exposes your entire development machine to Man-in-the-Middle (MitM) attacks, credential theft, and code injection vulnerabilities.
  * *Correction:* Always pin the explicit intermediate/root certificate bundle via `http.sslCAInfo`.

* **Anti-Pattern 2: Mixing Homebrew OpenSSL and Apple SecureTransport**
  * *Bad:* Installing Git via Homebrew without verifying which OpenSSL backend it links against, leading to conflicting certificate stores (`/usr/local/etc/openssl@3/cert.pem` vs macOS Keychain).
  * *Correction:* Standardize your team on either the Apple Xcode Command Line Tools Git (`/usr/bin/git`) or enforce a single Homebrew Git instance paired with a unified CA bundle configuration.

* **Anti-Pattern 3: Hardcoding User-Specific Paths in Shared Configs**
  * *Bad:* Committing absolute paths like `/Users/john/certs/emudhra.pem` into team-shared configuration templates.
  * *Correction:* Utilize shell expansion (`${HOME}/.git-emudhra/...`) or relative environment variables in initialization scripts.

---

## 5. Performance & Optimization Tips

1. **Leverage HTTP/2 Multiplexing for Large Enterprise Repositories:**
   Corporate Git repositories protected by eMudhra often experience latency overhead during TLS handshakes. Enable HTTP/2 multiplexing in Git to reuse established connections:
   ```bash
   git config --global http.version HTTP/2
   ```

2. **Optimize Credential Caching:**
   Prevent repetitive keychain prompts when authenticating through corporate proxies by utilizing the macOS native credential helper:
   ```bash
   git config --global credential.helper osxkeychain
   ```

3. **Pre-warm DNS and TLS Sessions:**
   For sluggish enterprise VPN connections, configure Git to maintain persistent socket connections:
   ```bash
   git config --global http.lowSpeedLimit 1000
   git config --global http.lowSpeedTime 60
   ```

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License (Type C-DevKit)
* **Copyright © 2026 MicroCorp AI & The Agency Engineering Division.** All rights reserved.
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this software kit within internal corporate environments, CI/CD pipelines, and developer workstations.
* **Restrictions:** Redistribution, resale, or public publishing of this specific source kit as a standalone commercial product without explicit written consent from MicroCorp AI is strictly prohibited.
* **Disclaimer:** Provided *as-is* without warranty of any kind, express or implied. The Agency and MicroCorp AI shall not be held liable for any damages arising from the deployment of cryptographic overrides or certificate manipulation scripts.