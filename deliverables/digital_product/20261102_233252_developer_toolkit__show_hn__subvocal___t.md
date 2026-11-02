# Subvocal: Enterprise Architecture & Developer Reference Kit
*Talk to your computer without making noise.*

---

## 1. Product Title & Value Proposition

### Subvocal: Local-First Myoelectric & Electromyography (EMG) Speech Recognition Engine
Subvocal is an enterprise-grade, low-latency developer toolkit that translates silent articulation (subvocalizations) into discrete machine-readable text and command intents. By capturing sub-audible neuromuscular signals from facial and throat micro-movements via surface electromyography (sEMG), Subvocal bypasses audio acoustics entirely—allowing developers, operators, and power users to command systems in high-noise environments, secure areas, or public spaces without emitting audible speech.

```
+-------------------------------------------------------------------------+
|                       SUBVOCAL ARCHITECTURE PIPELINE                    |
+-------------------------------------------------------------------------+
|                                                                         |
|  [ sEMG Sensors ] ---> [ Subvocal Daemon ] ---> [ Neural Decoder ] ---> |
|  (Jaw/Submental)       (Zero-Copy Ring)         (Quantized ONNX)        |
|                                                                         |
|                                          +----------------------------+ |
|                                          |   Parsed Intent / Text     | |
|                                          +----------------------------+ |
+-------------------------------------------------------------------------+
```

### Core Value Proposition
- **Absolute Privacy & Zero-Audio Footprint:** Operates completely offline with zero microphone requirement. No audio waveforms leave the local device.
- **Sub-50ms Edge Inference:** Optimized ONNX runtime models executing on local CPU/NPU with strict memory locking (`mlock`) to ensure predictable real-time response.
- **Deterministic Command Routing:** Bridges raw myoelectric feature vectors directly to POSIX shells, IDE extensions, or custom enterprise automation pipelines via Unix domain sockets.

---

## 2. Quick Start & Core Concepts

### CLI Quick Reference & Setup
The `subvocal` CLI is designed to adhere to strict developer tooling standards: fast startup (<15ms), zero network calls on the hot path, and clear actionable error messages.

```bash
# Initialize local configuration and calibrate baseline muscle tension
subvocal init

# Start the background capture daemon with hardware acceleration
subvocal daemon start --device=/dev/ttyUSB0 --npu

# Train a custom user vocabulary profile (requires 10 repetitions)
subvocal profile train --intent="deploy_prod" --samples=10

# Stream real-time text output to stdout (useful for piping into tmux/vim)
subvocal stream --format=raw
```

### Core Concepts & Syntax Table

| Concept | Definition | CLI Flag / API Equivalent | Exit Code / Behavior |
| :--- | :--- | :--- | :--- |
| **Calibration Profile** | User-specific baseline noise floor and muscle impedance vector. | `subvocal profile use <name>` | `0` on success; `64` if profile format is invalid. |
| **Intent Mapping** | Translates decoded phoneme vectors into deterministic shell commands or API hooks. | `subvocal route add <intent> <action>` | `0` on success; `71` on syntax parse error. |
| **Ring Buffer** | Memory-mapped zero-copy IPC buffer shared between kernel driver and user space. | `--buffer-size=4096` | `70` (OS internal error) if memory allocation fails. |
| **Confidence Threshold** | Minimum neural activation score required to emit an event (0.0 to 1.0). | `--threshold=0.85` | Drops packets silently if below threshold; logs drop count in verbose mode. |
| **Dry-Run Mode** | Simulates intent parsing without executing downstream system hooks. | `--dry-run` | Validates configuration syntax and exits `0`. |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: High-Performance Python Daemon Integration
This pattern demonstrates how to consume real-time decoded subvocal events via Unix domain sockets using non-blocking I/O.

```python
#!/usr/bin/env python3
"""
Subvocal Enterprise Daemon Client
Consumes real-time intent streams from the local Subvocal socket.
"""

import asyncio
import json
import sys
from pathlib import Path

SOCKET_PATH = Path("/var/run/subvocal/daemon.sock")

async def handle_intent_stream() -> None:
    if not SOCKET_PATH.exists():
        print(
            f"Error: Subvocal daemon socket not found at {SOCKET_PATH}.\n"
            "Fix: Run `subvocal daemon start` to initialize the background service.",
            file=sys.stderr
        )
        sys.exit(66) # EX_NOINPUT

    while True:
        try:
            reader, _ = await asyncio.open_unix_connection(str(SOCKET_PATH))
            while True:
                line = await reader.readline()
                if not line:
                    break
                
                event = json.loads(line.decode("utf-8").strip())
                if event.get("confidence", 0.0) >= 0.85:
                    print(f"[INTENT] Executing: {event['intent']} (Score: {event['confidence']})")
                    # Trigger downstream enterprise automation here
                    
        except ConnectionRefusedError:
            print("Warning: Connection lost. Retrying in 1 second...", file=sys.stderr)
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f"Error: Unexpected stream failure: {e}\nFix: Check `subvocal logs` for diagnostics.", file=sys.stderr)
            sys.exit(70) # EX_SOFTWARE

if __name__ == "__main__":
    try:
        asyncio.run(handle_intent_stream())
    except KeyboardInterrupt:
        print("\nShutting down Subvocal client gracefully.")
        sys.exit(0)
```

