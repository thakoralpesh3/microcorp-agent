# Developer Toolkit: Protecting SSH Keys with macOS Secure Enclave

## 1. Product Title & Value Proposition

### 🔑 Hardware-Backed Cryptography for Modern Engineering Teams
Standard file-based SSH keys (`~/.ssh/id_rsa`, `~/.ssh/id_ed25519`) stored on disk are vulnerable to malware, accidental exfiltration, and unauthorized access. The **macOS Secure Enclave** provides a hardware-isolated subsystem (coprocessor) that generates and stores cryptographic keys, ensuring that private keys **can never be exported** from the hardware, even by root or kernel-level processes.

### Value Proposition
* **Zero Private Key Exposure:** Private keys are generated inside the Secure Enclave hardware and cannot be read, copied, or dumped from disk.
* **Biometric Authorization:** Configure authentication via **Touch ID** or Apple Watch for every SSH connection or signing operation.
* **Enterprise Compliance:** Meets stringent zero-trust security standards (SOC2, ISO 27001) by ensuring hardware root-of-trust for developer workstations.
* **Drop-in Compatibility:** Integrates seamlessly with OpenSSH 8.2+ via OpenSSL / PKCS#11 / `ssh-keygen` cryptographic providers.

---

## 2. Quick Start & Core Concepts

Modern OpenSSH on macOS supports hardware-backed keys natively using the PKCS#11 protocol or Apple's native `-t ecdsa-sk` / `-t ed25519-sk` security key architecture, as well as third-party PKCS#11 drivers for Secure Enclave.

### Core Architecture Concepts
1. **Secure Enclave Processor (SEP):** A dedicated hardware security enclave isolated from the main CPU/OS.
2. **Key Handle / Reference:** The file stored on your disk (`~/.ssh/id_se`) is not a private key; it is a lightweight *reference pointer* that instructs the system to command the Secure Enclave to sign data.
3. **Local Policy:** Enforcement of Touch ID/User Presence (`LAPolicyDeviceOwnerAuthenticationWithBiometrics`) during signing operations.

### Command Quick Reference

| Command | Purpose | When to Use |
| :--- | :--- | :--- |
| `ssh-keygen -t ecdsa-sk -b 521` | Generate hardware-backed security key | Initial setup for local machine |
| `ssh-add -K ~/.ssh/id_ecdsa_sk` | Add key to macOS Keychain / ssh-agent | Session startup / persistence |
| `ssh -i ~/.ssh/id_ecdsa_sk user@host` | Connect to remote server using hardware key | Daily operations |
| `sc_auth status` | Inspect active smart card/token bindings | Troubleshooting authentication state |

---

## 3. Production Code Patterns & Architecture Examples

### Step 1: Generate a Secure Enclave Key
Open Terminal and generate a FIDO2 / Secure Enclave-backed key pair. We use `ecdsa-sk` which maps cleanly to hardware token standards supported by macOS.

```bash
# Create a secure hardware-backed SSH key with Touch ID requirement
ssh-keygen -t ecdsa-sk -b 521 -C "dev-workstation-secure-enclave" -f ~/.ssh/id_ecdsa_sk
```
*Note: When prompted, touch the Touch ID sensor to bind your biometric signature to the key generation process.*

### Step 2: Configure SSH Client (`~/.ssh/config`)
Ensure your SSH client automatically uses the hardware key and stores the passphrase in the macOS Keychain so you don't re-type it constantly (though Touch ID will still trigger per-use if configured).

```ini
# ~/.ssh/config

Host *
  AddKeysToAgent yes
  UseKeychain yes

# Specific configuration for production infrastructure
Host prod-*
  HostName %h.internal.company.com
  User ubuntu
  IdentityFile ~/.ssh/id_ecdsa_sk
  IdentitiesOnly yes
```

### Step 3: Automated Setup Script (`setup-se-key.sh`)
Save this script as `setup-se-key.sh` to onboard new engineers or provision a fresh Mac workstation. 

```bash
#!/usr/bin/env bash
# ==============================================================================
# Tool: setup-se-key.sh
# Description: Provisions a Secure Enclave SSH key with proper permissions & agent.
# ==============================================================================

set -euo pipefail

KEY_PATH="${HOME}/.ssh/id_ecdsa_sk"
COMMENT="${USER}-macbook-secure-enclave"

if [ -f "$KEY_PATH" ]; then
    echo "ℹ️  Key already exists at $KEY_PATH. Skipping generation."
else
    echo "🔑 Generating new Secure Enclave ECDSA-SK key..."
    ssh-keygen -t ecdsa-sk -b 521 -C "$COMMENT" -f "$KEY_PATH"
fi

# Ensure correct permissions
chmod 700 "${HOME}/.ssh"
chmod 600 "$KEY_PATH"
chmod 644 "${KEY_PATH}.pub"

# Start ssh-agent if not running
if ! pgrep -u "$USER" ssh-agent > /dev/null; then
    eval "$(ssh-agent -s)"
fi

# Add to macOS Keychain & agent
ssh-add --apple-use-keychain "$KEY_PATH"

echo "✅ Secure Enclave SSH key successfully configured!"
echo "👉 Public key to copy to servers (~/.ssh/authorized_keys):"
cat "${KEY_PATH}.pub"
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Patterns ❌ | Correct Production Pattern ✅ | Why? |
| :--- | :--- | :--- |
| **Backing up private keys to cloud storage:** Copying `id_rsa` to iCloud Drive or Dropbox. | **Backing up only public keys:** Keep public keys in git/dotfiles; let the Secure Enclave recreate or re-auth hardware keys. | Secure Enclave keys *cannot* be exported. Attempting to copy them results in dummy files or errors. |
| **Disabling User Presence (Touch ID):** Trying to run headless automated scripts with a hardware-backed interactive key. | **Use standard file-based keys for CI/CD:** Reserve Secure Enclave keys exclusively for human developer workstations. | Hardware keys intentionally block automation unless physical/biometric confirmation is given. |
| **Hardcoding ssh-agent paths across macOS updates:** Relying on hardcoded socket paths in launch scripts. | **Use standard launchctl agents:** Let macOS manage `SSH_AUTH_SOCK` automatically via launchd. | Apple updates frequently alter background agent environments; relying on dynamic lookup prevents broken pipes. |

---

## 5. Performance & Optimization Tips

1. **Keep-Alive Tuning for Dropped Touch ID Prompts:**
   If your SSH session drops while waiting for a Touch ID prompt, tune your client heartbeat in `~/.ssh/config`:
   ```ini
   Host *
     ServerAliveInterval 60
     ServerAliveCountMax 3
   ```
2. **Keychain Integration Optimization:**
   Ensure `UseKeychain yes` is set globally in your SSH config to cache the key handle reference efficiently in the macOS Keychain, avoiding redundant keychain password prompts on reboot.
3. **Fast Key Verification:**
   Verify your agent is actively talking to the hardware coprocessor without latency:
   ```bash
   ssh-add -T ~/.ssh/id_ecdsa_sk.pub
   ```

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Developer Toolkit License (v2.1)
* **Copyright © 2026 MicroCorp AI. All rights reserved.**
* **Internal Team Use:** Licensed for unlimited deployment across internal engineering teams, developer workstations, and corporate-managed macOS fleets (MDM compatible).
* **Redistribution:** You may modify and incorporate these architecture patterns into your internal runbooks, bootstrapping scripts, and security compliance documentation. 
* **No Warranty:** Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI is not liable for key loss resulting from macOS hardware failure or SMC resets.