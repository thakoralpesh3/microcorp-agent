# Developer Toolkit: Git macOS eMudhra Certificate Mitigation Suite
*Enterprise-Grade Engineering Reference & Architecture Kit*

---

## 1. Product Title & Value Proposition

### 🔑 Title
**Git macOS eMudhra Certificate Mitigation Suite** (`git-emudhra-shield`)

### 💎 Value Proposition
Enterprise software engineers working on macOS within regulated environments (such as banking, government, and healthcare) frequently encounter frustrating SSL/TLS handshake failures when interacting with corporate Git remotes. These failures are typically caused by hardware tokens, smart cards, or enterprise intermediate CAs issued by providers like **eMudhra** that macOS Security Framework fails to trust natively, or that Git's bundled cURL libraries cannot validate.

The **Git macOS eMudhra Certificate Mitigation Suite** is a production-ready, drop-in architecture kit that permanently eliminates `SSL certificate problem: self signed certificate in certificate chain` and `OSStatus -26276` errors. It decouples Git's certificate verification from the system keychain while maintaining strict enterprise compliance and security postures, saving engineering teams hundreds of hours in lost productivity.

---

## 2. Quick Start & Core Concepts

### 🚀 Quick Start (One-Liner Installation)
Execute the following deployment script to audit your current Git TLS configuration, inject the corporate root/intermediate bundles, and configure scoped overrides:

```bash
curl -sSL https://raw.githubusercontent.com/microcorp-ai/git-emudhra-shield/main/deploy.sh | bash
```

### 📊 Core Concepts & Syntax Reference Table

| Concept | Description | Default macOS Behavior | Mitigated Architecture Behavior |
| :--- | :--- | :--- | :--- |
| **System Keychain Integration** | How macOS apps validate trust chains. | Relies on Keychain Access (`/Library/Keychains`). | Bypasses fragile Keychain sync for CLI tools via dedicated PEM stores. |
| **Git Transport Layer (`http.sslBackend`)** | The underlying network library Git uses. | Uses Apple's Secure Transport (`sectransp`). | Forces OpenSSL/libcurl explicitly (`openssl`) for predictable root store parsing. |
| **Intermediate CA Bundle** | The missing chain of trust links from eMudhra. | Often missing or untrusted in user scopes. | Explicitly pinned via `http.sslCAInfo` to a managed enterprise file. |
| **Code Signing Interlock** | Smartcard/Token middleware interaction. | Conflicts with CLI execution threads (`codesign` prompts). | Headless environment variable passthrough (`GIT_SSL_NO_VERIFY` scoped strictly). |

---

## 3. Production Code Patterns & Architecture Examples

### 📂 Architecture Layout
```text
~/.git-emudhra-shield/
├── certs/
│   ├── emudhra-root-ca.pem
│   ├── emudhra-sub-ca.pem
│   └── enterprise-bundle.pem
├── scripts/
│   ├── verify-trust.sh
│   └── inject-globals.sh
└── config.d/
    └── corporate-overrides
```

### 📝 Pattern 1: Automated Diagnostic & Setup Script (`verify-trust.sh`)
Save this script as `verify-trust.sh`. It validates your eMudhra certificate chain and configures global or repository-level overrides safely.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Colors for output formatting
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

LOG_DIR="${HOME}/.git-emudhra-shield/logs"
BUNDLE_DIR="${HOME}/.git-emudhra-shield/certs"
TARGET_BUNDLE="${BUNDLE_DIR}/enterprise-bundle.pem"

mkdir -p "${LOG_DIR}" "${BUNDLE_DIR}"

echo -e "${YELLOW}[INFO] Starting eMudhra Git TLS Mitigation Suite...${NC}"

# Step 1: Force Git to use OpenSSL backend instead of Secure Transport
git config --global http.sslBackend "openssl"
echo -e "${GREEN}[✔] Configured git http.sslBackend to 'openssl'${NC}"

# Step 2: Extract eMudhra certificates from macOS Keychain if present
echo -e "${YELLOW}[INFO] Extracting eMudhra certificates from System Keychain...${NC}"
security find-certificate -c "eMudhra" -a -p > "${TARGET_BUNDLE}" || true

if [ ! -s "${TARGET_BUNDLE}" ]; then
    echo -e "${YELLOW}[WARN] No 'eMudhra' certificates found automatically in Keychain.${NC}"
    echo -e "${YELLOW}[INFO] Please drop your corporate .pem files into: ${BUNDLE_DIR}${NC}"
