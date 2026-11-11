# Developer Toolkit: Protecting SSH Keys with macOS Secure Enclave

## 1. Product Title & Value Proposition

### 🔑 Hardware-Backed SSH Authentication for macOS Engineers
Protecting production servers, staging clusters, and GitHub repositories with software-only RSA/Ed25519 keys stored on disk (`~/.ssh/id_ed25519`) leaves organizations vulnerable to infostealers, memory-scraping malware, and accidental leakage. 

This enterprise-grade reference architecture kit provides everything required to bind your SSH identity directly to the **Apple Secure Enclave**—a dedicated hardware subsystem featuring isolated AES-256 crypto engines, non-exportable hardware keys, and mandatory biometric (Touch ID) or PIN verification for every single signing operation.

#### 💼 Key Value Propositions
* **Zero-Export Guarantee:** Private keys generated within the Secure Enclave *cannot* be copied, extracted, or exfiltrated, even via root-level kernel exploits.
* **Biometric Enforcement:** Every git commit, production SSH session, or deployment pipeline execution requires localized Touch ID or Secure Enclave PIN confirmation.
* **OpenSSH Native Integration:** Leverages standard OpenSSH `PKCS#11` modules (`/usr/lib/ssh-keychain.dylib`) without requiring third-party background daemons or unsafe binaries.
* **Air-Gapped Portability Protection:** Eliminates vulnerable credential files sitting plaintext on developer laptops.

---

## 2. Quick Start & Core Concepts

### Architecture Flow
```
┌─────────────────┐      ┌──────────────────────────┐      ┌─────────────────────────┐
│  SSH Client     │ ---> │  ssh-agent / PKCS#11     │ ---> │ macOS Secure Enclave    │
│  (ssh / git)    │      │  (/usr/lib/ssh-keychain) │      │ (Hardware Cryptoprocessor)│
└─────────────────┘      └──────────────────────────┘      └─────────────────────────┘
```

### Clean Syntax & Command Reference

| Action / Operation | Command Syntax | Description |
| :--- | :--- | :--- |
| **Generate Hardware Key** | `ssh-keygen -t ecdsa-sk -a 100 -b 521` | Creates an ECDSA key backed by a security key (hardware-bound). |
| **List Keychain Keys** | `ssh-add -K -l` or `ssh-add -e /usr/lib/ssh-keychain.dylib -l` | Lists public keys currently exposed by the macOS Keychain / Secure Enclave provider. |
| **Add Key to Agent** | `ssh-add --apple-use-keychain ~/.ssh/id_ecdsa_sk` | Registers the hardware token with the system SSH agent, persisting Touch ID bindings. |
| **Verify Key Hardware Status** | `ssh-keygen -l -v -f ~/.ssh/id_ecdsa_sk.pub` | Inspects the public key structure to confirm the `sk-ecdsa-sha2-nistp521@openssh.com` type. |
| **Test Connection** | `ssh -vT git@github.com` | Validates SSH authentication handshake and triggers Touch ID challenge. |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: End-to-End Key Generation & Configuration Script
Save this script as `setup-secure-enclave-ssh.sh`. It automates the generation of a Secure Enclave-backed SSH key, registers it with your macOS keychain, configures your SSH client settings, and prints your public key for remote server deployment.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Configuration
KEY_COMMENT="${USER}@macbook-secure-enclave"
KEY_PATH="${HOME}/.ssh/id_ecdsa_sk_enclave"
SSH_CONFIG="${HOME}/.ssh/config"

echo "=== [1/4] Checking macOS Environment ==="
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This script is designed exclusively for macOS. Exiting." >&2
    exit 1
fi

# Ensure .ssh directory exists with strict permissions
mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"

echo "=== [2/4] Generating Secure Enclave ECDSA Key ==="
if [[ -f "${KEY_PATH}" ]]; then
    echo "Warning: Key already exists at ${KEY_PATH}. Skipping generation."
else
    # -t ecdsa-sk: Hardware security key / Secure Enclave backed ECDSA
    # -a 100: Higher KDF rounds for brute-force resistance
    # -b 521: Maximum curve strength for NIST P-521
    ssh-keygen -t ecdsa-sk -a 100 -b 521 -C "${KEY_COMMENT}" -f "${KEY_PATH}"
    
    chmod 600 "${KEY_PATH}"
    chmod 644 "${KEY_PATH}.pub"
    echo "Success: Hardware key generated at ${KEY_PATH}"
fi

echo "=== [3/4] Configuring SSH Client to Auto-Load Keychain ==="
# Append Host block for global management if not already present
if ! grep -q "UseKeychain yes" "${SSH_CONFIG}" 2>/dev/null; then
    {
        echo ""
        echo "Host *"
        echo "  AddKeysToAgent yes"
        echo "  UseKeychain yes"
        echo "  IdentityFile ${KEY_PATH}"
    } >> "${SSH_CONFIG}"
    chmod 600 "${SSH_CONFIG}"
    echo "Success: Updated ${SSH_CONFIG}"
else
    echo "Info: SSH Config already contains keychain directives."
fi

