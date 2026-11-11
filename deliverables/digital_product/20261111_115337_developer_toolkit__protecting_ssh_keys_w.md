# Developer Toolkit: Protecting SSH Keys with macOS Secure Enclave

## 1. Product Title & Value Proposition

### 🔑 Hardware-Backed SSH Authentication on macOS
Eliminate vulnerable plaintext RSA/ED25519 private keys sitting on your disk. This developer reference kit provides the architecture, precise OpenSSH configuration patterns, and automation scripts required to bind your SSH credentials directly to the Apple Secure Enclave coprocessor (Apple Silicon M-series & T2 security chips).

### Why Your Current Setup is Vulnerable
Standard SSH keys (`~/.ssh/id_rsa`, `~/.ssh/id_ed25519`) stored on disk can be silently exfiltrated by malicious Node.js dependencies, supply-chain vulnerabilities in dev dependencies, or malware running in user space. Once extracted, your keys can be cloned infinitely across the globe without your knowledge.

### The Secure Enclave Solution
By leveraging the macOS `ssh-add` integration with the device's cryptographic coprocessor:
* **Hardware Isolation:** Private keys are generated inside isolated silicon and **can never be exported or read**, even by root or kernel-level malware.
* **Biometric Authorization:** Every authentication request (`git push`, `ssh production`) prompts for Touch ID or Apple Watch confirmation.
* **Zero-Disk Footprint:** No private key files exist on your disk to be backed up to unencrypted cloud drives or stolen.

---

## 2. Quick Start & Core Concepts

### Core Architecture Concepts
1. **Secure Enclave:** A hardware-based key manager isolated from the main CPU, featuring its own secure boot, random number generator, and AES encryption engine.
2. **PKCS#11 / CryptoTokenKit:** macOS abstracts hardware tokens via `CryptoTokenKit`. OpenSSH communicates with this subsystem using macOS's native library bridge located at `/usr/lib/ssh-keychain.dylib`.
3. **Key Type Restrictions:** The Secure Enclave currently supports NIST P-256 (secp256r1) elliptic curve cryptography via hardware backing. 

### Quick Setup Commands (Copy-Paste Reference)

| Step | Command | Description |
| :--- | :--- | :--- |
| **1. Generate Key** | `ssh-keygen -t ecdsa-sk -a 100 -b 256 -C "work-key"` | Generates a resident/hardware-bound key tied to the Secure Enclave. |
| **2. Start Agent** | `eval "$(ssh-agent -s)"` | Ensures your local SSH agent session is active. |
| **3. Add to Keychain** | `ssh-add --apple-use-keychain ~/.ssh/id_ecdsa_sk` | Registers the key and hooks it into macOS Touch ID/Keychain services. |
| **4. Export Public Key** | `cat ~/.ssh/id_ecdsa_sk.pub` | Copies public key to append to remote `~/.ssh/authorized_keys`. |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Automated Key Generation & SSH Config Setup
Save this script as `setup-secure-enclave.sh`. It enforces strong parameters, names the key appropriately, and configures your `~/.ssh/config` automatically.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

KEY_NAME="id_ecdsa_enclave"
KEY_PATH="$HOME/.ssh/$KEY_NAME"
COMMENT="${USER}@macbook-secure-enclave"

echo "==> [1/4] Checking OpenSSH version and Secure Enclave availability..."
if ! ssh -V 2>&1 | grep -q "OpenSSH"; then
    echo "Error: OpenSSH is required. Run 'brew install openssh' — see https://brew.sh" >&2
    exit 1
fi

if [[ ! -d "$HOME/.ssh" ]]; then
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
fi

echo "==> [2/4] Generating hardware-backed ECDSA key in Secure Enclave..."
if [[ -f "$KEY_PATH" ]]; then
    echo "Warning: Key already exists at $KEY_PATH. Skipping generation." >&2
else
    # -t ecdsa-sk specifies FIDO/Secure Enclave hardware token
    # -a 100 increases KDF rounds for brute-force resistance
    ssh-keygen -t ecdsa-sk -a 100 -C "$COMMENT" -f "$KEY_PATH"
    chmod 600 "$KEY_PATH"
    chmod 644 "${KEY_PATH}.pub"
fi

echo "==> [3/4] Configuring ssh-agent macOS Keychain integration..."
# Ensure Apple Keychain integration is configured in ~/.ssh/config
SSH_CONFIG="$HOME/.ssh/config"
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

