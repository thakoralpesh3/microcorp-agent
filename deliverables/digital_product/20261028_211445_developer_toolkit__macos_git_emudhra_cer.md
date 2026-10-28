# Developer Toolkit: macOS Git eMudhra Certificate Remediation Guide & Boilerplates

> **Product SKU:** MC-MACP-EMUD-012  
> **Target Audience:** Senior DevOps Engineers, Enterprise macOS Developers, Security Compliance Officers  
> **Format:** Enterprise Engineering Reference & Remediation Kit  

---

## 1. # Product Title & Value Proposition

### The Enterprise Pain Point
When enterprise developers operating on macOS attempt to push, fetch, or clone from internal Git repositories (such as GitLab, GitHub Enterprise, or Bitbucket Data Center) secured by private corporate Public Key Infrastructure (PKI)—specifically **eMudhra Enterprise CA** roots—Git operations fail catastrophically. 

Standard error outputs include:
* `SSL certificate problem: self signed certificate in certificate chain`
* `curl 60: SSL certificate problem: unable to get local issuer certificate`
* `fatal: unable to access 'https://git.corp.internal/': schannel: failed to receive handshake`

This happens because the native macOS Git binary relies on Apple’s Secure Transport or embedded `libcurl` stores which frequently fail to inherit intermediate and root certificates injected via enterprise Mobile Device Management (MDM) profiles or manual eMudhra enterprise trust stores.

### The Value Proposition
This developer kit provides a **zero-downtime, automated remediation architecture**. It bridges macOS system keychains with Git’s isolated runtime environment. By deploying these battle-tested configuration scripts and system daemon boilerplates, engineering organizations eliminate developer onboarding friction, secure continuous integration (CI/CD) runners, and enforce strict zero-trust transport security compliance across all Apple Silicon and Intel macOS workstations.

---

## 2. ## Quick Start & Core Concepts

### Core Architecture Concepts
1. **System Keychain vs. Git CA Store:** macOS uses Keychain Access (`/Library/Keychains/System.keychain`), while Git can use Apple Secure Transport, OpenSSL, or dynamic bundle files (`curl-ca-bundle.crt`). 
2. **eMudhra Intermediate Chain Binding:** Corporate eMudhra deployments require both the Root CA and the Issuing Sub-CA to be explicitly trusted in the correct format (`.pem` or `.cer`).
3. **Targeted Scope Configuration:** Remediations can be applied globally (`~/.gitconfig`), system-wide (`/etc/gitconfig`), or via automated environment injection to prevent blanket SSL verification bypasses (`http.sslVerify = false`), which violate SOC2 and ISO-27001 policies.

### Syntax & Configuration Reference Table

| Configuration Directive | Scope | Purpose | Production Recommendation |
| :--- | :--- | :--- | :--- |
| `http.sslCAInfo` | Global / System | Points Git explicitly to the enterprise eMudhra bundle. | **Mandatory.** Use absolute path to verified PEM file. |
| `http.sslVerify` | Local / Global | Toggles SSL certificate verification checks. | **Never set to `false`.** Fix the chain instead. |
| `core.askPass` | System | Handles credential helper interactions securely. | Pair with macOS Keychain credential helper. |
| `credential.helper` | Global | Caches PATs/Kerberos tokens securely. | Set to `osxkeychain` for native integration. |
| `http.schannelCheckRevoke` | Windows Only | N/A for macOS; keep unconfigured. | Leave unset on macOS architectures. |

---

## 3. ## Production Code Patterns & Architecture Examples

### Pattern 1: Automated eMudhra Certificate Extraction & Git Configuration Script
Save this script as `remediate-emudhra-git.sh`. It extracts the corporate eMudhra root certificates from the macOS System Keychain, bundles them into an enterprise PEM file, and configures Git securely.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: remediate-emudhra-git.sh
# Description: Automated macOS Git eMudhra Certificate Chain Fixer
# Target: macOS Ventura, Sonoma, Sequoia (Apple Silicon & Intel)
# ==============================================================================

set -euo pipefail

# Configuration Variables
GIT_CONFIG_PATH="${HOME}/.gitconfig"
CERT_DIR="${HOME}/.git/certs"
EMUDHRA_PEM="${CERT_DIR}/emudhra-enterprise-chain.pem"
LOG_PREFIX="[EMUDHRA-REMEDIATION]"

echo "${LOG_PREFIX} Initializing Git SSL remediation for eMudhra PKI..."

# 1. Create secure certificate directory structure
if [ ! -d "$CERT_DIR" ]; then
    mkdir -p "$CERT_DIR"
    chmod 755 "$CERT_DIR"
    echo "${LOG_PREFIX} Created secure directory at ${CERT_DIR}"
fi

# 2. Extract eMudhra certificates from macOS System Keychain
# Note: Adjust the common name search query to match your organization's eMudhra CA CN
echo "${LOG_PREFIX} Extracting eMudhra certificates from macOS System Keychain..."
security find-certificate -c "eMudhra" -a -p > "${EMUDHRA_PEM}" || {
    echo "${LOG_PREFIX} WARNING: Direct extraction via common name failed. Attempting fallback export..."
    # Fallback: Export trusted roots if specific CN is unavailable
    security find-certificate -a -Z -p /Library/Keychains/System.keychain > "${EMUDHRA_PEM}"
}

