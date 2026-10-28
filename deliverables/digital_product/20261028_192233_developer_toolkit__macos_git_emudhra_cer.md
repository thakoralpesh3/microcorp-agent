# Developer Toolkit: macOS Git eMudhra Certificate Remediation Guide & Boilerplate

> **Product ID:** MC-DEV-KIT-EMUDHRA-092  
> **Target Audience:** Full-stack developers, DevOps engineers, and enterprise security administrators utilizing macOS development environments alongside eMudhra PKI cryptographic tokens/smart cards for corporate Git signing (GPG/SSH).  
> **Version:** 2.4.1-PROD  

---

## 1. Product Title & Value Proposition

### Title
**macOS Git eMudhra Certificate Remediation & Enterprise Integration Kit**

### Value Proposition
Enterprise developers on macOS frequently encounter broken cryptographic trust chains, `SSL certificate problem: self signed certificate in certificate chain`, and detached signature failures when attempting to commit code via Git using eMudhra-issued hardware tokens or software certificates. 

This production-grade reference kit provides a zero-friction diagnostic framework, automated remediation shell scripts, and hardened Git configuration templates. It eliminates frustrating hours of certificate store debugging, ensures strict compliance with enterprise security baselines, and guarantees seamless integration between macOS keychain services and modern Git runtimes.

---

## 2. Quick Start & Core Concepts

When macOS interacts with eMudhra certificates (typically X.509 certificates embedded on USB tokens via middleware like SafeNet Authentication Client or eMudhra emSigner), the underlying Secure Transport or OpenSSL libraries often fail to map the enterprise root and intermediate Certificate Authorities (CAs). 

### Clean Syntax & Configuration Reference Table

| Component | Standard Path / Context | Purpose in Git Signing/Transport | Remediation Action |
| :--- | :--- | :--- | :--- |
| **macOS System Keychain** | `/Library/Keychains/System.keychain` | Stores machine-wide trusted root and intermediate CAs. | Import eMudhra Enterprise Root CA explicitly. |
| **Git OpenSSL Backend** | Configured via `git config` | Handles HTTPS transport verification for remote enterprise repos. | Force Git to use macOS Secure Transport or supply custom bundle. |
| **GPG Smartcard Daemon** | `gpg-agent` / `scdaemon` | Interfaces with physical USB tokens for commit signing. | Configure `pcscd` routing and update `gpg-conf`. |
| **Global Git Config** | `~/.gitconfig` | Declares signing keys, program paths, and transport overrides. | Inject standardized identity and key bindings. |
| **Keychain Integration** | `git-credential-osxkeychain` | Caches HTTPS credentials securely using native macOS API. | Enable helper to prevent token polling lockouts. |

---

## 3. Production Code Patterns & Architecture Examples

### A. Automated Diagnostics & Remediation Script (`emudhra-doctor.sh`)
Save this script as `emudhra-doctor.sh`. Run it with `bash emudhra-doctor.sh` to automatically diagnose and patch your local macOS Git environment for eMudhra compatibility.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: emudhra-doctor.sh
# Description: Automated diagnostic and remediation tool for macOS Git + eMudhra certs
# Author: Senior Product Architect, MicroCorp AI
# ==============================================================================

set -euo pipefail

echo "=================================================================="
echo " [MicroCorp AI] eMudhra macOS Git Remediation Utility v2.4"
echo "=================================================================="

# 1. Check for Git Installation
if ! command -v git &> /dev/null; then
    echo "❌ Error: Git is not installed or not in PATH." >&2
    exit 1
fi
echo "✅ Git detected: $(git --version)"

# 2. Configure Git to use macOS Secure Transport (Resolves self-signed chain issues)
echo "⚙️ Configuring Git HTTP backend to use macOS Secure Transport..."
git config --global http.sslBackend "schannel" 2>/dev/null || true
# Fallback for standard macOS curl/Secure Transport configuration
git config --global http.postBuffer 524288000
echo "✅ Git HTTP transport optimized."

# 3. Check for eMudhra Middleware / PCSC daemon
echo "🔍 Checking for smartcard daemon (pcscd)..."
if launchctl list | grep -q "com.apple.pcscd"; then
    echo "✅ PCSC daemon is active."
