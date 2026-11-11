# Developer Toolkit: Protecting SSH Keys with macOS Secure Enclave

## 1. Product Title & Value Proposition

### 🔑 Hardware-Backed SSH Authentication on macOS
Eliminate vulnerable plaintext private keys on your developer workstations. This reference kit provides the architecture, precise OpenSSH configurations, and automated tooling required to bind your SSH identity directly to the Apple Secure Enclave (Apple Silicon M-series or Intel T2 chips). 

```
┌────────────────────────┐      ┌──────────────────────────┐      ┌─────────────────────────┐
│   SSH Client (OpenSSH) │ ───> │ macOS ssh-agent (Keychain)│ ───> │ Apple Secure Enclave    │
│   (ecdsah-sk key)      │      │ (Hardware-backed proxy)  │      │ (Hardware Cryptoprocessor)│
└────────────────────────┘      └──────────────────────────┘      └─────────────────────────┘
```

### The Enterprise Developer Problem
* **The Risk**: Standard SSH keys (`id_rsa`, `id_ed25519`) stored unencrypted or under weak passphrases on disk are vulnerable to exfiltration via malicious `npm` packages, rogue IDE plugins, or local malware.
* **The Solution**: FIDO2/WebAuthn hardware tokens embedded directly into your Mac's silicon. Private keys generated inside the Secure Enclave **cannot be exported, copied, or read** by users, processes, or kernel-level exploits. Even root cannot extract the private key material.

### What's Included in This Kit
* Complete lifecycle management scripts for Secure Enclave resident keys.
* Production-ready `ssh_config` templates with hardware confirmation overrides.
* Troubleshooting playbooks for Touch ID timeouts and SSH multiplexing edge cases.
* Drop-in configuration for Git commit signing via Secure Enclave keys.

---

## 2. Quick Start & Core Concepts

