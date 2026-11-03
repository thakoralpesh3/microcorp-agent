# Subvocal: Enterprise Architecture & Integration Kit
**Developer Reference & Architecture Kit v1.0.0**  
*Published by MicroCorp AI Engineering Division*

---

## 1. Product Title & Value Proposition

### Subvocal: Silent Speech Interface for Developers & Power Users
**Talk to your computer without making noise.**

Modern development workflows demand deep focus, yet our primary human-computer interaction models (keyboard, mouse, audio voice dictation) either break flow or fail in open-plan offices, quiet environments, and secure facilities. **Subvocal** is a high-performance, edge-first machine learning CLI and SDK pipeline that captures subtle electromyographic (EMG) or sub-audible vocal tract kinematics via lightweight hardware, translating silent mouth movements and micro-gestures into verified shell commands, IDE actions, and programmatic input with zero audio leakage.

```
+------------------+     +-----------------------     +------------------------+
|  Hardware Sensor | --> | Subvocal Daemon (C++) | --> | Local LLM / Matcher    |
|  (EMG / Mic Grid)|     | Sub-15ms Latency      |     | Intent Resolution      |
+------------------+     +-----------------------     +------------------------+
                                                                   |
                                                                   v
                                                      +------------------------+
                                                      | Executable Action /    |
                                                      | Shell Output (Exit 0)  |
                                                      +------------------------+
```

### Core Value Proposition
- **Total Silence, Absolute Privacy:** Process all tensor models and signal classification strictly locally on-device. Zero cloud audio telemetry.
- **Sub-50ms End-to-End Latency:** Engineered in optimized C++ and Rust bindings, guaranteeing that silent command invocation feels as instantaneous as a mechanical keypress.
- **Enterprise Scriptability & Extensibility:** Exposes a strict CLI interface with predictable exit codes, JSON output flags for CI/CD pipeline integration, and robust hook APIs for custom IDE actions.

---

## 2. Quick Start & Core Concepts

### Installation & System Requirements
Ensure you have the required audio/EMG capture permissions and system dependencies.

```bash
# Install the core CLI and daemon via our installer script
curl -sSL https://raw.githubusercontent.com/microcorp-ai/subvocal/main/install.sh | sh

# Verify installation and inspect hardware loopback
subvocal doctor
```

### CLI Command Reference & Syntax Table

| Command | Arguments / Flags | Description | Exit Codes |
| :--- | :--- | :--- | :--- |
| `subvocal init` | `--config <path>`, `--force` | Initializes local configuration file (`subvocal.toml`). | `0`: Success<br>`1`: Config exists (use `--force`) |
| `subvocal daemon` | `--port <int>`, `--verbose`, `-q` | Starts the background classification engine. | `0`: Clean shutdown<br>`2`: Port in use |
| `subvocal train` | `--phrase <str>`, `--samples <int>` | Records and trains custom local vocabulary tensors. | `0`: Trained<br>`3`: Insufficient signal |
| `subvocal exec` | `--dry-run`, `--json` | Captures single silent utterance and executes mapped action. | `0`: Success<br>`4`: Match failure |
| `subvocal doctor` | `--fix`, `--json` | Diagnostics for audio/EMG devices and tensor runtimes. | `0`: All systems operational<br>`5`: Hardware missing |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Daemon Integration Client (Python SDK)
This robust integration demonstrates how to consume the Subvocal local WebSocket daemon, handle connection drops with exponential backoff, and safely execute system actions.

```python
#!/usr/bin/env python3
"""
Subvocal Enterprise Client Integration
--------------------------------------
Connects to the local Subvocal daemon, receives classified intent events,
and dispatches safe operational tasks.
"""

import asyncio
import json
import sys
import websockets
from typing import Dict, Any

DAEMON_URI = "ws://127.0.0.1:9870/events"
RECONNECT_INTERVAL_SEC = 2.0

async def handle_intent(intent: Dict[str, Any]) -> None:
    """Process incoming classified intent from the subvocal pipeline."""
    action = intent.get("action")
    confidence = intent.get("confidence", 0.0)

    if confidence < 0.85:
        print(f"[WARN] Intent '{action}' dropped: low confidence ({confidence:.2f})", file=sys.stderr)
        return

    print(f"[EXEC] Triggering action: {action} (Confidence: {confidence:.2f})")
    
    # Map actions to system tasks
    if action == "git_status":
        proc = await asyncio.create_subprocess_exec("git", "status", "--porcelain")
        await proc.communicate()
    elif action == "toggle_mute":
        # Example system call abstraction
        print("[INFO] Audio mute state toggled silently.")
    else:
        print(f"[ERROR] Unrecognized intent mapping: '{action}'", file=sys.stderr)

async def subvocal_listener() -> None:
    """Main event loop with fault-tolerant reconnection logic."""
    while True:
        try:
            async with websockets.connect(DAEMON_URI) as websocket:
                print(f"[INFO] Connected to Subvocal daemon at {DAEMON_URI}", file=sys.stderr)
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await handle_intent(data)
                    except json.JSONDecodeError as err:
                        print(f"[ERROR] Malformed JSON payload: {err} — ignoring frame", file=sys.stderr)
        except websockets.exceptions.ConnectionClosedError as err:
            print(f"[WARN] Connection dropped ({err}). Reconnecting in {RECONNECT_INTERVAL_SEC}s...", file=sys.stderr)
            await asyncio.sleep(RECONNECT_INTERVAL_SEC)
        except OSError as err:
            # Fix error message guidance per engineering specs
            print(f"[ERROR] Cannot reach Subvocal daemon at {DAEMON_URI}. Run `subvocal daemon start` to launch it.", file=sys.stderr)
            await asyncio.sleep(RECONNECT_INTERVAL_SEC * 2)

if __name__ == "__main__":
    try:
        asyncio.run(subvocal_listener())
    except KeyboardInterrupt:
        print("\n[INFO] Client shut down cleanly by user.", file=sys.stderr)
        sys.exit(0)
```

