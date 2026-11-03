# Developer Toolkit: Show HN: Subvocal – Talk to your computer without making noise

> **The Agency Engineering Division** — *Developer Tooling Series*  
> *Production Architecture & Integration Kit v1.0.0*

---

## 1. Product Title & Value Proposition

### Subvocal: Silent Speech Interface (SSI) Developer Kit
**Subvocal** is an open, local-first developer framework that intercepts, decodes, and translates subvocalized speech (sub-audible electromyographic [EMG] signals from the jaw and throat, combined with ultra-low-amplitude sub-acoustic vibrations) into actionable system commands, text, and API payloads—**without making a single audible sound**.

```
[ Jaw/Throat EMG Sensors ] 
        │
        ▼ (Sub-millivolt electrical signals)
[ Subvocal Edge Daemon ] ──(Local Ring-Buffer)──> [ ML Intent Decoder (ONNX Runtime) ]
                                                            │
                                                            ▼
                                                [ JSON-RPC / CLI Output ]
```

### Core Value Proposition
* **Zero-Audio Dependency:** Operate microphones-free in open-plan offices, secure cleanrooms, or high-noise environments where speech recognition fails entirely.
* **Air-Gap Privacy:** 100% local processing via quantized ONNX models running on the CPU/NPU. Zero audio data leaves the machine; only abstracted intent events are transmitted.
* **Sub-50ms Latency Pipeline:** Optimized ring-buffers and zero-copy memory mapping ensure sub-vocalization to text/command execution happens before the user finishes articulating the word in their head.
* **Universal Interoperability:** Exposes a lightning-fast CLI and a local Unix Domain Socket / IPC interface (`/var/run/subvocal.sock`) consumable by any language or toolchain.

---

## 2. Quick Start & Core Concepts

### Installation & System Setup
```bash
# Install the core CLI and daemon via The Agency tooling registry
curl -sSL https://raw.githubusercontent.com/the-agency/subvocal/main/install.sh | sh

# Verify hardware sensor connection and initialize baseline calibration
subvocal init --sensors=/dev/ttyACM0
```

### Core Concepts Syntax Table

| Concept | Description | Syntax / Config Example |
| :--- | :--- | :--- |
| **Intent Trigger** | A mapped subvocal pattern that fires a specific OS or shell command. | `subvocal bind "git status" --pattern=jaw_double_clench` |
| **Stream Profile** | Sensor gain, sample rate (default 1000Hz), and noise gate configuration. | `subvocal profile set --rate=1000 --gate=0.12` |
| **Confidence Threshold** | Minimum model certainty required to emit an intent event (0.0 - 1.0). | `subvocal config set inference.threshold 0.85` |
| **Passthrough Mode** | Forwards raw feature tensors to stdout for custom model training. | `subvocal stream --format=json --raw` |
| **Hotword Ring** | Always-listening low-power wake state guarding active execution contexts. | `subvocal daemon --wake-word="computer"` |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Node.js IPC Client for Real-time Subvocal Stream Integration
This robust, production-ready TypeScript module connects to the local Subvocal UNIX domain socket, handles automatic reconnection, and emits typed intent events.

```typescript
// subvocal-client.ts
import * as net from 'net';
import { EventEmitter } from 'events';

export interface SubvocalEvent {
  timestamp: number;
  intent: string;
  confidence: number;
  rawTensorHash: string;
}

export class SubvocalClient extends EventEmitter {
  private socketPath: string;
  private client: net.Socket | null = null;
  private reconnectIntervalMs: number;
  private isDestroyed: boolean = false;

  constructor(socketPath: string = '/var/run/subvocal.sock', reconnectIntervalMs: number = 2000) {
    super();
    this.socketPath = socketPath;
    this.reconnectIntervalMs = reconnectIntervalMs;
  }

  public connect(): void {
    if (this.isDestroyed) return;

    this.client = net.createConnection({ path: this.socketPath }, () => {
      this.emit('connected');
    });

    this.client.setEncoding('utf8');

    let buffer = '';
    this.client.on('data', (chunk: string) => {
      buffer += chunk;
      let boundary = buffer.indexOf('\n');
      while (boundary !== -1) {
        const record = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 1);
        try {
          const parsed: SubvocalEvent = JSON.parse(record);
          this.emit('intent', parsed);
        } catch (err) {
          this.emit('parse_error', { error: err, data: record });
        }
        boundary = buffer.indexOf('\n');
      }
    });

    this.client.on('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'ENOENT') {
        // Respect CLI design rule: Provide actionable fix
        this.emit('error', new Error(`Subvocal daemon socket not found at ${this.socketPath}. Run 'subvocal daemon start' to launch the background service.`));
      } else {
        this.emit('error', err);
      }
    });

    this.client.on('close', () => {
      this.emit('disconnected');
      if (!this.isDestroyed) {
        setTimeout(() => this.connect(), this.reconnectIntervalMs);
      }
    });
  }

  public destroy(): void {
    this.isDestroyed = true;
    if (this.client) {
      this.client.destroy();
    }
  }
}

// --- Usage Example ---
if (require.main === module) {
  const subvocal = new SubvocalClient();
  
  subvocal.on('connected', () => console.log('🟢 Connected to Subvocal daemon IPC.'));
  subvocal.on('intent', (event) => {
    console.log(`🎯 Intent Received: [${event.intent}] (Confidence: ${event.confidence.toFixed(2)})`);
  });
  subvocal.on('error', (err) => {
    console.error(`❌ ${err.message}`);
    process.exit(1);
  });

  subvocal.connect();
}
```

