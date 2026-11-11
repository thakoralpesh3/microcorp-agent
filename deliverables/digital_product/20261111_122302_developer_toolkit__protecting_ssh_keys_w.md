# Developer Toolkit: Protecting SSH Keys with macOS Secure Enclave
*Architecture Guide, Implementation Kit, and Production Reference*

---

## 1. Product Title & Value Proposition

### 🔑 Hardware-Backed SSH Authentication for Modern Engineering Teams
Standard file-based SSH keys (`id_rsa`, `id_ed25519`) stored on disk represent a persistent security vector: they can be exfiltrated via malware, leaked through misconfigured container volumes, or compromised via compromised workstation backups. 

This **Developer Reference & Architecture Kit** provides a battle-tested blueprint for generating, storing, and utilizing SSH keys bound directly to the **macOS Secure Enclave**—a hardware-isolated cryptographic coprocessor present on Apple Silicon (M1/M2/M3/M4) and T2-security-chip Intel Macs.

#### Value Proposition
* **Zero-Exfiltration Private Keys:** Private keys generated inside the Secure Enclave cannot be exported, copied, or read by user-space malware—even with root/kernel privileges.
* **Biometric Authorization:** Tie every SSH authentication request, Git commit sign, or remote server connection to Touch ID or Apple Watch proximity.
* **OpenSSH Native Integration:** Leverages OpenSSH 8.2+ PKCS#11 support without requiring proprietary wrapper binaries or background daemons.
* **Compliance Ready:** Meets high-bar internal security requirements (SOC2, ISO 27001) for local developer workstation endpoint hardening.

---

## 2. Quick Start & Core Concepts

### Architectural Overview
```
┌────────────────────────────────────────────────────────┐
│                      macOS Host                        │
│                                                        │
│  ┌──────────────┐      ┌──────────────┐                │
│  │    ssh       │─────►│  ssh-agent   │                │
│  └──────────────┘      └──────┬───────┘                │
│                               │ PKCS#11                │
│                               ▼                        │
│                        ┌──────────────┐                │
│                        │  OpenSC █    │                │
│                        └──────┬───────┘                │
└───────────────────────────────┼────────────────────────┘
                                │ PC/SC API
                        ┌───────▼───────┐
                        │Secure Enclave │ 🔒 Hardware Isolated
                        └───────────────┘
```

### Core Syntax & Command Reference

| Operation | Command / Tool | Description |
| :--- | :--- | :--- |
| **Prerequisite Check** | `system_profiler SPiBridgeDataType` | Verifies Apple T2 or Apple Silicon Secure Enclave presence. |
| **Driver Installation** | `brew install opensc` | Installs the PKCS#11 middleware required for OpenSSH-to-Hardware bridge. |
| **Key Generation** | `ssh-keygen -t ecdsa-sk ...` | Generates a resident or non-resident hardware key pair (FIDO2/U2F style). |
| **Agent Registration** | `ssh-add -K /path/to/key` | Loads the PKCS#11 module or hardware token into the SSH agent. |
| **Verify Authentication** | `ssh -Tv git@github.com` | Tests connectivity and confirms hardware token prompt interaction. |

---

## 3. Production Code Patterns & Architecture Examples

### Step 1: Install Required Tooling
Ensure your environment has Homebrew, OpenSSH (v8.2 or newer), and OpenSC installed.

```bash
#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -euo pipefail

echo "==> Checking OpenSSH version..."
# OpenSSH must be >= 8.2 for built-in hardware token / PKCS#11 support
SSH_VERSION=$(ssh -V 2>&1 | awk '{print $1}' | cut -d_ -f2)
echo "Detected OpenSSH version: ${SSH_VERSION}"

echo "==> Installing OpenSC (PKCS#11 middleware)..."
brew install opensc

echo "==> Verifying OpenSC PKCS#11 library path..."
PKCS11_LIB="/opt/homebrew/lib/opensc-pkcs11.so"
if [ ! -f "$PKCS11_LIB" ]; then
  # Fallback for Intel Macs homebrew path
  PKCS11_LIB="/usr/local/lib/opensc-pkcs11.so"
fi

if [ -f "$PKCS11_LIB" ]; then
  echo "✔ OpenSC PKCS#11 library located at: ${PKCS11_LIB}"
else
  echo "Error: OpenSC PKCS#11 library not found. Run 'brew install opensc' and verify architecture." >&2
  exit 1
fi
```

### Step 2: Generate Secure Enclave-Backed SSH Key
Using FIDO2 / ECDSA token parameters supported by macOS `ssh-keygen`:

```bash
#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${HOME}/.ssh/id_ecdsa_secure_enclave"
COMMENT="developer@microcorp.ai-secure-enclave"

if [ -f "$KEY_PATH" ]; then
  echo "Error: Key already exists at ${KEY_PATH}. Back it up or remove it first." >&2
  exit 1
fi

echo "==> Generating hardware-backed SSH key..."
# -t ecdsa-sk: Creates an ECDSA key backed by a security key / hardware enclave
# -a 100: Sets KDF rounds for passphrase protection (if added)
ssh-keygen -t ecdsa-sk -a 100 -C "${COMMENT}" -f "${KEY_PATH}"

echo "==> Key generated successfully."
echo "Public key contents:"
cat "${KEY_PATH}.pub"
```