### Pattern 2: Custom C++ Signal Processing Hook
For engineers embedding Subvocal into custom hardware peripherals or low-latency desktop wrappers.

```cpp
#include <iostream>
#include <vector>
#include <cstdint>
#include <stdexcept>

// Subvocal Hardware Abstraction Interface
namespace MicroCorp::Subvocal {

struct SignalFrame {
    uint64_t timestamp;
    std::vector<float> sensor_channels;
};

class TensorClassifier {
public:
    explicit TensorClassifier(const std::string& model_path) {
        if (model_path.empty()) {
            // Rule 1: Errors must state the fix, not just the failure
            throw std::runtime_error(
                "Error: Model weights path is empty. "
                "Specify a valid tensor file path or run `subvocal init --download-weights`."
            );
        }
        // Initialize weights...
    }

    float classify(const SignalFrame& frame, std::string& out_intent) {
        if (frame.sensor_channels.empty()) {
            out_intent = "UNKNOWN";
            return 0.0f;
        }
        // Mock classification inference pass
        out_intent = "git_commit_quick";
        return 0.94f;
    }
};

} // namespace MicroCorp::Subvocal

int main() {
    try {
        MicroCorp::Subvocal::TensorClassifier classifier("./models/v1_quantized.bin");
        MicroCorp::Subvocal::SignalFrame sample{1700000000, {0.12f, 0.45f, 0.89f}};
        
        std::string intent;
        float score = classifier.classify(sample, intent);
        
        std::cout << "{\"intent\": \"" << intent << "\", \"confidence\": " << score << "}" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        return 1; // Exit code 1: Unhandled initialization/runtime error with action fix
    }
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | The Correct Enterprise Approach |
| :--- | :--- | :--- |
| **Direct Audio Mic Hooking** | Ordinary room microphones pick up ambient keyboard clatter, breathing, and HVAC noise, destroying classifier accuracy. | Use dedicated contact microphones or differential EMG sensor arrays designed specifically for subvocal muscle twitch isolation. |
| **Hardcoding API Ports in Client Scripts** | Daemon ports conflict in multi-user environments or containerized dev boxes. | Read configuration dynamically from `~/.config/subvocal/config.toml` or environment variable `SUBVOCAL_DAEMON_PORT`. |
| **Blocking the Event Loop on Inference** | Performing synchronous tensor operations inside the main UI thread freezes IDE extensions or window managers. | Offload all tensor classification to the background daemon and communicate purely via async IPC / WebSockets. |
| **Ignoring Exit Codes in Automation** | Treating all CLI errors as generic failures breaks shell scripting pipelines and automated test suites. | Inspect specific exit codes (e.g., `4` for intent match failure vs `5` for missing hardware) to branch recovery logic cleanly. |

---

## 5. Performance & Optimization Tips

1. **Enable SIMD and Hardware Acceleration:** Ensure your build compiles with AVX2 or Apple Silicon Neural Engine (ANE) flags enabled. Set `hardware_acceleration = "auto"` in your `subvocal.toml`.
2. **Quantize Custom Tensors:** When training custom vocabularies via `subvocal train`, export models in 8-bit integer quantization (`INT8`) to reduce memory footprint by 75% and cut inference time down to under 12ms.
3. **Tune Silence Thresholds:** Adjust the Voice/Muscle Activity Detection (VMAD) gate threshold to prevent background jaw movements from triggering accidental CLI commands:
   ```toml
   [audio_gate]
   threshold_db = -42.5
   min_duration_ms = 80
   ```
4. **Pipe-Safe Scripting:** When integrating into shell automation, always pass `--json` and `-q` (quiet) to suppress human-readable progress spinners and ANSI color codes:
   ```bash
   subvocal exec --json -q | jq '.action'
   ```

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial Developer License v2.4
Copyright © 2026 MicroCorp AI. All rights reserved.

- **Grant of Rights:** This Enterprise Reference & Architecture Kit is licensed for internal evaluation, commercial product integration, and deployment within your organization. Redistribution of raw kit source code or derivative commercial products without prior written authorization from MicroCorp AI is strictly prohibited.
- **Warranty Disclaimer:** The software and reference designs are provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.
- **Support & Enterprise Upgrades:** For 24/7 mission-critical SLAs, custom sensor array integration, and proprietary model fine-tuning support, contact the MicroCorp AI Engineering Division at `enterprise@microcorp.ai`.