### Pattern 2: Rust Zero-Allocation sEMG Feature Extractor
High-performance backend component processing raw sensor arrays with zero heap allocations on the hot path.

```rust
use std::error::Error;
use std::fmt;

#[derive(Debug)]
pub enum SubvocalError {
    SensorDisconnected(String),
    BufferOverflow,
}

impl fmt::Display for SubvocalError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SubvocalError::SensorDisconnected(dev) => {
                write!(f, "Sensor device disconnected at '{}'. Fix: Reconnect hardware and run `subvocal init --reset`.", dev)
            }
            SubvocalError::BufferOverflow => {
                write!(f, "Ring buffer overflow detected. Fix: Increase buffer allocation via `--buffer-size`.")
            }
        }
    }
}

impl Error for SubvocalError {}

pub struct FeatureExtractor {
    window_size: usize,
}

impl FeatureExtractor {
    pub const fn new(window_size: usize) -> Self {
        Self { window_size }
    }

    /// Extracts Root Mean Square (RMS) features from raw sEMG channels without heap allocation.
    pub fn process_window(&self, raw_samples: &[f32], output: &mut [f32]) -> Result<(), SubvocalError> {
        if raw_samples.len() < self.window_size {
            return Err(SubvocalError::BufferOverflow);
        }

        for (i, chunk) in raw_samples.chunks(self.window_size).enumerate() {
            if i >= output.len() {
                break;
            }
            let sum_squares: f32 = chunk.iter().map(|&x| x * x).sum();
            output[i] = (sum_squares / chunk.len() as f32).sqrt();
        }

        Ok(())
    }
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### Anti-Patterns
1. **Polling the Socket in a Tight Loop:** Writing sync loops to poll the Unix socket without backpressure will saturate CPU cores. *Fix:* Use asynchronous event loops or blocking `epoll`/`kqueue` primitives.
2. **Hardcoding Electrode Placement Coordinates:** Assuming uniform facial muscle topography across users. *Fix:* Always require a per-user calibration profile before enabling inference.
3. **Ignoring Exit Codes in Shell Automation:** Piping `subvocal` directly into destructive commands without checking exit codes. *Fix:* Wrap pipeline executions in defensive shell checks (`set -euo pipefail`).

### Failure Reference Table

| Symptom | Root Cause | Exact Remediation Step |
| :--- | :--- | :--- |
| `Error: ENOENT /etc/subvocal.toml` | Configuration file missing. | Run `subvocal init` to generate a valid template. |
| `Error: Device permission denied (/dev/ttyUSB0)` | User lacks dialout group access. | Run `sudo usermod -aG dialout $USER` and re-login. |
| High latency (>200ms inference) | CPU frequency scaling throttled. | Set CPU governor to performance: `sudo cpupower frequency-set -g performance`. |

---

## 5. Performance & Optimization Tips

- **Memory Locking (`mlockall`):** Configure the Subvocal daemon to lock its memory pages into physical RAM to prevent OS swapping latency during critical decoding phases.
- **Thread Pinning:** Bind the neural decoder inference thread to an isolated physical CPU core using `taskset` or `pthread_setaffinity_np` to eliminate context-switch jitter.
- **Model Quantization:** Always deploy INT8 quantized ONNX models for production edge hardware. FP32 models introduce unnecessary memory bandwidth overhead with zero perceivable gain in phoneme accuracy.

---

## 6. Commercial License & Attribution Summary

### Licensing Terms
- **Developer Tier:** Dual-licensed under MIT for open-source evaluation and Apache 2.0 for internal commercial prototyping.
- **Enterprise OEM Tier:** Requires a commercial runtime license for embedded hardware distribution, closed-source SaaS bundling, or mission-critical safety systems.

### Attribution Requirement
All derivative works, commercial distributions, and user-facing documentation must include the following notice in the About/Credits panel:

> *Powered by Subvocal™ – Local-First Myoelectric Speech Recognition Engine.*
> *Copyright © 2026 MicroCorp AI Engineering Division. All rights reserved.*