if [ ! -s "${EMUDHRA_PEM}" ]; then
    echo "${LOG_PREFIX} ERROR: Failed to extract certificates. Verify eMudhra profile installation." >&2
    exit 1
fi

CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" "${EMUDHRA_PEM}")
echo "${LOG_PREFIX} Successfully bundled ${CERT_COUNT} certificate(s) into ${EMUDHRA_PEM}"

# 3. Apply Git Global Configuration Settings
echo "${LOG_PREFIX} Applying secure global Git configurations..."
git config --global http.sslCAInfo "${EMUDHRA_PEM}"
git config --global http.sslVerify true
git config --global credential.helper osxkeychain

# 4. Verification Check
echo "${LOG_PREFIX} Verifying configuration against internal endpoint..."
# Replace with your enterprise git domain for testing
TEST_DOMAIN="git.corp.internal"
if nc -zvw1 "${TEST_DOMAIN}" 443 &>/dev/null; then
    if git ls-remote "https://${TEST_DOMAIN}/vcs/scm" HEAD &>/dev/null; then
        echo "${LOG_PREFIX} SUCCESS: Git authenticated successfully with eMudhra SSL chain verified!"
    else
        echo "${LOG_PREFIX} NOTICE: Network reachable, but Git authentication requires manual credential entry."
    fi
else
    echo "${LOG_PREFIX} NOTICE: Test domain ${TEST_DOMAIN} is currently unreachable (VPN may be disconnected)."
fi

exit 0
```

### Pattern 2: Enterprise LaunchAgent for Continuous Certificate Sync
MDM profiles or eMudhra token updates can alter keychain entries. Deploy this `com.microcorp.git-emudhra-sync.plist` to `/Library/LaunchAgents/` to automatically re-sync certificates upon user login.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.microcorp.git-emudhra-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/remediate-emudhra-git.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>86400</integer>
    <key>StandardOutPath</key>
    <string>/var/log/git-emudhra-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/git-emudhra-sync.error.log</string>
</dict>
</plist>
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Global SSL Verification Disabling
* **The Mistake:** Running `git config --global http.sslVerify false` across developer terminals or CI pipelines.
* **The Risk:** Exposes internal repositories to Man-in-the-Middle (MitM) attacks, credential sniffing, and severe compliance violations (SOC2, ISO 27001, HIPAA).
* **The Correct Approach:** Always inject the specific eMudhra CA bundle using `http.sslCAInfo` while maintaining `http.sslVerify = true`.

### ❌ Anti-Pattern 2: Hardcoding Absolute User Paths in Shared Configs
* **The Mistake:** Committing `.gitconfig` files containing user-specific home paths (e.g., `/Users/john.doe/.git/certs/...`) into team boilerplate repositories.
* **The Risk:** Breaks Git operations for every developer whose short username differs from the configuration author.
* **The Correct Approach:** Use environment variables or shell scripts (like Pattern 1) to dynamically construct paths relative to `$HOME`.

### ❌ Anti-Pattern 3: Ignoring Intermediate Certificate Chains
* **The Mistake:** Exporting only the leaf eMudhra root certificate without capturing the intermediate signing authorities.
* **The Risk:** Git throws validation errors because the validation path cannot construct a complete trust chain from the server certificate up to the root store.
* **The Correct Approach:** Export the entire keychain slot or bundle all operational CAs into the PEM file.

---

## 5. ## Performance & Optimization Tips

1. **Leverage Git HTTP Multiplexing:** Enable HTTP/2 and connection reuse in your global config to accelerate clone and fetch speeds across enterprise gateways:
   ```bash
   git config --global http.version HTTP/2
   git config --global http.lowSpeedLimit 1000
   git config --global http.lowSpeedTime 60
   ```
2. **Optimize Core Compression Settings for Apple Silicon:** Maximize multi-threaded pack compression leveraging unified memory performance:
   ```bash
   git config --global pack.threads 0
   git config --global core.compression 6
   ```
3. **Cache Management:** Prevent keychain prompt fatigue by extending credential timeout caching safely:
   ```bash
   git config --global credential.helper "osxkeychain --timeout=43200"
   ```

---

## 6. ## Commercial License & Attribution Summary

### MicroCorp AI Commercial License (MACL-v1.2)
*Copyright © 2026 MicroCorp AI. All rights reserved.*

1. **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, non-transferable enterprise license to deploy, modify, and distribute these scripts and boilerplates internally across all corporate-managed macOS endpoints within the purchasing organization.
2. **Restrictions:** Redistribution of this exact architectural kit, documentation, or code boilerplates on public marketplaces, open-source code hosting platforms without explicit authorization, or resale to third parties is strictly prohibited.
3. **Warranty Disclaimer:** This software and reference kit are provided "as is" without warranty of any kind, express or implied. MicroCorp AI explicitly disclaims liability for any direct, indirect, or consequential damages resulting from PKI misconfigurations or deployment errors.

---
*End of Document — MicroCorp AI Engineering Division.*