### Pattern 2: Python Edge Daemon Integration & Custom Command Dispatcher
A lightweight Python script demonstrating how to consume raw sensor output or translated commands and trigger OS-level window management or IDE actions.

```python
#!/usr/bin/env python3
"""
subvocal_dispatcher.py
Consumes Subvocal JSON event streams and dispatches hotkeys or API requests.
"""

import sys
import json
import socket
import subprocess
from typing import Dict, Any

SOCKET_PATH = "/var/run/subvocal.sock"

def execute_action(intent: str) -> None:
    actions: Dict[str, list] = {
        "IDE_NEXT_TAB": ["xdotool", "key", "ctrl+Tab"],
        "TERMINAL_TOGGLE": ["i3-msg", "[class=Alacritty] scratchpad toggle"],
        "AI_COMPLETE": ["curl", "-s", "http://localhost:11434/api/generate", "-d", '{"model": "codellama", "prompt": "explain selection"}']
    }
    
    if intent in actions:
        try:
            subprocess.run(actions[intent], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[ACTION] Dispatched: {intent}", flush=True)
        except subprocess.SubprocessError as e:
            print(f"[ERROR] Failed to execute action for {intent}: {e}", file=sys.stderr)
    else:
        print(f"[WARN] Unmapped intent received: {intent}", flush=True)

def main() -> None:
    print(f"Connecting to Subvocal daemon at {SOCKET_PATH}...")
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(SOCKET_PATH)
    except FileNotFoundError:
        print(f"Error: Subvocal socket not found at {SOCKET_PATH}.\nFix: Start the background service using `subvocal daemon start`.", file=sys.stderr)
        sys.exit(1)

    file_obj = client.makefile('r', encoding='utf-8')
    try:
        for line in file_obj:
            line = line.strip()
            if not line:
                continue
            try:
                data: Dict[str, Any] = json.loads(line)
                if data.get("confidence", 0.0) >= 0.80:
                    execute_action(data["intent"])
            except json.JSONDecodeError:
                continue
    except KeyboardInterrupt:
        print("\nShutting down Subvocal dispatcher.")
    finally:
        client.close()

if __name__ == "__main__":
    main()
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Production Approach |
| :--- | :--- | :--- |
| **Polling the Daemon via HTTP** | Adds 10–50ms network overhead and CPU thrashing, destroying the sub-50ms latency target. | Use persistent UNIX domain sockets (`/var/run/subvocal.sock`) with line-delimited JSON streams. |
| **Hardcoding Sensor Thresholds** | Muscle conductivity and skin impedance change with sweat, fatigue, and ambient temperature throughout the day. | Implement dynamic baseline recalibration using `subvocal calibrate --auto` every 4 hours. |
| **Processing Raw ADC Tensors in UI Threads**| Freezes user interfaces (Electron/React) when decoding high-frequency 1000Hz EMG arrays. | Offload inference to the native background daemon and consume lightweight IPC event notifications. |
| **Ignoring Non-TTY Pipe Checks** | Emits ANSI spinners and color codes into automated log collectors or stdout pipes, breaking CI/CD or automation parsers. | Always verify `process.stdout.isTTY` or pass `--quiet`/`--json` flags for headless environments. |

---

## 5. Performance & Optimization Tips

1. **Zero-Copy Memory Mapping:**  
   Configure the sensor ingestion driver to write directly to a shared POSIX shared-memory segment (`/dev/shm/subvocal_ring`) rather than copying buffers across process boundaries.
2. **ONNX Runtime Thread Pinning:**  
   When deploying custom classification models, pin the ONNX Runtime execution provider to dedicated physical CPU cores (avoiding hyperthreaded siblings) to maintain deterministic inference latencies under 12ms.
3. **Quantization to INT8:**  
   Export your subvocalization transformer models to 8-bit integer quantization. This cuts model memory footprint by 75% and speeds up matrix multiplication on edge hardware without sacrificing phoneme recognition accuracy.
4. **Bandpass Filtering:**  
   Enable hardware-level or initial software bandpass filtering (20Hz–250Hz) to strip out 50/60Hz mains hum and gross head movement artifacts before the tensor reaches the classification layer.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial-Grade License (v2.4)
* **Copyright © 2026 MicroCorp AI & The Agency Engineering Division.** All rights reserved.
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, integrate, and deploy this Developer Reference & Architecture Kit within commercial products, internal enterprise tooling, and proprietary SaaS platforms.
* **Restrictions:** Redistribution of this exact documentation kit or underlying proprietary ML weights as a standalone competing developer toolkit is strictly prohibited without written authorization from MicroCorp AI.
* **Warranty & Liability:** Provided "as-is" without warranty of any kind, express or implied. In no event shall MicroCorp AI be liable for any claim, damages, or liability arising from the deployment of neural interface hardware or edge daemons.