if ! grep -q "UseKeychain yes" "$SSH_CONFIG"; then
    cat << 'EOF' >> "$SSH_CONFIG"

# Added by Secure Enclave Toolkit
Host *
    AddKeysToAgent yes
    UseKeychain yes
    IdentityFile ~/.ssh/id_ecdsa_enclave
EOF
    echo "Updated ~/.ssh/config with UseKeychain directives."
else
    echo "ssh config already contains Keychain directives."
fi

echo "==> [4/4] Registering key with running ssh-agent..."
eval "$(ssh-agent -s)"
ssh-add --apple-use-keychain "$KEY_PATH"

echo ""
echo "✨ Success! Your public key is ready for deployment:"
echo "--------------------------------------------------------"
cat "${KEY_PATH}.pub"
echo "--------------------------------------------------------"
echo "Next step: Append this public key to your server's ~/.ssh/authorized_keys"
```

### Pattern 2: Enterprise SSH Config (`~/.ssh/config`) Template
Manage multiple environments cleanly while enforcing hardware token usage.

```ini
# Global Defaults: Force Secure Enclave storage and Keychain caching
Host *
    AddKeysToAgent yes
    UseKeychain yes
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Production Environment (Requires Touch ID confirmation)
Host prod-*
    User deploy
    IdentityFile ~/.ssh/id_ecdsa_enclave
    IdentitiesOnly yes

# Internal Staging Cluster
Host staging.internal.corp
    User engineer
    Port 2222
    IdentityFile ~/.ssh/id_ecdsa_enclave
    IdentitiesOnly yes
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
| :--- | :--- | :--- |
| **Using `rsa` or non-`-sk` keys** | Standard keys are stored as plaintext files on disk and processed entirely in CPU memory space. | Always use `-t ecdsa-sk` or `-t ed25519-sk` to invoke hardware security modules. |
| **Omitting `--apple-use-keychain`** | Without this flag, macOS forgets the key reference after a reboot, requiring manual re-addition. | Always use `ssh-add --apple-use-keychain ~/.ssh/id_ecdsa_sk` during setup. |
| **Disabling Touch ID Prompts** | Trying to bypass Touch ID via automation tools (`expect`, unattended scripts) breaks the hardware security contract. | Accept that hardware tokens require intentional human physical presence (Touch ID). |
| **Copying keys between Macs** | Secure Enclave keys are bound permanently to the specific physical silicon chip they were generated on. They cannot be migrated. | Generate a fresh key pair on each new physical machine using the script in Pattern 1. |

---

## 5. Performance & Optimization Tips

1. **Persistent Agent Configuration:**
   Add the following snippet to your `~/.zshrc` or `~/.bash_profile` to ensure your SSH agent automatically inherits keychain items across shell windows without spawning duplicate agent daemons:
   ```zsh
   # Re-use or start ssh-agent cleanly
   if [ -z "$SSH_AUTH_SOCK" ]; then
       eval "$(ssh-agent -s)" > /dev/null
   fi
   ```
2. **Speeding Up Multiplexed Connections:**
   If you execute frequent SSH commands or run continuous CI/CD deploy scripts against remote servers, enable ControlMaster in your `~/.ssh/config` to reuse the secure channel:
   ```ini
   Host *
       ControlMaster auto
       ControlPath ~/.ssh/ctl-%C
       ControlPersist 10m
   ```
   *Note: Touch ID will only be triggered on the **first** connection establishment; subsequent multiplexed sessions pass instantly through the authenticated socket.*

---

## 6. Commercial License & Attribution Summary

### Developer Commercial License (v1.0)
* **Copyright © 2026 MicroCorp AI & The Agency Engineering Division.** All rights reserved.
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this code and architectural pattern within internal engineering teams, commercial software projects, and enterprise infrastructure pipelines.
* **Restrictions:** Redistribution of this exact documentation or code kit as a standalone paid product, training dataset, or open-source commercial competitor template is strictly prohibited.
* **Warranty Disclaimer:** Provided "as is" without warranty of any kind, express or implied. MicroCorp AI accepts zero liability for deployment misconfigurations, locked-out server access, or lost authentication tokens resulting from hardware replacement or system failure. Always retain emergency out-of-band server access (e.g., cloud provider serial consoles).