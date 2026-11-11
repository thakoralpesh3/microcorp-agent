# Developer Toolkit: Protecting SSH Keys with macOS Secure Enclave

## 1. Product Title & Value Proposition

### 🔑 Hardware-Backed SSH Authentication for macOS Engineers
Protect your production infrastructure from credential theft, malware exfiltration, and unauthorized access by binding your SSH keys directly to the Apple Secure Enclave (Apple Silicon M-series or Intel T2 chips). 

> **The Problem:** Traditional SSH keys live as plaintext files on disk (`~/.ssh/id_rsa`). If a malicious npm package, compromised IDE extension, or phishing binary reads your home directory, your infrastructure is instantly compromised.
> 
> **The Solution:** This Developer Reference & Architecture Kit provides battle-tested patterns, native OpenSSH integration scripts, and production configurations to generate, store, and utilize SSH keys anchored inside a dedicated hardware cryptographic co-processor. Private keys **never** leave the Secure Enclave, and signing operations require biometric confirmation (Touch ID).

---

## 2. Quick Start & Core Concepts

OpenSSH 8.2+ introduced native support for FIDO/U2F hardware tokens and the macOS Secure Enclave via the `ssh-sk` API. By leveraging the `apksig` or native `Keychain` integration, your Mac's secure hardware handles the heavy lifting.

### Clean Syntax & Command Reference

| Action | Command / Syntax | Description |
| :--- | :--- | :--- |
| **Check OpenSSH Version** | `ssh -V` | Verify support for FIDO2/Secure Enclave (Requires OpenSSH $\ge$ 8.2). |
| **Generate Enclave Key** | `ssh-keygen -t ecdsa-sk -O resident -O verify-required -f ~/.ssh/id_enclave` | Generates a hardware-backed key requiring Touch ID. |
| **Add to SSH Agent** | `ssh-add --apple-use-keychain ~/.ssh/id_enclave` | Loads the key into the macOS keychain and ssh-agent. |
| **List Configured Keys** | `ssh-add -l -E sha256` | Displays loaded keys with fingerprint hashes. |
| **Test Connection** | `ssh -vT git@github.com` | Verifies end-to-end handshake with verbose debugging. |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Automated Secure Enclave Key Generation Script
Save this script as `scripts/setup-enclave-key.sh`. It handles generation, permission hardening, and keychain registration idempotently.

```bash
#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${HOME}/.ssh/id_enclave"
KEY_COMMENT="${1:-developer@microcorp.internal}"

echo "🛠️  [MicroCorp Engineering] Initializing Secure Enclave SSH Key Setup..."

# 1. Validate OpenSSH version
SSH_VERSION=$(ssh -V 2>&1 | awk '{print $1}' | cut -d'_' -f2)
REQUIRED_VERSION="8.2"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$SSH_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "❌ Error: OpenSSH version $SSH_VERSION is too old. Secure Enclave requires >= 8.2."
    echo "👉 Fix: Run 'brew install openssh' and update your \$PATH."
    exit 1
fi

# 2. Check if key already exists
if [[ -f "$KEY_PATH" ]]; then
    echo "⚠️ Warning: Key already exists at $KEY_PATH."
    read -rp "Do you want to overwrite it? [y/N] " response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Aborted by user."
        exit 0
    fi
    rm -f "$KEY_PATH" "${KEY_PATH}.pub"
fi

# 3. Generate Secure Enclave Key (ECDSA P-256 with Touch ID enforcement)
echo "🔒 Generating hardware-backed key (Touch ID prompt incoming)..."
ssh-keygen -t ecdsa-sk \
    -o \
    -a 100 \
    -C "$KEY_COMMENT" \
    -f "$KEY_PATH" \
    -O resident \
    -O verify-required

# 4. Set strict file permissions
chmod 600 "$KEY_PATH"
chmod 644 "${KEY_PATH}.pub"

# 5. Register with macOS Keychain and Agent
echo "🔑 Registering with macOS Keychain..."
ssh-add --apple-use-keychain "$KEY_PATH"

echo "✅ Success! Your public key is located at: ${KEY_PATH}.pub"
echo "👉 Copy it to your clipboard with: pbcopy < ${KEY_PATH}.pub"
```