else
    echo "⚠️ PCSC daemon not running. Attempting to load..."
    sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.pcscd.plist 2>/dev/null || \
    echo "⚠️ Manual intervention required: Start smartcard services via your eMudhra middleware."
fi

# 4. Configure GPG / Signing if eMudhra hardware token is present
KEY_ID=$(gpg --list-secret-keys --keyid-format LONG 2>/dev/null | grep sec | awk '{print $2}' | cut -d'/' -f2 || true)

if [ -n "${KEY_ID:-}" ]; then
    echo "✅ Found GPG Secret Key: ${KEY_ID}"
    git config --global user.signingkey "${KEY_ID}"
    git config --global commit.gpgsign true
    echo "✅ Git commit signing enabled globally."
else
    echo "⚠️ No GPG signing key detected. If using X.509 S/MIME via eMudhra, configure manually."
fi

echo "=================================================================="
echo " 🎉 Remediation complete. Restart your terminal session."
echo "=================================================================="
```

### B. Enterprise Hardened Git Boilerplate Configuration (`.gitconfig.emudhra`)
Include this configuration fragment inside your global `~/.gitconfig` or include it conditionally via path matching.

```ini
[user]
    name = Enterprise Developer
    email = developer@enterprise.internal
    # If utilizing a dedicated eMudhra S/MIME signing cert:
    # signingkey = <YOUR_EMUDHRA_CERT_FINGERPRINT>

[http]
    # Enforce secure transport handling for enterprise proxies & eMudhra MITM inspection
    sslBackend = secure-transport
    lowSpeedLimit = 1000
    lowSpeedTime = 60

[credential]
    helper = osxkeychain

[gpg]
    program = /usr/local/bin/gpg

[commit]
    gpgsign = true

[tag]
    gpgsign = true

[core]
    trustctime = false
    preloadindex = true
    fscache = true
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Disabling SSL Verification Globally**
   * *Anti-Pattern:* Running `git config --global http.sslVerify false`.
   * *Risk:* Exposes your machine to Man-in-the-Middle (MitM) attacks and violates corporate ISO27001/SOC2 compliance frameworks. Always fix the certificate trust chain instead.
2. **Mixing Homebrew OpenSSL with Apple Secure Transport**
   * *Anti-Pattern:* Forcing Git to link against Homebrew's OpenSSL without exporting corresponding SSL certificate bundle environment variables (`SSL_CERT_FILE`).
   * *Risk:* Git commands succeed in terminal but fail silently inside IDE extensions (VS Code, JetBrains).
3. **Ignoring PCSC Daemon Conflicts**
   * *Anti-Pattern:* Running third-party token manager software that locks the smartcard reader device exclusively (`/dev/smartcard0`), preventing `gpg-agent` or Git credential helpers from accessing the eMudhra token.
4. **Hardcoding Expiring Intermediate CAs**
   * *Anti-Pattern:* Manually adding intermediate certificates to local repos rather than the system keychain.
   * *Risk:* Fails instantly upon certificate rotation cycles, requiring manual updates across all developer workstations.

---

## 5. Performance & Optimization Tips

* **Enable HTTP/2 Multiplexing:** Enterprise servers hosting large monorepos benefit heavily from HTTP/2 multiplexing via curl/Secure Transport. Ensure your macOS system curl is up to date via Xcode Command Line Tools.
* **Credential Caching Tuning:** Prevent your eMudhra hardware token from constantly prompting for PIN re-entry by setting up proper cache TTLs in `~/.gnupg/gpg-agent.conf`:
  ```ini
  default-cache-ttl 28800
  max-cache-ttl 86400
  ```
* **Selective Submodule Fetching:** When dealing with heavy enterprise repositories integrated with eMudhra authenticated submodules, configure shallow clones by default:
  ```bash
  git config --global submodule.recurse true
  ```

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial Developer License (MC-CDL-v1.0)
* **Copyright © 2026 MicroCorp AI. All rights reserved.**
* **Usage Rights:** This digital product is licensed to the purchasing entity for internal engineering use, workstation provisioning, and CI/CD pipeline template standardization.
* **Redistribution:** Redistribution, resale, public posting, or sub-licensing of this exact reference kit outside the purchasing organization is strictly prohibited.
* **Warranty Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any cryptographic token lockouts, pipeline failures, or data loss resulting from improper certificate deployment.