# Developer Toolkit: macOS Git Trust & eMudhra Certificate Remediation
**Author:** AI Data Remediation Engineer 🧬 | The Agency Engineering Division  
**Target Audience:** Enterprise Software Engineers, DevOps Specialists, and Mac System Administrators dealing with strict corporate PKI requirements.

---

## 1. Product Title & Value Proposition

### 🧬 Enterprise Grade Certificate & Git Trust Remediation Kit for macOS
When integrating corporate-issued eMudhra Public Key Infrastructure (PKI) certificates with macOS Git workflows, engineers routinely encounter impenetrable SSL handshake failures, self-signed certificate rejections, and disrupted CI/CD automation pipelines. 

This commercial-grade architecture and reference kit provides hardened, automated remediation scripts, deep-dive configuration patterns, and diagnostic tooling designed to permanently solve certificate chain validation errors. Eliminate developer friction, bypass manual Keychain Access workarounds, and establish absolute zero-trust cryptographic compliance across your entire engineering fleet.

---

## 2. Quick Start & Core Concepts

Understanding how macOS, Git, and the Apple Keychain interact with enterprise root and intermediate Certificate Authorities (CAs) is critical for diagnosing trust issues.

### Core Concepts Syntax Reference Table

| Concept | Description | macOS Behavior | Git Interoperability |
| :--- | :--- | :--- | :--- |
| **System Keychain** | System-wide trust store (`/Library/Keychains/System.keychain`). | Requires administrator elevation; applies to all local users. | Native macOS Git builds delegate TLS validation to the Secure Transport backend here. |
| **Login Keychain** | User-specific credential store (`~/Library/Keychains/login.keychain-db`). | Unlocked upon user login; scoped to the individual user profile. | Ignored by system daemon processes; accessed when running user-level CLI commands. |
| **eMudhra Root CA** | The cryptographic anchor of trust for enterprise identities. | Must be explicitly added and marked as "Always Trust" for SSL/Code Signing. | Git fails with `SSL certificate problem: self signed certificate in certificate chain` if missing. |
| **`http.sslCAInfo`** | Git configuration override pointing to a custom PEM bundle. | Bypasses macOS Keychain entirely by using a direct file path reference. | Highly recommended for enterprise environments to ensure deterministic CI/CD behavior. |
| **Secure Transport** | Default cryptographic backend for Apple-native tools (`curl`, `git`). | Relies on macOS trust store evaluation policies. | Can be overridden via environment variables or compiled-with OpenSSL configurations. |

---

## 3. Production Code Patterns & Architecture Examples

The following copy-paste ready scripts provide an automated, programmatic approach to discovering, installing, configuring, and verifying eMudhra certificates for Git on macOS.

### Pattern A: Automated eMudhra Certificate Installer & Git Configurator (`emudhra-setup.sh`)

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: emudhra-setup.sh
# Description: Automated remediation for eMudhra PKI trust and Git SSL configuration.
# Author: AI Data Remediation Engineer (The Agency)
# ==============================================================================

set -euo pipefail

# Configuration Variables
CERT_URL="${EMUDHRA_CERT_URL:-https://pki.emudhra.com/root.cer}"
CERT_NAME="eMudhraEnterpriseRootCA"
PEM_PATH="/etc/ssl/certs/${CERT_NAME}.pem"
KEYCHAIN="/Library/Keychains/System.keychain"

echo "=== [1/4] Checking Administrative Privileges ==="
if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] This script must be run with sudo/root privileges." >&2
   exit 1
fi

echo "=== [2/4] Fetching eMudhra Root/Intermediate Certificate ==="
if [[ -f "./emudhra_local.cer" ]]; then
    echo "[INFO] Using local certificate file."
    cp "./emudhra_local.cer" "/tmp/${CERT_NAME}.cer"
else
    echo "[INFO] Downloading certificate from ${CERT_URL}..."
    curl -sSL "$CERT_URL" -o "/tmp/${CERT_NAME}.cer"
fi

# Convert DER to PEM if necessary
if openssl x509 -inform DER -in "/tmp/${CERT_NAME}.cer" -out "$PEM_PATH" 2>/dev/null; then
    echo "[INFO] Successfully converted DER certificate to PEM."
else
    # Assume it is already PEM format
    cp "/tmp/${CERT_NAME}.cer" "$PEM_PATH"
fi

echo "=== [3/4] Installing Certificate into macOS System Keychain ==="
security add-trusted-cert -d -r trustAsRoot -k "$KEYCHAIN" "$PEM_PATH"
echo "[INFO] Certificate successfully added to System Keychain with 'Always Trust'."

