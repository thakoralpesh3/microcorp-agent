# Developer Toolkit: Protecting SSH Keys with macOS Secure Enclave

## 1. Product Title & Value Proposition

### 🔑 Hardware-Backed SSH Authentication on macOS
Eliminate the risk of stolen private keys. This production-ready architecture kit enables you to bind your SSH identity directly to the **Apple Secure Enclave** (Apple Silicon M1/M2/M3/M4 or Intel T2 chips), requiring biometric verification (Touch ID) or your device PIN for every single SSH signing or authentication challenge.

```
+-----------------------------------------------------------------+
|                       macOS Client Host                         |
|                                                                 |
|  [ git push / ssh ]                                             |
|         │                                                       |
|         ▼                                                       |
|  [ OpenSSH Client (ssh-agent) ]                                 |
|         │                                                       |
|         ▼ (PKCS#11 Provider Bridge)                             |
|  [ libsk-client.dylib ]                                         |
|         │                                                       |
|         ▼ (OS Security Framework)                               |
|  +-----------------------------------------------------------+  |
|  |                   Apple Secure Enclave                     |  |
|  |      [ Private Key (Non-Exportable Hardware ECC/RSA) ]    |  |
|  +-----------------------------------------------------------+  |
|                               │ (Biometric Touch ID Prompt)     |
|                               ▼                                 |
|                    [ User Presence Check ]                      |
+-----------------------------------------------------------------+
```

### Why Your Engineering Team Needs This
* **Zero Key Exportability:** Private keys generated within the Secure Enclave physically cannot be read, dumped, or exfiltrated from the chip, even via kernel exploits or root-level malware.
* **Hardware-Enforced Presence:** Every SSH connection or Git commit signing demands active Touch ID or Mac login password confirmation.
* **FIPS & Compliance Ready:** Satisfies stringent enterprise security baselines (SOC2, ISO 27001, NIST SP 800-63B) requiring hardware token (FIDO2/U2F-equivalent) bindings for developer access.
* **Drop-in OpenSSH Compatibility:** Integrates natively with OpenSSH 8.2+ via standard PKCS#11 / FIDO2 security key (`-t ecdsa-sk` / `-t ed25519-sk`) interfaces.

---

## 2. Quick Start & Core Concepts

### Prerequisites & Compatibility Matrix
* **Hardware:** Apple Silicon (M1, M2, M3, M4 series) or Intel Mac equipped with a T2 Security Chip.
* **OS Version:** macOS Ventura (13.x) or macOS Sonoma / Sequoia (14.x / 15.x).
* **Software:** OpenSSH version `8.2` or higher (run `ssh -V` to verify).

### Core Syntax & Command Reference

| Action / Verb | Command Syntax | Description & Expected Outcome |
| :--- | :--- | :--- |
| **Check Support** | `ssh -Q key` | Lists supported key types. Look for `ecdsa-sk` and `ed25519-sk`. |
| **Generate Key** | `ssh-keygen -t ecdsa-sk -a 100 -N "" -f ~/.ssh/id_ecdsa_sk` | Generates a resident hardware-backed key pair tied to the Secure Enclave. |
| **Add to Agent** | `ssh-add --apple-use-keychain ~/.ssh/id_ecdsa_sk` | Loads the key stub into `ssh-agent` and saves reference to macOS Keychain. |
| **List Keys** | `ssh-add -l -E sha256` | Displays loaded keys with fingerprints, confirming `sk` designation. |
| **Test Connection** | `ssh -Tv git@github.com` | Verifies end-to-end authentication with verbose logging. |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Automated Provisioning Script (`setup-secure-enclave-ssh.sh`)
Save this script as `setup-ssh.sh`. It enforces idempotency, validates prerequisites, generates the key with Touch ID binding, and configures your local SSH client.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: setup-secure-enclave-ssh.sh
# Description: Provisions a Hardware-Backed Secure Enclave SSH Key on macOS
# Author: MicroCorp AI Developer Tooling Engineering
# ==============================================================================

set -Eeuo pipefail

KEY_PATH="${HOME}/.ssh/id_ecdsa_enclave"
KEY_COMMENT="${USER}@$(sc-get-host-name 2>/dev/null || hostname)"

echo "==> [1/5] Validating environment and OpenSSH version..."
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This automation is strictly for macOS systems." >&2
    echo "Next Step: Run this script on a macOS host with a Secure Enclave." >&2
    exit 1
fi

SSH_VERSION=$(ssh -V 2>&1 | awk '{print $1}' | cut -d'_' -f2 | cut -d'p' -f1)
REQUIRED_VERSION="8.2"

# Simple numeric version comparison check
if awk "BEGIN {exit !($SSH_VERSION < $REQUIRED_VERSION)}"; then
    echo "Error: OpenSSH version ${SSH_VERSION} is outdated. Version >= ${REQUIRED_VERSION} required." >&2
    echo "Next Step: Upgrade OpenSSH via Homebrew: brew install openssh" >&2
    exit 1
fi

echo "==> [2/5] Checking for existing Secure Enclave key at ${KEY_PATH}..."
if [[ -f "${KEY_PATH}" ]]; then
    echo "Notice: Key already exists at ${KEY_PATH}." >&2
    echo "Next Step: Delete or backup existing key before re-running, or skip to ssh-add." >&2
    exit 0
fi

echo "==> [3/5] Generating FIDO2/Secure Enclave ECDSA key..."
echo "ℹ️  NOTE: Touch ID prompt will appear. Place your finger on the sensor."

# -t ecdsa-sk: Creates a security-key backed ECDSA key (Curve NIST P-256)
# -O resident: Makes it resident (optional, enables key retrieval from hardware)
# -O verify-required: Forces explicit user verification (Touch ID) for every use
ssh-keygen \
    -t ecdsa-sk \
    -a 100 \
    -b 256 \
    -C "${KEY_COMMENT}" \
    -O application=ssh:secure-enclave \
    -O verify-required \
    -f "${KEY_PATH}"

