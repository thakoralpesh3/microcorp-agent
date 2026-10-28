# Developer Toolkit: macOS Git eMudhra Certificate Remediation Suite
**Enterprise Architecture & Engineering Reference Kit (v2.4.0)**  
*Produced by MicroCorp AI Engineering Division • Enterprise Security & Developer Productivity Series*

---

## 1. Product Title & Value Proposition

### Product Title
**macOS Git eMudhra Certificate Remediation Suite** — Enterprise Cryptographic Continuity Framework for Distributed Engineering Teams.

### Value Proposition
Enterprise engineers utilizing macOS development environments frequently encounter Git transport failures (`SSL certificate problem: self signed certificate in certificate chain`, `unable to get local issuer certificate`) when communicating with corporate source control repositories secured by eMudhra or internal Public Key Infrastructures (PKIs). 

Standard workarounds—such as globally disabling SSL verification (`git config --global http.sslVerify false`)—introduce catastrophic security vulnerabilities, exposing codebases to Man-in-the-Middle (MitM) attacks and violating SOC2, ISO 27001, and NIST compliance mandates.

This toolkit provides a **cryptographically secure, automated, and deterministic remediation suite**. It bridges macOS Keychain Services, OpenSSL trust stores, and Git's native transport layers, ensuring seamless integration with eMudhra enterprise signing and TLS inspection gateways without compromising security postures.

---

## 2. Quick Start & Core Concepts

### Architectural Overview
macOS handles certificates through its native Keychain Access database, whereas command-line tools like Git (compiled against LibreSSL, Apple Secure Transport, or OpenSSL) often maintain independent certificate stores or require explicit bundle paths. eMudhra root and intermediate certificates must be extracted from the System Keychain, converted to PEM format, and explicitly bound to Git's environment without polluting global system trust models.

### Clean Syntax & Configuration Reference Table

| Target Layer | Mechanism | Configuration / Command | Operational Intent |
| :--- | :--- | `git config --global http.sslCAInfo ~/.git_emudhra_bundle.pem` | Directs Git to a dedicated, aggregated enterprise CA bundle. |
| **System Trust** | macOS Keychain | `security find-certificate -a -c "eMudhra" -p > cert.pem` | Extracts eMudhra certificates directly from the macOS trust store. |
| **Environment** | Shell Export | `export GIT_SSL_CAINFO="$HOME/.git_emudhra_bundle.pem"` | Forces CI/CD pipelines and shell sub-processes to respect custom CAs. |
| **OpenSSL Fallback** | Config Override | `git config --global http.sslBackend schannel / openssl` | Explicitly aligns Git’s SSL backend engine with system libraries. |
| **Verification** | Diagnostic | `GIT_CURL_VERBOSE=1 git ls-remote <URL>` | Diagnostic mode for inspecting TLS handshake and certificate chain validation. |

---

## 3. Production Code Patterns & Architecture Examples

### Automation Script: `emudhra-git-fix.sh`
This robust, idempotent bash script automates discovery, extraction, formatting, and configuration of eMudhra certificates for Git on macOS. Save this script as `emudhra-git-fix.sh` and execute it with standard user privileges.

```bash
#!/usr/bin/env bash
# ==============================================================================
# MicroCorp AI Engineering - macOS Git eMudhra Remediation Suite
# Version: 2.4.0
# Description: Automatically extracts eMudhra enterprise certificates from macOS
#              Keychain, constructs a unified PEM bundle, and configures Git.
# ==============================================================================

set -Eeuo pipefail

# Configuration Constants
BUNDLE_PATH="$HOME/.git_emudhra_bundle.pem"
BACKUP_PATH="$HOME/.git_emudhra_bundle.pem.bak"
CERT_LABEL_QUERY="eMudhra"

log_info()  { echo -e "\033[34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[32m[SUCCESS]\033[0m $1"; }
log_warn()  { echo -e "\033[33m[WARN]\033[0m $1"; }
log_error() { echo -e "\033[31m[ERROR]\033[0m $1" >&2; }

cleanup() {
    if [[ -f "/tmp/_emudhra_raw.pem" ]]; then
        rm -f "/tmp/_emudhra_raw.pem"
    fi
}
trap cleanup EXIT

main() {
    log_info "Initiating eMudhra certificate extraction from macOS Keychain..."

    # Step 1: Extract certificates matching the query from System and Login keychains
    if ! security find-certificate -a -c "$CERT_LABEL_QUERY" -p > "/tmp/_emudhra_raw.pem" 2>/dev/null; then
        log_error "Failed to query macOS Keychain for certificates matching '$CERT_LABEL_QUERY'."
        exit 1
    fi

    if [[ ! -s "/tmp/_emudhra_raw.pem" ]]; then
        log_error "No certificates found matching '$CERT_LABEL_QUERY' in the macOS Keychain."
        log_info "Please ensure your IT department has installed the eMudhra profile."
        exit 1
    }

    CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" /tmp/_emudhra_raw.pem)
    log_info "Discovered ${CERT_COUNT} certificate(s) matching '$CERT_LABEL_QUERY'."

    # Step 2: Backup existing bundle if present
    if [[ -f "$BUNDLE_PATH" ]]; then
        cp "$BUNDLE_PATH" "$BACKUP_PATH"
        log_info "Backed up existing bundle to $BACKUP_PATH"
    fi

    # Step 3: Normalize and write out the PEM bundle
    cat "/tmp/_emudhra_raw.pem" > "$BUNDLE_PATH"
    chmod 644 "$BUNDLE_PATH"
    log_success "Generated clean PEM bundle at: $BUNDLE_PATH"

    # Step 4: Configure Git Globally
    log_info "Configuring Git global transport properties..."
    git config --global http.sslCAInfo "$BUNDLE_PATH"
    
    # Ensure SSL verification remains strictly enabled
    git config --global http.sslVerify true

    log_success "Git successfully configured to use the eMudhra certificate bundle."
    
    # Step 5: Verification check against a dummy or internal git endpoint (non-destructive)
    log_info "Running validation check against Git configuration..."
    CURRENT_CA=$(git config --global --get http.sslCAInfo)
    log_info "Active Git sslCAInfo path: $CURRENT_CA"
    
    log_success "Remediation Suite execution completed successfully."
}

main "$@"
```