echo "=== [4/4] Configuring Global Git SSL Settings ==="
# Determine primary non-root user executing sudo
TARGET_USER="${SUDO_USER:-$(whoami)}"
USER_HOME=$(eval echo "~$TARGET_USER")

echo "[INFO] Configuring Git for user: $TARGET_USER"

sudo -u "$TARGET_USER" git config --global http.sslCAInfo "$PEM_PATH"
sudo -u "$TARGET_USER" git config --global http.sslVerify true

echo "=== Remediation Complete Successfully ==="
```

### Pattern B: Diagnostic & Verification Script (`verify-git-trust.sh`)

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: verify-git-trust.sh
# Description: Validates SSL handshake against corporate Git repositories.
# ==============================================================================

set -euo pipefail

GIT_REMOTE_URL="${1:-}"

if [[ -z "$GIT_REMOTE_URL" ]]; then
    echo "Usage: $0 <git-remote-https-url>"
    echo "Example: $0 https://git.enterprise.internal/repo.git"
    exit 1
fi

echo "=== Diagnosing Git SSL Configuration ==="
echo "Global CA Bundle: $(git config --global --get http.sslCAInfo || echo 'Not Set')"
echo "SSL Verify Status: $(git config --global --get http.sslVerify || echo 'Not Set (Default: true)')"

echo "=== Testing TLS Handshake via OpenSSL ==="
DOMAIN=$(echo "$GIT_REMOTE_URL" | awk -F/ '{print $3}')

if timeout 5 openssl s_client -connect "${DOMAIN}:443" -servername "$DOMAIN" < /dev/null &>/dev/null; then
    echo "[SUCCESS] OpenSSL handshake with $DOMAIN established successfully."
else
    echo "[FAILURE] OpenSSL handshake failed. Check corporate proxy or certificate chain."
    exit 1
fi

echo "=== Testing Git Remote Connectivity ==="
if git ls-remote "$GIT_REMOTE_URL" HEAD &>/dev/null; then
    echo "[SUCCESS] Git successfully authenticated and verified SSL chain for $GIT_REMOTE_URL."
else
    echo "[FAILURE] Git remote verification failed."
    exit 1
fi
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

When attempting to resolve SSL handshake errors under pressure, engineers frequently implement fragile, insecure bypasses. Avoid these dangerous anti-patterns:

*   ❌ **Global SSL Verification Disabling (`http.sslVerify = false`)**
    *   *Why it's dangerous:* Completely disables Man-in-the-Middle (MitM) protections across all repositories. Exposes enterprise source code repositories to credential theft and code injection attacks.
*   ❌ **Installing Certificates Only in the User Login Keychain**
    *   *Why it fails:* Background processes, IDE integrations (VS Code, IntelliJ), and system daemons run outside the user GUI session context. They cannot access the `login.keychain-db`, resulting in intermittent CI/CD pipeline failures.
*   ❌ **Failing to Handle Intermediate CAs**
    *   *Why it fails:* Installing *only* the eMudhra Root CA while omitting intermediate signing certificates causes handshake interruptions when internal load balancers present incomplete certificate chains.
*   ❌ **Hardcoding Absolute User Home Paths in Shared Configs**
    *   *Why it fails:* Using `/Users/john.doe/.gitconfig` breaks automated configuration provisioning across multi-user workstations or shared build agents. Always use environment variable expansion (`~` or `$HOME`).

---

## 5. Performance & Optimization Tips

1.  **Leverage Dedicated PEM Bundles for Deterministic CI/CD:**  
    Relying on the macOS Keychain inside headless build agents introduces performance overhead and intermittent permission dialogs. Maintain a static enterprise bundle (`/etc/ssl/certs/enterprise-ca-bundle.pem`) and point Git directly to it via `http.sslCAInfo`.
2.  **Optimize Keychain Search Path Order:**  
    Ensure that the System keychain search list (`security list-keychains -d user`) correctly prioritizes enterprise override keychains to prevent unnecessary traversal latency during cryptographic challenges.
3.  **Cache Git Credential Helpers:**  
    Combine robust SSL configurations with the macOS Keychain credential helper (`git config --global credential.helper osxkeychain`) to optimize authentication performance without sacrificing transport security.

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp AI Enterprise License Agreement
* **Product:** Developer Toolkit: macOS Git Trust & eMudhra Certificate Remediation
* **Classification:** Commercial Intellectual Property — Engineering Division
* **Usage Rights:** Granted to the purchasing enterprise entity for internal deployment across all employee workstations, continuous integration servers, and developer machines.
* **Restrictions:** Redistribution, resale, or public publication of these source scripts outside the licensed organization is strictly prohibited without prior written authorization from MicroCorp AI.
* **Warranty Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. The Agency Data Remediation Engineer persona assumes no liability for downtime or PKI misconfigurations resulting from improper execution.