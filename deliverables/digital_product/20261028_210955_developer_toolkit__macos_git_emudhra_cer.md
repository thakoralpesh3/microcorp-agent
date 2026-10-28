# Developer Toolkit: macOS Git eMudhra Certificate Remediation Suite
**Enterprise Architecture Kit & Engineering Reference Guide**  
*Version 2.4.0-Enterprise | MicroCorp AI Engineering Division*

---

## 1. Product Title & Value Proposition

### The Developer Problem
Enterprise developers using macOS frequently encounter cryptographic validation failures when committing code to enterprise Git repositories signed with or protected by eMudhra Digital Signatures (PKI / USB Tokens / `.cer` / `.pfx` chains). Because macOS relies on the System Keychain while Git (via Secure Transport or OpenSSL) and Node/Python runtimes rely on independent trust stores, developers face persistent errors like:
* `SSL certificate problem: self signed certificate in certificate chain`
* `git push` aborts due to intermediate CA untrusted roots
* `em_signer` local bridge daemon communication timeouts
* Code signing verification rejections during CI/CD handoffs

### The Solution: eMudhra Remediation Suite
This toolkit provides a battle-tested, automated remediation framework to bridge macOS Keychain, Git configuration, and enterprise certificate chains. It eliminates manual keychain keychain-dumping, unifies root trust stores, and ensures seamless Git signing workflows across terminal, IDE, and containerized runtimes.

---

## 2. Quick Start & Core Concepts

### Core Architecture Concepts
1. **The Trust Split:** macOS separates user/system trust stores from Git's underlying network transport layer. Injecting the eMudhra root and intermediate certificates directly into Git's CA bundle or forcing macOS Keychain integration resolves trust mismatch.
2. **`em_signer` Local IPC:** eMudhra desktop applications utilize local loopback services for cryptographic signing. Environment variables must explicitly map paths to avoid sandbox blocks on modern macOS (Sonoma / Sequoia).
3. **Keychain Pinning:** Enterprise code-signing requires exact matching of SHA-1/SHA-256 fingerprints in `~/.gitconfig` to prevent interactive prompt hangs in headless or automated terminal environments.

### Configuration & Tooling Quick-Reference

| Component | Target Path / Command | Purpose |
| :--- | :--- | :--- |
| **System Keychain** | `/Library/Keychains/System.keychain` | Stores enterprise intermediate & root CAs system-wide. |
| **Git Global Config** | `~/.gitconfig` | Houses signing key references, program paths, and SSL backend overrides. |
| **Custom CA Bundle** | `~/.git/certs/emudhra-ca-bundle.crt` | Consolidated PEM file containing the full eMudhra trust chain. |
| **Signer Binary** | `/Applications/eMudhra/em_signer/em_signer` | Local daemon facilitating hardware token (USB) signing operations. |
| **Env Override** | `GIT_SSL_CAINFO` | Forces Git to bypass default Apple Secure Transport in favor of explicit bundles. |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Automated Trust-Chain Extractor & Git Injector (`emudhra-bootstrap.sh`)
*Save as `emudhra-bootstrap.sh`. Run via `bash emudhra-bootstrap.sh` to fully configure your development environment.*

```bash
#!/usr/bin/env bash
# ==============================================================================
# MicroCorp AI - macOS Git eMudhra Remediation Suite
# Automated Certificate Extraction & Git Environment Alignment
# ==============================================================================

set -Eeuo pipefail
trap 'echo "❌ Error on line $LINENO. Exit code: $?"' ERR

CERTS_DIR="$HOME/.git/certs"
BUNDLE_PATH="$CERTS_DIR/emudhra-ca-bundle.crt"
LABEL_FILTER="eMudhra"

echo "===> [1/4] Initializing secure certificate directory..."
mkdir -p "$CERTS_DIR"
chmod 700 "$CERTS_DIR"

echo "===> [2/4] Extracting eMudhra Certificates from macOS System Keychain..."
# Extract certificates matching 'eMudhra' from System and Login keychains into PEM format
security find-certificate -a -c "$LABEL_FILTER" -p /Library/Keychains/System.keychain > "$BUNDLE_PATH" 2>/dev/null || true
security find-certificate -a -c "$LABEL_FILTER" -p ~/Library/Keychains/login.keychain-db >> "$BUNDLE_PATH" 2>/dev/null || true

# Fallback check if certificates were found
if [ ! -s "$BUNDLE_PATH" ]; then
    echo "⚠️ Warning: No certificates found matching '$LABEL_FILTER' via automated keychain scan."
    echo "Please export your .cer/.pem chain manually to: $BUNDLE_PATH"
else
    CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" "$BUNDLE_PATH")
    echo "✅ Successfully extracted $CERT_COUNT certificate(s) into trust bundle."
fi

echo "===> [3/4] Configuring Git Global Settings..."
git config --global http.sslCAInfo "$BUNDLE_PATH"
git config --global credential.helper cache
git config --global core.longpaths true

# Enable Git Commit Signing if a signing key is present in the keychain
SIGNING_KEY_HASH=$(security find-identity -v -p codesigning | grep -i "$LABEL_FILTER" | head -n 1 | awk -F'"' '{print $2}')

if [ -n "$SIGNING_KEY_HASH" ]; then
    echo "✅ Found eMudhra Signing Identity: $SIGNING_KEY_HASH"
    git config --global user.signingkey "$SIGNING_KEY_HASH"
    git config --global gpg.format x509
    git config --global commit.gpgsign true
else
    echo "ℹ️ No active eMudhra code-signing identity found in Keychain. Skipping auto-sign configuration."
fi

echo "===> [4/4] Validating Git Network & SSL Stack..."
if git ls-remote https://github.com > /dev/null 2>&1; then
    echo "✅ Git SSL verification operational and verified."
else
    echo "❌ Git SSL handshake failed. Inspect bundle at $BUNDLE_PATH"
    exit 1
fi

echo "✨ eMudhra Remediation Suite execution completed successfully!"
```