echo "=== [4/4] Adding Key to ssh-agent with Touch ID Binding ==="
# Load key into agent and request keychain persistence
eval "$(ssh-agent -s)" >/dev/null
ssh-add --apple-use-keychain "${KEY_PATH}"

echo ""
echo "=================================================================="
echo " SETUP COMPLETE! Your public key is below:"
echo "=================================================================="
cat "${KEY_PATH}.pub"
echo "=================================================================="
echo "Run: pbcopy < ${KEY_PATH}.pub to copy it to your clipboard."
```

### Pattern 2: Enterprise SSH Config Template (`~/.ssh/config`)
For environments managing multiple cloud providers (AWS, GitHub, internal bastion hosts), isolate your Secure Enclave hardware key configuration cleanly.

```ssh
# =====================================================================
# Enterprise Global Defaults for Secure Enclave Keys
# =====================================================================
Host *
  AddKeysToAgent yes
  UseKeychain yes
  # Enforce strong cryptographic defaults
  Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
  KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org
  MACs hmac-sha2-512-etm@openssh.com

# =====================================================================
# Production Bastion / Kubernetes Control Plane
# =====================================================================
Host prod-bastion-*.internal.corp
  User ubuntu
  IdentityFile ~/.ssh/id_ecdsa_sk_enclave
  IdentitiesOnly yes
  ServerAliveInterval 60
  ServerAliveCountMax 3

# =====================================================================
# GitHub Enterprise / Cloud Git Repositories
# =====================================================================
Host github.com
  User git
  IdentityFile ~/.ssh/id_ecdsa_sk_enclave
  IdentitiesOnly yes
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Copying Private Keys Between Machines
* **The Mistake:** Attempting to backup or copy `id_ecdsa_sk` to a secondary MacBook or external drive.
* **Why it Fails:** Secure Enclave keys are bound inextricably to the physical Apple Silicon secure enclave chip (`T2` or `M-series` SoC). The private key material *never* leaves the hardware module. Copying the file only copies a reference pointer; authentication on another machine will fail instantly.
* **The Correct Fix:** Generate a unique hardware key pair independently on each physical workstation. Register each distinct public key (`.pub`) in your GitHub or server `authorized_keys`.

### ❌ Anti-Pattern 2: Forgetting `--apple-use-keychain` in Automated Shells
* **The Mistake:** Running cron jobs, CI scripts, or automated `git push` pipelines that trigger Secure Enclave operations without an interactive TTY.
* **Why it Fails:** Secure Enclave signing mandates a physical Touch ID touch or PIN confirmation. If run headless without a UI session, the command will hang indefinitely waiting for biometric input.
* **The Correct Fix:** Use traditional software keys (managed via secure CI secrets vaults like GitHub Actions Secrets) for automated headless runners, reserving Secure Enclave hardware keys strictly for interactive developer workstations.

### ❌ Anti-Pattern 3: Using Legacy RSA Keys (`-t rsa`) for Hardware Tokens
* **The Mistake:** Expecting old RSA keys to integrate with Apple's FIDO2/U2F Secure Enclave APIs.
* **Why it Fails:** The Secure Enclave's cryptographic coprocessor natively accelerates elliptic curve cryptography (ECDSA P-256 / Ed25519-sk). RSA operations are not natively supported in hardware security key profiles in the same manner.
* **The Correct Fix:** Always use `ecdsa-sk` (`-t ecdsa-sk`) or `ed25519-sk` (`-t ed25519-sk`) when initializing security-key-backed credentials.

---

## 5. Performance & Optimization Tips

1. **Leverage ControlMaster for Multiplexing:**
   When connecting repeatedly to remote development boxes via Touch ID-protected keys, opening a new TCP connection every time will require constant Touch ID confirmations. Enable SSH connection multiplexing in your `~/.ssh/config`:
   ```ssh
   Host *.internal.corp
     ControlMaster auto
     ControlPath ~/.ssh/ctl-%r@%h:%p
     ControlPersist 10m
   ```
   *Result:* You authenticate with Touch ID *once* for the initial session; subsequent shell tabs open instantly through the shared master socket without re-prompting.

2. **Tune Agent Forwarding Security:**
   Never enable `ForwardAgent yes` globally. If an untrusted remote server is compromised, attackers can hijack your active socket. If you must forward keys, scope it strictly to trusted jump hosts:
   ```ssh
   Host trusted-jumpbox.corp
     ForwardAgent yes
   ```

3. **Pre-warm Keychain Integration on Login:**
   Ensure your shell profile (`~/.zshrc`) initializes the keychain correctly upon terminal startup to prevent delayed first-run responses:
   ```zsh
   # Add to ~/.zshrc
   if [ -z "$SSH_AUTH_SOCK" ]; then
     eval "$(ssh-agent -s)" >/dev/null
   fi
   ```

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp AI Enterprise Developer License (v2.1)
* **Copyright © 2025 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this architecture kit within internal engineering teams, corporate workstations, and CI/CD development pipelines.
* **Restrictions:** Redistribution, resale, public publishing of unmodified source kits, or inclusion in competing commercial developer training catalogs is strictly prohibited without written authorization from MicroCorp AI.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any damages arising from the use or misuse of hardware cryptographic modules or SSH key infrastructures.