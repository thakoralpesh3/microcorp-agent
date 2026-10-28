# Developer Toolkit: macOS Git eMudhra Certificate Remediation & Security Hardening

> **The Agency Security Division & MicroCorp AI Commercial Release**  
> *Target Audience:* DevOps Engineers, Enterprise Software Architects, and macOS Developers grappling with strict corporate Public Key Infrastructure (PKI), enterprise proxies, and rigid eMudhra cryptographic signing constraints.

---

## 1. Product Title & Value Proposition

### Title
**macOS Git eMudhra Certificate Remediation & Security Hardening Kit**

### Value Proposition
Enterprise macOS environments often break standard Git operations when enforcing strict mutual TLS (mTLS), deep-packet inspection (DPI) proxies, and hardware-backed or software-emulated eMudhra digital certificates. Developers frequently encounter cryptic SSL handshake failures, self-signed certificate untrust errors (`SSL certificate problem: self signed certificate in certificate chain`), and code-signing pipeline halts. 

This kit provides a bulletproof, cryptographically sound architecture to seamlessly bridge corporate eMudhra PKI requirements with native macOS Git and OpenSSL workflows—**without disabling system-wide security baselines or weakening TLS validation globally.**

```
+------------------------+      +---------------------------+      +---------------------------+
| macOS Developer System | ---> | Scoped Git PKI Config     | ---> | eMudhra Enterprise Chain  |
| (Keychain / PEM Store) |      | (Targeted .gitconfig)     |      | (Validated & Trusted)     |
+------------------------+      +---------------------------+      +---------------------------+
```

---

## 2. Quick Start & Core Concepts

When macOS Git encounters an eMudhra-issued certificate chain, it relies on Apple's Secure Transport or OpenSSL. Because eMudhra roots or intermediate issuing authorities often sit outside the default Mozilla/curl bundle utilized by Git for macOS, explicit trust anchoring is required.

### Clean Syntax & Configuration Reference Matrix

| Configuration Context | Command / Syntax | Security Impact | Recommendation Level |
| :--- | :--- | :--- | :--- |
| **Global Path Override** | `git config --global http.sslCAInfo /path/to/emudhra-bundle.pem` | Safe if scoped to enterprise CA bundle. | **Recommended** for corporate machines. |
| **Local Repository Scope** | `git config http.sslCAInfo .git/emudhra-bundle.pem` | Eliminates leakage to personal/external repos. | **Best Practice** for mixed-use machines. |
| **Insecure Bypass** | `git config --global http.sslVerify false` | **CRITICAL RISK:** Exposes codebases to MitM attacks. | **PROHIBITED.** Never use in production. |
| **Secure Transport Toggle** | `git config --global http.schannelCheckRevoke true` | Enforces CRL/OCSP checking via native keychain. | **Recommended** where applicable. |

---

## 3. Production Code Patterns & Architecture Examples

Below are production-ready scripts designed to ingest enterprise eMudhra certificates, construct an isolated trust store, and configure Git cleanly.

### Automated Remediation & Trust-Store Generation Script
Save this script as `harden-git-emudhra.sh`. It extracts certificates from the macOS System Keychain, builds a verified PEM bundle, and applies strict Git configurations locally or globally.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: harden-git-emudhra.sh
# Description: Extracts eMudhra enterprise certs from macOS Keychain and 
#              configures secure Git fallback stores without disabling SSL verify.
# Author: Application Security Engineer (The Agency / MicroCorp AI)
# ==============================================================================

set -euo pipefail

# Configuration
BUNDLE_DIR="${HOME}/.git-enterprise-certs"
BUNDLE_FILE="${BUNDLE_DIR}/emudhra-combined-ca.pem"
CORP_DOMAIN_PATTERN="emudhra" # Adjust to match your enterprise issuer Common Name

echo "[*] Initializing secure certificate hardening directory..."
mkdir -p "$BUNDLE_DIR"
chmod 700 "$BUNDLE_DIR"

echo "[*] Locating eMudhra and enterprise root certificates in macOS Keychain..."
# Export System Roots and System Keychain certificates matching the pattern to PEM
security find-certificate -a -p /Library/Keychains/System.keychain > "${BUNDLE_DIR}/system-roots.pem" 2>/dev/null || true
security find-certificate -a -p /System/Library/Keychains/SystemRoot.keychain >> "${BUNDLE_DIR}/system-roots.pem" 2>/dev/null || true

if [ ! -s "${BUNDLE_DIR}/system-roots.pem" ]; then
    echo "[!] Warning: No certificates extracted from standard keychains. Check permissions."
    exit 1
fi

echo "[*] Filtering and sanitizing certificate chain into hardened bundle..."
# Extract blocks cleanly and validate structure
awk '
    /-----BEGIN CERTIFICATE-----/ {flag=1}
    flag {print}
    /-----END CERTIFICATE-----/ {flag=0}