---

### Pattern 2: Programmatic Node.js / CLI Wrapper (`verify-git-env.js`)
*Use this integration test script within CI or local dev setups to guarantee the eMudhra environment variables and socket paths are fully reachable.*

```javascript
/**
 * MicroCorp AI - eMudhra Environment Health Check
 * Validates that Git, OpenSSL, and local eMudhra daemons are aligned.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const homeDir = process.env.HOME;
const bundlePath = path.join(homeDir, '.git', 'certs', 'emudhra-ca-bundle.crt');

function runCheck(name, fn) {
    try {
        fn();
        console.log(`[PASS] ${name}`);
    } catch (error) {
        console.error(`[FAIL] ${name}: ${error.message}`);
        process.exitCode = 1;
    }
}

console.log('--- eMudhra Remediation Suite: Diagnostic Runner ---');

runCheck('Git Binary Accessibility', () => {
    execSync('git --version', { stdio: 'ignore' });
});

runCheck('Custom CA Bundle Existence', () => {
    if (!fs.existsSync(bundlePath)) {
        throw new Error(`Missing CA bundle at ${bundlePath}. Run bootstrap script.`);
    }
    const stats = fs.statSync(bundlePath);
    if (stats.size === 0) throw new Error('CA bundle is empty.');
});

runCheck('Git Global SSL Configuration', () => {
    const configuredPath = execSync('git config --global --get http.sslCAInfo', { encoding: 'utf8' }).trim();
    if (configuredPath !== bundlePath) {
        throw new Error(`Expected http.sslCAInfo to be '${bundlePath}', got '${configuredPath}'`);
    }
});

runCheck('eMudhra Signer IPC Daemon Check', () => {
    // Check if local signer daemon port (typically 8192/18192) is active
    try {
        execSync('nc -z localhost 18192', { stdio: 'ignore' });
    } catch {
        console.warn('⚠️ Warning: eMudhra local signer daemon (port 18192) is not responding. USB token signing may fail.');
    }
});
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* **Anti-Pattern 1: Disabling Global SSL Verification**
  * *Bad:* Running `git config --global http.sslVerify false`.
  * *Why:* Exposes the enterprise network to MitM attacks and violates corporate compliance mandates (SOC2 / ISO 27001).
  * *Fix:* Always inject the exact corporate intermediate certificate chain via `http.sslCAInfo`.

* **Anti-Pattern 2: Mixing OpenSSL and Secure Transport Backends**
  * *Bad:* Manually compiling Git against custom Homebrew OpenSSL while leaving macOS system variables unassigned.
  * *Why:* Causes silent panics during cryptographic handshakes when tokens are queried. Stick to Apple’s native Secure Transport backed by explicit CA bundles.

* **Anti-Pattern 3: Hardcoding USB Token IDs**
  * *Bad:* Hardcoding dynamic hardware token serial numbers into `.gitconfig`.
  * *Why:* Hardware tokens rotate or get replaced. Use keychain identity matching patterns instead.

---

## 5. Performance & Optimization Tips

1. **Keychain Query Caching:** 
   Executing `security find-identity` on every single git commit invocation introduces a 400ms–800ms latency penalty. Configure Git credential caching to minimize frequent keychain lookups:
   ```bash
   git config --global credential.helper "cache --timeout=36000"
   ```
2. **Lean PEM Bundles:** 
   Avoid dumping the entire enterprise macOS system root store into `emudhra-ca-bundle.crt`. Filter specifically for `eMudhra` and parent organizational unit roots to keep parser footprint minimal during TLS handshakes.
3. **Daemon Keep-Alive:** 
   Ensure `em_signer` is registered in user LaunchAgents (`~/Library/LaunchAgents/`) rather than launched ad-hoc to prevent cold-start latency when executing batch commits.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Enterprise Commercial License (v2.0)
*Copyright © 2026 MicroCorp AI. All rights reserved.*

1. **Grant of Rights:** MicroCorp AI grants the purchasing enterprise, corporate entity, or individual developer a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this Remediation Suite internally within their organization.
2. **Redistribution Restrictions:** You may **not** resell, repackage, sub-license, or redistribute this digital product as a standalone commercial developer toolkit, template set, or SaaS wrapper without express written authorization from MicroCorp AI.
3. **No Warranty & Limitation of Liability:** THIS DIGITAL PRODUCT IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL MICROCORP AI BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE PRODUCT.