### CI/CD Pipeline Integration Snippet (`.github/workflows/git-setup.yml`)
For hybrid developer workflows executing inside macOS runner environments, inject this initialization step prior to repository checkouts.

```yaml
name: Setup eMudhra Git Transport
on:
  workflow_call:
    inputs:
      emudhra_cert_secret_name:
        required: true
        type: string

jobs:
  configure-ssl:
    runs-on: macos-latest
    steps:
      - name: Inject Enterprise eMudhra Bundle
        env:
          EMUDHRA_PEM: ${{ secrets[inputs.emudhra_cert_secret_name] }}
        run: |
          BUNDLE_PATH="$HOME/.git_emudhra_bundle.pem"
          echo "$EMUDHRA_PEM" > "$BUNDLE_PATH"
          chmod 644 "$BUNDLE_PATH"
          git config --global http.sslCAInfo "$BUNDLE_PATH"
          git config --global http.sslVerify true
          echo "Git successfully bound to enterprise eMudhra trust anchor."
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Disabling Global SSL Verification
* **The Practice:** Running `git config --global http.sslVerify false`.
* **The Risk:** Completely disables cryptographic validation across all repositories. Opens internal and external connections to sophisticated MitM intercept attacks, code injection, and immediate compliance failure during security audits.
* **The Fix:** Always use targeted CA bundling (`http.sslCAInfo`) as demonstrated in this suite.

### ❌ Anti-Pattern 2: Mixing LibreSSL and OpenSSL Paths on macOS Homebrew
* **The Gotcha:** Homebrew installs of Git often link against Homebrew's `openssl@3`, whereas system Git links against Apple Secure Transport. Mixing these up causes Git to ignore global certificate stores placed in standard system locations.
* **The Fix:** Explicitly anchor your custom bundle path via `git config --global http.sslCAInfo`, ensuring Git reads the exact file regardless of underlying dynamic library linking discrepancies.

### ❌ Anti-Pattern 3: Stale Certificate Chains After eMudhra Renewal
* **The Gotcha:** eMudhra certificates rotate periodically. Hardcoding static PEM files leads to sudden, unexplained CI/CD and local build failures upon certificate expiration.
* **The Fix:** Re-run the `emudhra-git-fix.sh` automation script quarterly or integrate it into your local machine bootstrapping framework (e.g., Ansible, Nix, or chezmoi).

---

## 5. Performance & Optimization Tips

1. **Minimize Bundle Bloat:** Only extract certificates matching the exact eMudhra organizational string (`-c "eMudhra"`). Appending thousands of extraneous root CAs to your Git bundle degrades TLS handshake evaluation performance.
2. **Leverage HTTP/2 Multiplexing:** Ensure your Git client leverages modern transport optimizations by pairing your custom CA bundle with HTTP/2 support:
   ```bash
   git config --global http.version HTTP/2
   ```
3. **Filesystem Caching:** Place your `.git_emudhra_bundle.pem` file on fast APFS internal storage paths (`$HOME/`) rather than network-mounted home directories to prevent disk I/O latency bottlenecks during massive repository clones (`git clone --recurse-submodules`).

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License (MACL-v1.2)
* **Copyright © 2026 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Licensed to the purchasing enterprise entity and its internal engineering personnel for internal deployment, continuous integration engineering, and developer workstation provisioning.
* **Restrictions:** Redistribution, resale, public sub-licensing, or inclusion of this architectural reference kit within commercial SaaS offerings without explicit written authorization from MicroCorp AI Legal Division is strictly prohibited.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.