echo "==> [4/5] Configuring ~/.ssh/config for automatic Keychain integration..."
CONFIG_FILE="${HOME}/.ssh/config"
touch "${CONFIG_FILE}"
chmod 600 "${CONFIG_FILE}"

# Check if Block already exists to prevent duplication
if ! grep -q "Host github.com" "${CONFIG_FILE}"; then
    cat << 'EOF' >> "${CONFIG_FILE}"

# --- MicroCorp AI Secure Enclave SSH Configuration ---
Host *
  AddKeysToAgent yes
  UseKeychain yes

Host github.com
  IdentityFile ~/.ssh/id_ecdsa_enclave
  IdentitiesOnly yes
EOF
    echo "Added default configuration blocks to ${CONFIG_FILE}"
else
    echo "SSH config already contains host rules; skipping append."
fi

echo "==> [5/5] Registering key with ssh-agent and macOS Keychain..."
eval "$(ssh-agent -s)" >/dev/null
ssh-add --apple-use-keychain "${KEY_PATH}"

echo "=============================================================================="
echo "SUCCESS: Secure Enclave SSH Key created and configured!"
echo "Your Public Key is below. Copy and paste this into GitHub / GitLab / Bitbucket:"
echo "------------------------------------------------------------------------------"
cat "${KEY_PATH}.pub"
echo "=============================================================================="
```

### Pattern 2: Enterprise `~/.ssh/config` Best Practices Template
Place this in `~/.ssh/config` to harden all outbound SSH connections, ensuring strict key isolation and persistent agent management across terminal sessions.

```ini
# ==============================================================================
# Enterprise SSH Configuration Template
# Enforces Secure Enclave Identity isolation and prevents key-stuffing attacks
# ==============================================================================

Host *
    # Force ssh-agent to store credentials securely in macOS Keychain
    AddKeysToAgent yes
    UseKeychain yes
    
    # Prevent SSH-agent forwarding to remote compromised hosts (Bastion safety)
    ForwardAgent no
    
    # Restrict authentication attempts to prevent brute-force triggers
    NumberOfPasswordPrompts 1
    ServerAliveInterval 60
    ServerAliveCountMax 30

# Production GitHub / GitLab Profile Mapping
Host github.com gitlab.com
    User git
    IdentitiesOnly yes
    IdentityFile ~/.ssh/id_ecdsa_enclave
    # Ensures macOS uses the hardware token provider explicitly
    SecurityKeyProvider internal
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Patterns & Bad Habits | Why It Fails | The Correct Engineering Approach |
| :--- | :--- | :--- |
| **❌ Using legacy RSA keys (`ssh-keygen -t rsa -b 4096`)** | RSA mathematically cannot be bound to the Secure Enclave hardware chip; keys remain exportable file blobs on disk. | Always use hardware-token parameters: `-t ecdsa-sk` or `-t ed25519-sk`. |
| **❌ Omitting `-O verify-required`** | Without explicit verification flags, keys might be used silently without requiring Touch ID validation in automated background shells. | Explicitly pass `-O verify-required` during generation to enforce biometric challenges. |
| **❌ Moving `id_ecdsa_enclave` to a new Mac** | Secure Enclave keys are permanently married to the physical silicon chip of the device where they were generated. They cannot be migrated. | Treat keys as ephemeral hardware credentials. Re-run your provisioning script on each new developer workstation. |
| **❌ Forgetting `AddKeysToAgent yes` in `~/.ssh/config`** | macOS will fail to locate or prompt for the Keychain-backed token stub upon shell restart, resulting in "Permission denied (publickey)". | Always pair your Secure Enclave key setup with explicit `AddKeysToAgent yes` and `UseKeychain yes` directives. |

---

## 5. Performance & Optimization Tips

1. **Keep-Alive Tuning for Corporate VPNs:**
   Enterprise VPNs drop idle TCP connections, causing hanging SSH sessions waiting for Secure Enclave timeouts. Add these parameters to your `~/.ssh/config` global block:
   ```ini
   ControlMaster auto
   ControlPath ~/.ssh/ctl-%C
   ControlPersist 10m
   ```
   *Note: ControlPersist keeps the secure connection channel open, reducing repeated Touch ID prompts when running multi-repo orchestration scripts.*

2. **Bypassing Touch ID Fatigue in CI/CD Automation:**
   * **Rule:** Never use Secure Enclave keys inside unattended CI/CD runners (GitHub Actions, Jenkins, GitLab CI). 
   * **Fix:** Secure Enclave keys are strictly for **local developer workstations**. For headless CI/CD pipelines, generate traditional non-resident deploy keys or scoped OAuth tokens stored in secure secret managers (AWS Secrets Manager, GitHub Repository Secrets).

3. **Keychain Health Diagnostics:**
   If your Touch ID prompt stops appearing or keys fail to load after macOS system updates, reset your local agent state instantly with:
   ```bash
   ssh-add -D && ssh-add --apple-use-keychain ~/.ssh/id_ecdsa_enclave
   ```

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp AI Commercial Developer License (v2.4)
* **Copyright © 2025 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, adapt, fork, and embed this code within internal corporate engineering environments, developer onboarding toolkits, and secure workstation setup frameworks.
* **Restrictions:** Redistribution, resale, or public publishing of this specific architecture kit or derivative documentation as a competing paid commercial product is strictly prohibited without explicit written clearance from MicroCorp AI.
* **No Warranty:** This software/documentation is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claims, damages, or infrastructure downtime arising from the deployment of hardware cryptographic keys.