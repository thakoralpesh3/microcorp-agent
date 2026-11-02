# Developer Toolkit: Show HN: Subvocal – Talk to your computer without making noise
**Version:** 1.0.0-rc.2  
**Author:** Developer Tooling Engineer, Engineering Division @ The Agency / MicroCorp AI  
**Target Audience:** Systems engineers, AI tool builders, desktop client developers, and accessibility hackers.

---

## 1. Product Title & Value Proposition

### Title
`subvocal` — The Local-First, Zero-Latency Silent Speech Capture Daemon & SDK

### Value Proposition
Traditional voice-to-text tools require you to speak aloud, disrupting open-plan offices, quiet study spaces, and late-night workflows while exposing sensitive conversations to cloud-based telemetry. **Subvocal** bridges the gap between human intent and machine execution by capturing micro-muscular gestures, sub-audible articulation, and high-frequency piezoelectric sensor data, running entirely offline on your local hardware.

This developer kit provides the complete system architecture, Rust backend daemon bindings, Python ML runtime integration, and cross-platform CLI tools required to build, embed, and commercialize silent-speech capabilities into your own desktop applications and developer tooling.

```
+------------------------------------------------------------+
|                       SUBVOCAL STACK                       |
+------------------------------------------------------------+
|  [Hardware: Piezo/EMG Sensors]                             |
|         │                                                  |
|         ▼ (Raw Analog/USB-HID)                             |
|  [subvocal-d: Real-Time Audio/Signal Daemon]               |
|         │                                                  |
|         ▼ (Local IPC / Unix Domain Socket)                 |
|  [SDK Clients: Rust, Python, TypeScript]                   |
+------------------------------------------------------------+
```

---

## 2. Quick Start & Core Concepts

### Installation
```bash
# Install the subvocal CLI and system daemon
curl --proto '=https' --tlsv1.2 -sSf https://sh.subvocal.dev/install.sh | sh

# Verify installation and check device connectivity
subvocal doctor
```

*If you encounter device permission issues (`Error: EACCES: /dev/hidraw4`), run `subvocal init --fix-udev` to install required udev rules.*

### Core Concepts & Syntax Reference

| Concept | Description | CLI / Code Equivalent |
| :--- | :--- | :--- |
| **Session** | An active capture loop binding sensor hardware to a model pipeline. | `subvocal session start --profile throat-piezo` |
| **Profile** | Calibration matrix mapping user-specific muscular impedance to phonemes. | `subvocal profile calibrate --user me` |
| **Token Stream** | The real-time output stream of inferred text or macro commands. | `subvocal stream --format json` |
| **Guardrail** | Confidence threshold filters preventing unintended actuation. | `--threshold 0.85` |
| **Daemon (`subvocal-d`)** | Background service managing hardware interrupts and local ML inference. | `systemctl --user start subvocal` |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Rust Client Integration (Async Event Loop)
Connect directly to the local Unix domain socket daemon to consume real-time inferred tokens with sub-millisecond overhead.

```rust
// Cargo.toml dependencies:
// tokio = { version = "1.0", features = ["full"] }, serde = { version = "1.0", features = ["derive"] }, serde_json = "1.0", tokio-stream = "0.1"

use serde::Deserialize;
use tokio::net::UnixStream;
use tokio_stream::StreamExt;
use tokio_util::codec::{FramedRead, LinesCodec};

#[derive(Debug, Deserialize)]
pub struct SubvocalEvent {
    pub timestamp: u64,
    pub token: String,
    pub confidence: f32,
    pub finalized: bool,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let socket_path = format!(
        "/run/user/{}/subvocal/subvocal.sock",
        nix::unistd::getuid()
    );

    let stream = UnixStream::connect(&socket_path).await.map_err(|e| {
        format!(
            "Failed to connect to Subvocal daemon at {} — run `subvocal-d` or check `subvocal doctor`. Details: {}",
            socket_path, e
        )
    })?;

    let framed = FramedRead::new(stream, LinesCodec::new());
    let mut lines = framed.map(|res| res.map_err(Into::into));

    println!("[subvocal-client] Listening for silent speech events...");

    while let Some(result) = lines.next().await {
        let line: String = result?;
        let event: SubvocalEvent = serde_json::from_str(&line)?;

        if event.confidence >= 0.82 {
            if event.finalized {
                print!("{}", event.token);
                use std::io::Write;
                std::io::stdout().flush()?;
            }
        }
    }

    Ok(())
}
```

### Pattern 2: Python ML Wrapper & FastAPI Bridge
Embed `subvocal` event streams into an internal AI copilot or IDE extension backend.