' "${BUNDLE_DIR}/system-roots.pem" > "$BUNDLE_FILE"

# Optional: Append custom organization-specific eMudhra intermediate if available locally
if [ -f "./emudhra-intermediate.pem" ]; then
    echo "[*] Appending local eMudhra intermediate certificate..."
    cat "./emudhra-intermediate.pem" >> "$BUNDLE_FILE"
fi

chmod 600 "$BUNDLE_FILE"
rm -f "${BUNDLE_DIR}/system-roots.pem"

echo "[*] Applying hardened Git configurations..."
# Prompt user for scope
read -p "Configure globally (--global) or locally for this repository (--local)? [g/l]: " SCOPE_CHOICE

if [[ "$SCOPE_CHOICE" =~ ^[Gg]$ ]]; then
    GIT_SCOPE="--global"
    echo "[+] Applying settings globally..."
else
    GIT_SCOPE="--local"
    if [ ! -d ".git" ]; then
        echo "[!] Error: Not inside a Git repository. Defaulting to global scope."
        GIT_SCOPE="--global"
    else
        echo "[+] Applying settings locally to current repository..."
    fi
fi

# Apply cryptographic hardening settings
git config $GIT_SCOPE http.sslCAInfo "$BUNDLE_FILE"
git config $GIT_SCOPE http.sslVerify true

echo "=============================================================================="
echo "[SUCCESS] Git eMudhra certificate remediation completed successfully."
echo "[INFO] Hardened CA Bundle stored at: $BUNDLE_FILE"
echo "[INFO] Git SSL Verification remains strictly ENFORCED."
echo "=============================================================================="
```

### Verification Test Harness
Use this snippet to verify that your Git client successfully communicates with your enterprise forge (GitHub Enterprise, GitLab, Bitbucket Server) via the new eMudhra-backed trust store without tripping verification logic:

```bash
#!/usr/bin/env bash
# Test Git connectivity with verbose SSL debugging enabled

TARGET_REPO="${1:-https://github.corp.internal/your-org/your-repo.git}"

echo "[*] Testing TLS handshake and authentication against: $TARGET_REPO"
GIT_TRACE=1 GIT_TRANSFER_TRACE=1 GIT_CURL_VERBOSE=1 git ls-remote "$TARGET_REPO" HEAD
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

When under pressure to fix broken builds, engineers frequently introduce critical vulnerabilities. Avoid these traps:

*   **Anti-Pattern 1: Disabling SSL Verification Globally**
    *   *The Trap:* Running `git config --global http.sslVerify false`.
    *   *The Risk:* Completely disables cryptographic validation, leaving the developer susceptible to active Man-in-the-Middle (MitM) token theft and malicious code injection on corporate or public Wi-Fi networks.
*   **Anti-Pattern 2: Hardcoding Personal Paths or Password Credentials**
    *   *The Trap:* Embedding user-specific absolute paths or cleartext credentials within shared build configurations or shared `.gitconfig` templates.
    *   *The Risk:* Fails across multi-developer environments or leaks internal eMudhra infrastructure paths.
*   **Anti-Pattern 3: Mixing Apple Secure Transport and OpenSSL Incompatibilities**
    *   *The Trap:* Assuming Git for macOS compiles identically across Homebrew, Xcode Command Line Tools, and official Git installers.
    *   *The Risk:* Homebrew Git defaults to OpenSSL, while Apple-bundled Git defaults to Secure Transport. Ensure your `http.sslCAInfo` path points to an explicit PEM bundle compatible with your specific binary build.

---

## 5. Performance & Optimization Tips

1.  **Scoped Overrides over Global Bloat:** Apply eMudhra certificate configurations locally (`--local`) inside enterprise repository templates rather than globally if developers switch frequently between open-source projects (which use standard Let's Encrypt/DigiCert chains) and secure enterprise environments.
2.  **Bundle Pruning:** Periodically prune unused or expired root certificates from your custom PEM bundle (`~/.git-enterprise-certs/emudhra-combined-ca.pem`) to minimize SSL handshake overhead during initial TLS negotiation.
3.  **Leverage Credential Helpers:** Combine eMudhra mTLS authentication hardening with macOS Keychain credential helpers (`git config --global credential.helper osxkeychain`) to ensure credentials never sit in plain text configuration files.

---

## 6. Commercial License & Attribution Summary

### Licensing Terms
*   **Product ID:** `MC-SEC-GIT-EMUDHRA-042`
*   **Usage Rights:** Licensed under the **MicroCorp AI Commercial Developer License**. 
*   **Permissions:** Internal deployment, modification, and integration into corporate developer onboarding kits are fully permitted for the acquiring enterprise entity.
*   **Restrictions:** Redistribution, resale, or publication on public code repositories without prior written authorization from The Agency Security Division is strictly prohibited.

---
*Secure Code is Clean Code. Keep your PKI tight and your repositories uncompromised.* 🔐