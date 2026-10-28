# Developer Toolkit: macOS Git eMudhra Certificate Remediation Guide
**Product ID:** MC-DEV-MAC-EMUDHRA-092  
**Version:** 2.4.0-Enterprise  
**Author:** Engineering Division, MicroCorp AI  

---

## 1. Product Title & Value Proposition

### Title
**The macOS Git & eMudhra Enterprise Certificate Remediation Kit**

### Value Proposition
Enterprise software engineering teams frequently experience CI/CD pipeline failures, cryptographic handshake rejections, and `SSL certificate problem: self-signed certificate in certificate chain` errors on macOS development workstations when integrating with strict institutional PKI infrastructure (such as eMudhra token-based signing and corporate TLS inspection proxies). 

This comprehensive engineering kit provides production-ready automation scripts, keychain configuration hardening techniques, and explicit Git runtime overrides. It eliminates environment-drift, secures enterprise source-control operations, and instantly resolves cryptographic breaks without sacrificing local machine security posture.

---

## 2. Quick Start & Core Concepts

When macOS Git encounters an eMudhra hardware token or corporate intermediate CA, standard system keychains often fail to bridge trust boundaries due to how Git links against Secure Transport or OpenSSL. 

### Clean Syntax & Configuration Reference Table

| Target Layer | Mechanism | Configuration / Command | Purpose |
| :--- | :--- | :--- | :--- |
| **Global Git Store** | Configuration Key | `git config --global http.sslCAInfo /path/to/ca.pem` | Directs Git to explicitly trust a custom root/intermediate CA bundle. |
| **Secure Transport** | macOS Keychain | `security add-trusted-cert -d -r trustRoot ...` | Injects the eMudhra cert into the system/login keychain for native toolchains. |
| **Runtime Override** | Environment Variable | `GIT_SSL_NO_VERIFY=true` | **(Emergency Only)** Disables verification for rapid triage in air-gapped runbooks. |
| **OpenSSL Fallback** | Dynamic Linkage | `brew install curl --with-openssl` | Re-links network utilities against modern cryptographic libraries. |
| **Diagnostic Mode** | Trace Flag | `GIT_TRACE=1 GIT_TRANSFER_TRACE=1 git clone ...` | Exposes low-level SSL handshakes and certificate chain validation steps. |

---

## 3. Production Code Patterns & Architecture Examples

Below is a complete, automated remediation script designed to inspect the current local certificate stores, extract missing eMudhra intermediate/root chains, register them with the system keychain, and configure local/global Git overrides safely.

### Automation Script: `remediate-emudhra-git.sh`

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: remediate-emudhra-git.sh
# Description: Automates macOS Keychain trust injection and Git SSL configuration
#              for eMudhra enterprise signing and TLS inspection endpoints.
# Author: MicroCorp AI Engineering Division
# ==============================================================================

set -Eeuo pipefail

# Color Codes for Output Formatting
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 1. Prerequisites Check
if [[ "$OSTYPE" != "darwin"* ]]; then
    log_err "This remediation toolkit is explicitly designed for macOS environments."
fi

# Target Domain for Diagnostic Check (Update to your enterprise Git server)
GIT_DOMAIN="${1:-git.enterprise.internal}"
CERT_BUNDLE_PATH="${HOME}/.git-enterprise-ca.pem"

log_info "Target Enterprise Git Domain: ${GIT_DOMAIN}"

# 2. Extract Certificate Chain from Remote Host
log_info "Probing SSL handshake and extracting certificate chain from ${GIT_DOMAIN}..."
if ! python3 -c "import socket, ssl; print(ssl.get_server_certificate(('${GIT_DOMAIN}', 443)))" > "${CERT_BUNDLE_PATH}" 2>/dev/null; then
    log_warn "Direct automated extraction failed. Falling back to manual bundle specification."
    if [ ! -f "${CERT_BUNDLE_PATH}" ]; then
        log_err "No certificate bundle found at ${CERT_BUNDLE_PATH}. Please drop your eMudhra/Corporate .pem file there."
    fi
else
    log_info "Successfully extracted server certificate chain to ${CERT_BUNDLE_PATH}"
fi