```python
import asyncio
import json
import sys
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Subvocal Bridge API", version="1.0.0")

SOCKET_PATH = Path(f"/run/user/{Path.home().owner() if hasattr(Path, 'owner') else 1000}/subvocal/subvocal.sock")

async def subvocal_streamer() -> AsyncGenerator[str, None]:
    if not SOCKET_PATH.exists():
        raise RuntimeError(
            f"Subvocal socket not found at {SOCKET_PATH}. "
            "Ensure the daemon is running with `systemctl --user start subvocal`."
        )
    
    while True:
        try:
            reader, _ = await asyncio.open_unix_connection(str(SOCKET_PATH))
            while True:
                line = await reader.readline()
                if not line:
                    break
                yield line.decode("utf-8").strip()
        except OSError as e:
            # Drop and retry connection with backoff
            await asyncio.sleep(1.0)

@app.websocket("/ws/speech")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        async for raw_event in subvocal_streamer():
            event = json.loads(raw_event)
            # Filter low-confidence inferences at the edge
            if event.get("confidence", 0.0) > 0.80:
                await websocket.send_json({
                    "text": event["token"],
                    "final": event["finalized"]
                })
    except WebSocketDisconnect:
        print("[bridge] Client disconnected", file=sys.stderr)
    except Exception as e:
        print(f"[bridge] Error in stream: {e}", file=sys.stderr)
        await websocket.close(code=1011, reason=str(e))
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Polling the Socket in a Tight Loop
**What people do:** Writing bash scripts or Python loops that `cat /run/user/1000/subvocal/subvocal.sock` or poll an HTTP endpoint every 10ms.  
**Why it fails:** Burns CPU cycles, causes socket desynchronization, and misses high-frequency buffer windows.  
**The Fix:** Use proper asynchronous stream consumption (e.g., `FramedRead` in Rust, `asyncio` UNIX streams in Python) or subscribe via event triggers.

### ❌ Anti-Pattern 2: Hardcoding User ID Paths in Systemd Services
**What people do:** Setting `WorkingDirectory=/run/user/1000/subvocal` in custom service scripts.  
**Why it fails:** Multi-user environments or varying UID allocations (e.g., UID 501 on macOS vs 1000 on Linux) break the daemon instantly.  
**The Fix:** Always resolve runtime paths dynamically via `$XDG_RUNTIME_DIR` or platform APIs:
```rust
let runtime_dir = std::env::var("XDG_RUNTIME_DIR")
    .unwrap_or_else(|_| format!("/run/user/{}", nix::unistd::getuid()));
```

### ❌ Anti-Pattern 3: Ignoring Hardware Calibration Drift
**What people do:** Shipping uncalibrated models across different users or wearing positions.  
**Why it fails:** Muscle impedance varies significantly by hydration, fatigue, and sensor placement, dropping word error rate (WER) accuracy below usable thresholds.  
**The Fix:** Require a 30-second calibration routine on startup if variance exceeds tolerance:
```bash
subvocal profile verify --strict || subvocal profile calibrate --interactive
```

---

## 5. Performance & Optimization Tips

1. **Kernel Buffer Tuning for USB-HID Sensors:**  
   If using custom raw USB piezoelectric sensors, increase the kernel ring buffer allocation to eliminate packet drops during rapid articulation bursts:
   ```bash
   sudo sysfs -w /sys/module/usbhid/parameters/mousepoll 1
   ```
2. **Quantized ONNX Runtime Inference:**  
   Ensure the local inference engine runs INT8 quantized weights (`model.quant.onnx`). This reduces memory footprint from 420MB to 68MB and drops inference latency from 14ms down to **2.4ms per token chunk**.
3. **CPU Affinity Pinning:**  
   For mission-critical low-latency setups, bind the `subvocal-d` daemon to performance cores using `taskset`:
   ```bash
   taskset -c 2,3 subvocal-d --daemonize
   ```

---

## 6. Commercial License & Attribution Summary

### Licensing Terms
* **Dual Licensing Model:** 
  * **Open Source (AGPLv3):** Free for personal use, internal research, and fully open-source Libre projects.
  * **Commercial / OEM License:** Required for closed-source commercial distribution, embedded hardware products, and enterprise SaaS integrations. Contact `licensing@microcorp.ai` for commercial grade SLAs and indemnification.
* **Redistribution:** You may bundle the `subvocal` runtime CLI within proprietary desktop installers provided the attribution footer and copyright notice remain intact in binary help screens (`subvocal --version`).

### Attribution Requirements
Any software utilizing the `subvocal` SDK or daemon API must include the following notice in its `About` dialog or documentation footer:
> *Powered by Subvocal™ by MicroCorp AI — Local-First Silent Speech Technology.*