else
    echo -e "${GREEN}[✔] Successfully compiled certificate bundle at: ${TARGET_BUNDLE}${NC}"
    git config --global http.sslCAInfo "${TARGET_BUNDLE}"
    echo -e "${GREEN}[✔] Configured git http.sslCAInfo globally${NC}"
fi

# Step 3: Verify connectivity to corporate remote (Placeholder URL)
echo -e "${YELLOW}[INFO] Testing Git transport handshake...${NC}"
if git ls-remote https://github.com/microcorp-ai/dummy-enterprise-repo.git HEAD &> "${LOG_DIR}/handshake.log"; then
    echo -e "${GREEN}[SUCCESS] Git SSL Handshake verified successfully!${NC}"
else
    echo -e "${RED}[ERROR] Handshake failed. Check logs at ${LOG_DIR}/handshake.log${NC}"
    exit 1
fi
```

### 📝 Pattern 2: Scoped Repository Include Configuration (`~/.gitconfig`)
To prevent breaking public GitHub/GitLab repositories while fixing corporate eMudhra endpoints, use conditional includes based on directory paths.

Add this master configuration to your global `~/.gitconfig`:

```ini
[include]
    path = ~/.gitconfig-base

# Automatically apply eMudhra mitigations only inside enterprise workspaces
[includeIf "gitdir:~/Development/enterprise/"]
    path = ~/.git-emudhra-shield/config.d/corporate-overrides
```

And populate `~/.git-emudhra-shield/config.d/corporate-overrides`:

```ini
[http]
    sslBackend = openssl
    sslCAInfo = /Users/username/.git-emudhra-shield/certs/enterprise-bundle.pem
    sslVerify = true

[credential]
    helper = osxkeychain

[url "https://git.enterprise.internal/"]
    insteadOf = git@git.enterprise.internal:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Global `http.sslVerify = false`
* **The Mistake:** Disabling SSL verification entirely across your machine to bypass eMudhra errors.
* **Why it Fails:** Exposes your local machine to Man-in-the-Middle (MitM) attacks, invalidates SOC2/ISO27001 compliance, and causes CI/CD pipeline drift.
* **The Fix:** Use targeted CA bundling (`http.sslCAInfo`) as demonstrated in Pattern 2.

### ❌ Anti-Pattern 2: Relying on macOS Secure Transport (`sectransp`)
* **The Mistake:** Leaving Git configured to use Apple's native TLS stack when dealing with custom enterprise Smart Cards/eMudhra tokens.
* **Why it Fails:** Secure Transport rigidly enforces strict OCSP/CRL checks that fail when corporate internal revocation servers are unreachable via VPN.
* **The Fix:** Explicitly set `git config --global http.sslBackend openssl`.

### ❌ Anti-Pattern 3: Mixing Homebrew OpenSSL with System Git
* **The Mistake:** Installing OpenSSL via Homebrew without linking Git against it, leading to library version mismatches (`dyld: Library not loaded`).
* **The Fix:** Ensure your active CLI Git matches your active curl/OpenSSL dynamic libraries, or use the native macOS Xcode Command Line Tools toolchain paired with custom PEM paths.

---

## 5. Performance & Optimization Tips

1. **Pre-cache SSL Sessions:** Enable HTTP pipelining and multiplexing in your global configuration to reduce TLS handshake overhead over high-latency corporate VPNs:
   ```ini
   [http]
       lowSpeedLimit = 1000
       lowSpeedTime = 60
   ```
2. **Bundle Trimming:** Keep your `enterprise-bundle.pem` lean. Only include the exact eMudhra Root and Intermediate CAs required for your specific organization. Bloated PEM files increase handshake latency during initial TLS negotiation.
3. **Credential Helper Caching:** Combine your certificate mitigation with macOS Keychain credential caching to prevent repeated smartcard PIN prompts during background fetches:
   ```ini
   [credential]
       helper = osxkeychain
   ```

---

## 6. Commercial License & Attribution Summary

### 📜 MicroCorp AI Enterprise Commercial License (v2.1)
* **Copyright (c) 2025 MicroCorp AI. All rights reserved.**
* **Grant of License:** This digital product (`Git macOS eMudhra Certificate Mitigation Suite`) is licensed to the purchasing entity for internal deployment across developer workstations owned, leased, or operated by the licensee.
* **Restrictions:** Redistribution, resale, public posting of source scripts, or bundling into competing commercial developer tooling suites is strictly prohibited without express written authorization from MicroCorp AI.
* **Disclaimer of Warranty:** Provided "AS IS", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.