### Pattern 2: Optimized `~/.ssh/config` Architecture
To ensure seamless integration with remote servers, GitHub, GitLab, and corporate bastion hosts, configure your SSH client explicitly.

```ini
# Global Defaults
Host *
    AddKeysToAgent yes
    UseKeychain yes
    ForwardAgent no
    ServerAliveInterval 60
    ServerAliveCountMax 3

# MicroCorp Production Infrastructure (Enforced Hardware Key)
Host *.microcorp.internal prod-bastion-*.aws
    HostName %h
    User ubuntu
    IdentityFile ~/.ssh/id_enclave
    IdentitiesOnly yes
    PubkeyAcceptedKeyTypes ecdsa-sk-sha2-nistp256@openssh.com

# GitHub Integration
Host github.com
    User git
    IdentityFile ~/.ssh/id_enclave
    IdentitiesOnly yes
```

### Pattern 3: Automated Shell Initialization (`~/.zshrc` snippet)
Ensure your SSH agent automatically picks up keys and integrates smoothly with macOS Keychain on terminal launch without prompting needlessly.

```zsh
# --- MicroCorp Secure Enclave SSH Integration ---
test -z "$SSH_AUTH_SOCK" && export SSH_AUTH_SOCK="$HOME/.library/Caches/com.apple.ssh/ssh-agent.socket"

# Automatically load Secure Enclave keys into agent on shell start if missing
if ! ssh-add -l | grep -q "id_enclave"; then
    ssh-add --apple-use-keychain ~/.ssh/id_enclave 2>/dev/null || true
fi
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Patterns ❌ | Why It Fails | Correct Production Pattern ✅ |
| :--- | :--- | :--- |
| **Using RSA keys with Secure Enclave** | The Secure Enclave hardware co-processor natively runs elliptic curve cryptography (ECDSA P-256 / FIDO2). RSA is unsupported in hardware. | Always use `-t ecdsa-sk` for hardware-backed keys. |
| **Forgetting `-O resident`** | Without a resident key, if your local `~/.ssh/` directory is wiped, your private key reference is permanently orphaned from the hardware slot. | Always specify `-O resident` and `-O verify-required` during generation. |
| **Disabling Touch ID (`-O no-verify`)** | Defeats the entire security model. If malware hijacks your shell session, it can silently sign SSH challenges without human presence. | Require user presence (`verify-required`), forcing biometric approval for every connection or session negotiation. |
| **Hardcoding System SSH Paths** | macOS ships with an outdated system OpenSSH binary that lacks full FIDO2/Sk support or Keychain integration flags. | Use Homebrew OpenSSH (`brew install openssh`) and prepend it to your `$PATH`. |

---

## 5. Performance & Optimization Tips

1. **Bypass Keychain Password Prompts:** 
   When running `ssh-add --apple-use-keychain`, macOS may prompt you to store the passphrase in your login keychain. To prevent recurring prompts across reboots, ensure your login keychain password matches your macOS account password.
2. **Control Master Multiplexing for Speed:**
   If you execute frequent SSH commands or deploy via CI scripts inside your terminal, enable connection multiplexing in `~/.ssh/config` to avoid repeated Secure Enclave Touch ID handshakes over a single established session:
   ```ini
   Host *
       ControlMaster auto
       ControlPath ~/.ssh/ctl-%r@%h:%p
       ControlPersist 10m
   ```
3. **Audit Key Health Periodically:**
   Run `ssh-add -T ~/.ssh/id_enclave.pub` to test whether your ssh-agent can successfully communicate with the Secure Enclave hardware slot without executing a full network connection.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Developer Toolkit — Commercial End-User License Agreement (EULA)

* **Version:** 1.0.0
* **Author:** Principal Developer Tooling Engineer, Engineering Division, MicroCorp AI.
* **Grant of Rights:** You are granted a perpetual, worldwide, non-exclusive license to use, modify, adapt, and deploy these code patterns and architectural guides within your personal and enterprise engineering environments.
* **Restrictions:** Redistribution of this kit as a paid commercial product, training data aggregator, or competing developer cheat sheet without explicit written consent from MicroCorp AI is strictly prohibited.
* **Disclaimer of Warranty:** Provided "AS IS", without warranty of any kind, express or implied. In no event shall MicroCorp AI be liable for any claim, damages, or infrastructure security breaches arising from improper configuration of hardware tokens or operating system permissions.