### Step 3: Configure `~/.ssh/config` for Automated Loading
Configure your local SSH client to automatically interface with the hardware token or PKCS#11 provider without manual `ssh-add` gymnastics on every shell startup.

```ssh
# ~/.ssh/config

Host *
    AddKeysToAgent yes
    UseKeychain yes

# Specific rule for enterprise Git hosting (e.g., GitHub Enterprise or GitLab)
Host github.com-enclave
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ecdsa_secure_enclave
    IdentitiesOnly yes
```

### Step 4: Automated Setup & Verification Script (`bootstrap-enclave-ssh.sh`)
Save this as an executable script in your dotfiles repository to provision new developer workstations in under 60 seconds.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script Name: bootstrap-enclave-ssh.sh
# Description: Automates Secure Enclave SSH configuration on macOS
# Next Step on Error: Read output message and ensure Touch ID is functional.
# ==============================================================================
set -euo pipefail

CONFIG_DIR="${HOME}/.ssh"
TARGET_CONFIG="${CONFIG_DIR}/config"

echo "==> Ensuring ${CONFIG_DIR} permissions..."
mkdir -p "${CONFIG_DIR}"
chmod 700 "${CONFIG_DIR}"

echo "==> Configuring SSH agent auto-start in shell profile..."
ZSHRC="${HOME}/.zshrc"
if ! grep -q "ssh-add" "${ZSHRC}" 2>/dev/null; then
  cat << 'EOF' >> "${ZSHRC}"

# --- MicroCorp AI Secure Enclave SSH Agent Integration ---
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval "$(ssh-agent -s)"
fi
# ---------------------------------------------------------
EOF
  echo "✔ Added ssh-agent evaluation to ${ZSHRC}"
fi

echo "==> Testing SSH connection configuration..."
ssh -T -o ConnectTimeout=5 git@github.com || true

echo "==> Setup complete. Remember to register your public key (.pub) with your code hosting provider."
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Exporting or Backing Up the Private Key File
* **What engineers do:** Try to copy `id_ecdsa_secure_enclave` to a thumb drive or password manager as a "backup."
* **Why it fails:** The file generated by `-sk` parameters is **not** a private key; it is merely a stub / token handle containing the key handle and application parameters. The actual private key bits cannot leave the Secure Enclave. Copying the file without the hardware chip yields an unusable token.
* **The Correct Fix:** Treat the Secure Enclave as disposable hardware. If a Mac is replaced, generate a new key pair and register the new public key with your IdP/GitHub accounts. Maintain access via multiple authorized keys (e.g., secondary hardware tokens or corporate SSO recovery).

### ❌ Anti-Pattern 2: Disabling Touch ID Prompt Timeouts
* **What engineers do:** Attempting to script around Touch ID prompts using background cron jobs or automated scripts.
* **Why it fails:** The Secure Enclave explicitly requires explicit user presence (Touch ID, Apple Watch double-click, or local password) for every signing operation to prevent silent hijacking by malicious user-space processes.
* **The Correct Fix:** Accept the Touch ID prompt as a feature. Configure agent timeouts sensibly if you need balance between security and convenience.

### ❌ Anti-Pattern 3: Mixing Up OpenSC PKCS#11 and FIDO2 Standards
* **What engineers do:** Conflating generic PKCS#11 smart card modules with native OpenSSH FIDO2 (`-sk`) flags.
* **Why it fails:** Results in silent failures, unrecognized token errors, or fallback to standard disk-based keys.
* **The Correct Fix:** Use native OpenSSH FIDO2 implementation (`-t ecdsa-sk` or `-t ed25519-sk`) on macOS Monterey and above; fallback to OpenSC PKCS#11 only when integrating physical YubiKeys via PIV mode.

---

## 5. Performance & Optimization Tips

1. **Leverage ControlMaster for Multiplexing:**
   When running heavy CI pipelines or frequent `git fetch` operations against remote servers, Touch ID prompts can become intrusive if requested on *every* connection. Enable SSH connection multiplexing in `~/.ssh/config`:
   ```ssh
   Host *
       ControlMaster auto
       ControlPath ~/.ssh/ctl-%r@%h:%p
       ControlPersist 10m
   ```
   *Note: This authenticates once via Touch ID and reuses the encrypted socket channel for subsequent commands within the persistence window.*

2. **Optimize Agent Key Lifetimes:**
   Configure your local agent to drop keys or lock when the screen locks to balance ergonomics and security:
   ```bash
   # Add keys with a strict lifetime limit (e.g., 8 hours)
   ssh-add -t 8h ~/.ssh/id_ecdsa_secure_enclave
   ```

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp AI Commercial Developer License (v2.4)
* **Copyright © 2026 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, integrate, and deploy this architecture kit and code patterns within internal corporate environments and commercial products.
* **Restrictions:** Redistribution, resale, or public publishing of this document or its verbatim code patterns as a standalone commercial competing product is strictly prohibited without explicit written authorization from MicroCorp AI.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claims, damages, or security breaches arising from the implementation of cryptographic hardware configurations.