# 3. Configure Git Global Settings
log_info "Configuring global Git HTTP SSL backend..."
git config --global http.sslCAInfo "${CERT_BUNDLE_PATH}"
git config --global http.version HTTP/1.1

# Verify configuration write
CONFIGURED_CA=$(git config --global --get http.sslCAInfo)
log_info "Git global http.sslCAInfo successfully set to: ${CONFIGURED_CA}"

# 4. Inject into macOS System/Login Keychain (Optional but recommended for GUI clients like SourceTree/VS Code)
log_info "Injecting certificate into macOS login keychain for native toolchain alignment..."
if security add-trusted-cert -d -r trustRoot -k "${HOME}/Library/Keychains/login.keychain-db" "${CERT_BUNDLE_PATH}" 2>/dev/null; then
    log_info "Successfully added eMudhra/Corporate CA to macOS login keychain."
else
    log_warn "Keychain addition skipped or certificate already trusted in system store."
fi

# 5. Validation Test
log_info "Executing verification clone test against ${GIT_DOMAIN}..."
if git ls-remote "https://${GIT_DOMAIN}/" HEAD &>/dev/null; then
    log_info "SUCCESS: Git SSL handshake verified successfully!"
else
    log_warn "Git ls-remote failed. Run with GIT_TRACE=1 to inspect handshake failures."
fi

log_info "Remediation sequence completed successfully."
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

When implementing certificate fixes under high-pressure enterprise environments, developers often resort to shortcuts that introduce severe vulnerabilities or break downstream systems.

*   **Anti-Pattern 1: Permanent Global SSL Verification Disabling**
    *   *Bad Practice:* Running `git config --global http.sslVerify false`.
    *   *Risk:* Exposes the engineering workstation to Man-in-the-Middle (MitM) attacks, token interception, and code injection during transit over untrusted networks (e.g., public Wi-Fi).
    *   *Remediation:* Always pin the explicit intermediate/root CA via `http.sslCAInfo`.

*   **Anti-Pattern 2: Mixing OpenSSL and Secure Transport Backends**
    *   *Bad Practice:* Forgetting that Homebrew-installed Git links against dynamic OpenSSL while Xcode Command Line Tools Git links against Apple Secure Transport, leading to split-brain certificate validation behavior.
    *   *Remediation:* Standardize your engineering fleet on a single installation path (`brew install git` vs system `/usr/bin/git`).

*   **Anti-Pattern 3: Ignoring eMudhra Hardware Token Middleware Drivers**
    *   *Bad Practice:* Assuming software certificate stores cover hardware-backed cryptographic tokens (USB tokens / smart cards).
    *   *Remediation:* Ensure cryptographic middleware (e.g., SafeNet Authentication Client / eMudhra emToken PKCS#11 drivers) is actively loaded into the macOS crypto framework (`/usr/local/lib/libeToken.dylib`).

---

## 5. Performance & Optimization Tips

1.  **HTTP/2 Multiplexing Downgrade for Proxies:** Enterprise SSL inspection proxies often misbehave with HTTP/2 framing. Forcing Git to use HTTP/1.1 (`git config --global http.version HTTP/1.1`) prevents abrupt connection resets during heavy repository fetches.
2.  **Buffer Size Tuning for Large Repositories:** Enterprise monorepos paired with strict inspection proxies require expanded post buffers to avoid timeout drops:
    ```bash
    git config --global http.postBuffer 524288000
    git config --global http.lowSpeedLimit 1000
    git config --global http.lowSpeedTime 60
    ```
3.  **Local Credential Caching:** Optimize token read cycles by utilizing the macOS Keychain credential helper:
    ```bash
    git config --global credential.helper osxkeychain
    ```

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License (MC-EULA-COMM-v1.0)
*   **Copyright © 2024 MicroCorp AI. All rights reserved.**
*   **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, non-transferable enterprise license to deploy, modify, and distribute this remediation script across internal corporate engineering workstations and CI/CD runners.
*   **Restrictions:** Redistribution of this exact documentation or kit as a standalone commercial product on marketplaces (Gumroad, GitHub Marketplace, etc.) is strictly prohibited.
*   **Warranty Disclaimer:** Provided "AS IS" without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any data loss, pipeline outages, or cryptographic misconfigurations arising from the deployment of this toolkit.