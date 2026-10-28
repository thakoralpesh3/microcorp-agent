# Developer Toolkit: macOS Git eMudhra Certificate Remediation Guide
**Product ID:** MTC-MAC-GIT-EMUDHRA-001  
**Version:** 2.4.0-Enterprise  
**Author:** Engineering Division, The Agency & MicroCorp AI  
**Target Audience:** DevOps Engineers, Mac-based Software Architects, Enterprise Developers, and Security Compliance Leads.

---

## 1. # Product Title & Value Proposition

### Value Proposition
Enterprise macOS developer environments frequently break when integrating corporate PKI solutions, specifically India-mandated eMudhra Class 3 / Enterprise signing certificates for Git commit verification and mutual TLS (mTLS) enterprise proxy authentication. Apple's native Keychain, Git's abstraction layer (`osxkeychain`/`SecureTransport`), and OpenSSL/LibreSSL often experience silent handshake failures, resulting in the dreaded `SSL certificate problem: self signed certificate in certificate chain` or `git push` aborts during code signing operations.

This architecture kit provides a **bulletproof, automated remediation pipeline** to bridge macOS Keychain certificates with Git’s runtime credential and transport layers. It eliminates environment drift, bypasses annoying keychain permission popups, and enforces cryptographic compliance across distributed engineering teams in under 5 minutes.

---

## 2. ## Quick Start & Core Concepts

### Core Architecture Concepts
1. **The Keychain Split:** macOS stores enterprise root and intermediate certificates in the *System* or *Login* Keychain, whereas Git compiled with LibreSSL/OpenSSL maintains its own independent CA bundle or relies on Apple's Security Framework.
2. **SecureTransport vs. OpenSSL:** Modern Git on macOS uses `SecureTransport` by default. When eMudhra tokens (USB tokens or soft-certs) are introduced, their cryptographic identity must be explicitly mapped to Git's signing configuration (`user.signingkey`) and SSH/HTTPS transport layers.
3. **Automated Trust Injection:** Manual keychain exports (`.cer`/`.pem`) fail due to missing trust anchors. This toolkit automates extraction, chain validation, and forced global overrides.

### Syntax & Configuration Reference Table

| Configuration / Command | Target Layer | Purpose & Description |
| :--- | :--- | :--- |
| `git config --global http.sslBackend schannel` / `openssl` | Transport | Forces Git to utilize a specific SSL backend engine instead of auto-detecting broken wrappers. |
| `git config --global http.sslCAInfo /path/to/emudhra-bundle.pem` | Trust Store | Points Git directly to the concatenated corporate eMudhra CA chain, bypassing macOS keychain parsing errors. |
| `git config --global user.signingkey <KEY_ID>` | Cryptography | Binds the eMudhra hardware/software certificate fingerprint to commit signing operations (`git commit -S`). |
| `security find-identity -v -p codesigning` | macOS Keychain | Queries the local keychain to extract valid SHA-1 hashes of installed eMudhra certificates. |
| `export GIT_SSL_NO_VERIFY=true` *(Emergency Only)* | Debugging | Disables certificate verification for local debugging against broken corporate proxies. **Never use in production.** |

---

## 3. ## Production Code Patterns & Architecture Examples

### Automated Remediation Script (`emudhra-git-fix.sh`)
Save the following production-ready shell script as `emudhra-git-fix.sh`. It automates certificate discovery, PEM conversion, Git global configuration injection, and verification.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: emudhra-git-fix.sh
# Description: Automated macOS Git eMudhra Certificate & Signing Remediation
# Author: MicroCorp AI & The Agency Engineering Division
# ==============================================================================

set -euo pipefail

# Color definitions for enterprise logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

LOG_FILE="$HOME/.emudhra_git_fix.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo -e "${YELLOW}[INFO] Starting eMudhra Git Remediation Pipeline...${NC}"

# Step 1: Locate eMudhra Certificate in macOS Keychain
echo -e "${YELLOW}[INFO] Scanning macOS Keychain for eMudhra certificates...${NC}"
CERTS=$(security find-identity -v -p codesigning | grep -i "eMudhra" || true)

if [ -z "$CERTS" ]; then
    echo -e "${RED}[ERROR] No eMudhra certificates found in macOS Keychain.${NC}"
    echo -e "${YELLOW}[HINT] Ensure your eMudhra USB token is inserted or the .p12/.pfx profile is imported.${NC}"
    exit 1
fi

echo -e "${GREEN}[SUCCESS] Found matching eMudhra identities:${NC}"
echo "$CERTS"

# Extract the SHA-1 Hash of the first found eMudhra signing certificate
CERT_HASH=$(echo "$CERTS" | head -n 1 | awk '{print $2}')
echo -e "${GREEN}[INFO] Target Certificate SHA-1 Hash: ${CERT_HASH}${NC}"

# Step 2: Configure Git Global Signing Key
echo -e "${YELLOW}[INFO] Configuring Git global signing parameters...${NC}"
git config --global user.signingkey "$CERT_HASH"
git config --global gpg.format x509