### Core Concepts & Terminology
* **Secure Enclave**: A hardware-based isolated coprocessor separate from the main CPU, featuring its own secure boot, AES engine, and hardware UID.
* **FIDO2 / SK (Security Key)**: OpenSSH supports hardware tokens via the `ecdsa-sk` and `ed25519-sk` key types (PKCS#11 / FIDO2 standards adapted for SSH).
* **Resident Key**: A key stored physically inside the Secure Enclave hardware itself, allowing you to recreate the public key reference file anywhere without carrying raw key blobs.
* **Touch ID Prompt**: Biometric user-presence verification required *on every single authentication attempt*, preventing automated session hijacking.

### Essential Command Reference

| Action | Command | Purpose |
| :--- | :--- | :--- |
| **Check Support** | `ssh -Q key` | Verify if OpenSSH supports `ecdsa-sk` / `ed25519-sk`. |
| **Generate Key** | `ssh-keygen -t ecdsa-sk -O resident -O verify-required -f ~/.ssh/id_ecdsa_sk` | Generates a hardware-bound key requiring Touch ID. |
| **List Resident** | `ssh-add -K` or `ssh-add -T` | Interrogates the agent and hardware tokens. |
| **Test Agent** | `ssh-add -l` | Lists fingerprints of keys currently loaded in `ssh-agent`. |
| **Add to Agent** | `ssh-add --apple-use-keychain ~/.ssh/id_ecdsa_sk` | Loads the key into the macOS Keychain-backed agent. |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Automated Key Generation & Enrollment Script
Save this script as `bin/setup-secure-enclave-ssh.sh`. It enforces optimal security flags: `-O resident` (stored in hardware), `-O verify-required` (forces Touch ID biometric verification), and outputs clear next steps.

```bash
#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${HOME}/.ssh/id_ecdsa_sk"
COMMENT="${USER}@macbook-secure-enclave"

echo "=== [1/4] Validating macOS Environment ==="
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This architecture pattern requires macOS with Apple Silicon or T2 chip." >&2
    echo "Next Step: Run this script on a supported macOS workstation." >&2
    exit 1
fi

if ! ssh -Q key | grep -q "ecdsa-sk"; then
    echo "Error: Installed OpenSSH client does not support ecdsa-sk." >&2
    echo "Next Step: Upgrade OpenSSH via Homebrew: 'brew install openssh'" >&2
    exit 1
fi

echo "=== [2/4] Generating Secure Enclave Resident Key ==="
if [[ -f "${KEY_PATH}" ]]; then
    echo "Warning: Key already exists at ${KEY_PATH}."
    read -rp "Do you want to overwrite it? [y/N] " response
    if [[ "${response}" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        rm -f "${KEY_PATH}" "${KEY_PATH}.pub"
    else
        echo "Aborted by user."
        exit 0
    fi
fi

# Generate the key. 
# -t ecdsa-sk: Uses ECDSA over Curve P-256 backed by FIDO2 token
# -O resident: Makes it a resident key (stored on token hardware)
# -O verify-required: Forces user verification (Touch ID / PIN) on every use
ssh-keygen -t ecdsa-sk \
    -O resident \
    -O verify-required \
    -C "${COMMENT}" \
    -f "${KEY_PATH}"

echo "=== [3/4] Configuring macOS ssh-agent & Keychain ==="
# Ensure ssh-agent is running and configured to load keys into macOS keychain
eval "$(ssh-agent -s)"
ssh-add --apple-use-keychain "${KEY_PATH}"

echo "=== [4/4] Setup Complete ==="
echo "Success! Your public key is ready at: ${KEY_PATH}.pub"
echo ""
echo "Next Action: Append your public key to remote servers:"
echo "  ssh-copy-id -i ${KEY_PATH}.pub user@your-server"
cat "${KEY_PATH}.pub"
```

### Pattern 2: Enterprise `~/.ssh/config` Best Practices
Add this configuration block to your `~/.ssh/config` to ensure your SSH client automatically prompts the Secure Enclave agent and handles persistent connections safely.

```ssh
# ~/.ssh/config

Host *
    # Automatically add keys to the keychain and use Apple's agent
    AddKeysToAgent yes
    UseKeychain yes
    
    # Prevent connection drops by sending keepalive pulses (every 60s)
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Specific configuration for high-security production environments
Host prod-cluster-*.internal
    User deploy
    IdentityFile ~/.ssh/id_ecdsa_sk
    IdentitiesOnly yes
    # Force strict host key checking for financial/enterprise tiers
    StrictHostKeyChecking yes
```

### Pattern 3: Git Commit Signing via Secure Enclave
You can leverage your Secure Enclave key to sign Git commits cryptographically, ensuring tamper-proof commit histories.

```bash
# 1. Configure Git to use SSH signing format
git config --global gnu.format ssh

# 2. Point Git to your Secure Enclave public key
git config --global user.signingkey ~/.ssh/id_ecdsa_sk.pub

# 3. Enable automatic signing for all repositories
git config --global commit.gpgsign true

# 4. (Optional) Configure allowed signers for verification
echo "$(git config --global user.email) namespaces=\"git\" $(cat ~/.ssh/id_ecdsa_sk.pub)" >> ~/.ssh/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
| :--- | :--- | :--- |
| **Copying `id_ecdsa_sk` between machines** | The private key does *not* exist in the file; the file is only a stub pointer. Copying the file to another Mac will result in authentication failures. | Generate a unique resident key pair independently on each physical workstation. |
| **Disabling Touch ID (`-O no-verify`)** | Defeats the hardware security guarantee. If malware gains shell access, it can silently hijack your open `ssh-agent`. | Always enforce `-O verify-required` so physical user presence (Touch ID) is required. |
| **Using legacy RSA keys with tokens** | FIDO2 / Secure Enclave standards do not support legacy RSA algorithms (`rsa4096`). | Strictly use `ecdsa-sk` (P-256) or `ed25519-sk`. |
| **Ignoring macOS SSH Agent overrides** | System updates or third-party terminal multiplexers can spawn orphaned `ssh-agent` processes that do not hook into the macOS Keychain. | Explicitly invoke `eval "$(ssh-agent -s)"` and verify Keychain integration with `ssh-add -A`. |

---

## 5. Performance & Optimization Tips

1. **Keepalive Tuning for Touch ID Prompts**: If your SSH session times out due to inactivity, your Touch ID token session might require re-authentication. Set `ServerAliveInterval 60` to keep connections fresh without hammering the Secure Enclave coprocessor.
2. **Multiplexing (`ControlMaster`)**: Enable SSH connection multiplexing for frequently accessed development bastions. This reuses an authenticated encrypted channel, reducing the frequency of Touch ID prompts during heavy deployment cycles:
   ```ssh
   Host *.mycompany.com
       ControlMaster auto
       ControlPath ~/.ssh/ctl-%C
       ControlPersist 10m
   ```
3. **Backup Strategy for Resident Keys**: Because resident keys are stored within the Secure Enclave hardware, if your Mac's logic board is replaced, the hardware token ID changes. Always register *two separate* backup keys (e.g., one on your MacBook Secure Enclave and one on a physical YubiKey FIDO2 token) and append both public keys to your remote `~/.ssh/authorized_keys`.

---

## 6. Commercial License & Attribution Summary

### Developer Toolkit Commercial License (v1.0.0)
* **Copyright © 2026 MicroCorp AI. All rights reserved.**
* **Grant of Rights**: Licensed to the purchasing individual engineer or enterprise team for internal deployment, continuous integration pipelines, and workstation security hardening.
* **Restrictions**: Redistribution, resale, public publishing of this specific compilation document, or inclusion in paid training courses without express written consent from MicroCorp AI is strictly prohibited.
* **Support & Warranty**: Provided "AS IS" without warranty of any kind, express or implied. MicroCorp AI disclaims all liability for misconfigured system files or locked-out server environments.

---
*Generated by Developer Tooling Engineer 🛠️ | MicroCorp AI Engineering Division*