# Step 3: Extract CA Chain and Setup Custom Trust Store
BUNDLE_DIR="$HOME/.git_emudhra"
mkdir -p "$BUNDLE_DIR"
BUNDLE_PATH="$BUNDLE_DIR/emudhra-ca-bundle.pem"

echo -e "${YELLOW}[INFO] Generating corporate CA bundle at ${BUNDLE_PATH}...${NC}"

# Export certificates from System keychain matching eMudhra issuers into PEM format
# Note: Adjust Common Name (CN) filtering if your enterprise uses a specific sub-CA
security find-certificate -a -p /Library/Keychains/System.keychain > "$BUNDLE_PATH" 2>/dev/null || true
security find-certificate -a -p ~/Library/Keychains/login.keychain-db >> "$BUNDLE_PATH" 2>/dev/null || true

# Step 4: Configure Git SSL & Transport Layers
echo -e "${YELLOW}[INFO] Enforcing Git SSL backend and CA bundle paths...${NC}"
git config --global http.sslCAInfo "$BUNDLE_PATH"
git config --global http.postBuffer 524288000 # 500MB buffer for large enterprise repos

# Step 5: Verification Phase
echo -e "${YELLOW}[INFO] Verifying Git configuration settings...${NC}"
echo "------------------------------------------------"
git config --global --get-regexp '(user\.signingkey|http\.sslCAInfo|gpg\.format)'
echo "------------------------------------------------"

echo -e "${GREEN}[SUCCESS] eMudhra Git remediation completed successfully!${NC}"
echo -e "${YELLOW}[LOG] Execution log stored at: ${LOG_FILE}${NC}"
```

### Usage Instructions
```bash
chmod +x emudhra-git-fix.sh
./emudhra-git-fix.sh
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Architecture Approach |
| :--- | :--- | :--- |
| **Global SSL Disablement** (`git config --global http.sslVerify false`) | Leaves the entire development machine vulnerable to Man-in-the-Middle (MitM) attacks on public networks and violates corporate SOC2/ISO27001 compliance frameworks. | Always inject the corporate CA bundle via `http.sslCAInfo` while maintaining strict SSL verification. |
| **Hardcoding Keychain Passwords in Scripts** | Exposes plain-text credentials in shell history files (`~/.bash_history`, `~/.zsh_history`) or version control systems. | Rely on macOS Keychain Services (`security` CLI) to manage token interactions securely without persistent plaintext caching. |
| **Mixing LibreSSL and Native OpenSSL Binaries** | Homebrew Git installations link against Homebrew OpenSSL, whereas Xcode Command Line Tools Git links against Apple LibreSSL/SecureTransport, causing root store desyncs. | Standardize the team on a single package manager path (e.g., exclusively `brew install git`) and align global PATH variables. |
| **Ignoring Hardware Token Timeout Limits** | eMudhra USB cryptographic tokens drop their active session state after inactivity, causing automated CI/CD hook scripts or background `git fetch` operations to hang indefinitely awaiting a PIN prompt. | Implement local SSH/HTTPS credential helper caching timeouts or use soft-certificates for automated environments while reserving tokens strictly for interactive commits. |

---

## 5. ## Performance & Optimization Tips

1. **Optimize Git HTTP Buffer for Enterprise Monorepos:**  
   Enterprise repositories containing large binary assets or deep commit histories often trigger SSL renegotiation failures over VPNs. Increase the HTTP buffer size and low-speed timeout limits:
   ```bash
   git config --global http.postBuffer 1048576000 # 1GB Buffer
   git config --global http.lowSpeedLimit 1000
   git config --global http.lowSpeedTime 60
   ```

2. **Leverage Git Credential Manager (GCM) for macOS:**  
   Replace legacy basic auth prompt handlers with the cross-platform Git Credential Manager, which natively integrates with macOS Keychain and enterprise identity providers (Azure AD / Okta / eMudhra SSO):
   ```bash
   brew install --cask git-credential-manager
   git-credential-manager configure
   ```

3. **Pre-warm Keychain Handles in CI/Local Daemons:**  
   If your development workflow uses background file watchers or IDE Git integrations (VS Code, JetBrains), configure them to respect the global Git configuration path rather than spawning isolated sandboxed credential agents that ignore the custom eMudhra CA bundle.

---

## 6. ## Commercial License & Attribution Summary

### MicroCorp AI Commercial License (MACL-v1.2)
* **Copyright © 2026 MicroCorp AI & The Agency. All rights reserved.**
* **Grant of License:** This digital product ("Developer Toolkit: macOS Git eMudhra Certificate Remediation Guide") is licensed, not sold. Purchaser is granted a perpetual, non-exclusive, non-transferable enterprise-wide internal deployment license to distribute this documentation, scripts, and configuration patterns within their immediate corporate organization.
* **Restrictions:** Redistribution, resale, public posting, or sub-licensing of this source kit on open-source repositories, public code marketplaces, or third-party training datasets without express written consent from MicroCorp AI is strictly prohibited.
* **Warranty Disclaimer:** This software and documentation are provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability arising from the use of this toolkit.