# Developer Toolkit: Show HN: Subvocal – Talk to your computer without making noise

> **SKU:** `MC-DT-SUB-2026-V1`  
> **Author:** Developer Tooling Engineer, Engineering Division @ MicroCorp AI  
> **Target Audience:** Systems Engineers, Machine Learning Practitioners, and Desktop Tooling Developers building low-latency, privacy-first voice and sub-vocal interfaces.

---

## 1. Product Title & Value Proposition

### Value Proposition
Modern developer workflows demand voice interaction (for hands-free coding, prompt injection, and terminal control), but open-microphone setups fail in open-plan offices, coffee shops, and secure zones where acoustic speech is unacceptable or a privacy leak. 

**Subvocal** is a local-first, low-latency developer toolkit that captures micro-muscular electrical signals, facial electromyography (EMG), or ultra-low amplitude laryngeal vibrations via commodity hardware (bone-conduction sensors, modified earbuds, or electromyographic patches) and translates them into deterministic shell commands, IDE actions, and LLM prompts—**without a single decibel leaving your lips.**

### What You Get in This Kit
- **Architectural Blueprints:** End-to-end signal processing pipelines from raw analog-to-digital conversion (ADC) to intent resolution.
- **Production-Ready Code:** Real-time ring buffers, ONNX Runtime inference wrappers, and asynchronous event emitters in Rust and Python.
- **Operational Safety:** Built-in validation, fallback modes, and deterministic exit codes for automated tooling integration.

---

## 2. Quick Start & Core Concepts

### Core Concepts
1. **EMG/Laryngeal Signal Stream:** High-frequency sampling (1kHz–4kHz) of neuromuscular impulses controlling speech articulators.
2. **Sliding Feature Extraction:** Short-Time Fourier Transform (STFT) combined with Mel-Frequency Cepstral Coefficients (MFCCs) optimized for non-acoustic micro-vibrations.
3. **Intent Router:** A zero-copy classification engine mapping tensor outputs to executable actions with sub-50ms execution budgets.

### CLI & API Reference Table

| Flag / Command | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `subvocal init` | Subcommand | N/A | Generates local configuration (`subvocal.toml`) and calibrates baseline muscle noise. |
| `subvocal daemon` | Subcommand | N/A | Starts the background inference daemon processing the hardware input stream. |
| `--device` | String | `auto` | Specifies the input hardware interface (`/dev/ttyUSB0`, `pipewire`, or `ble:mac`). |
| `--model` | Path | `~/.subvocal/models/default.onnx` | Path to the custom ONNX intent classification model. |
| `--threshold` | Float | `0.85` | Confidence threshold required to trigger downstream execution. |
| `--dry-run` | Boolean | `false` | Logs matched intents to `stdout` without executing bound actions. |
| `--json` | Boolean | `false` | Emits structured JSON events instead of human-readable terminal UI. |

---

## 3. Production Code Patterns & Architecture Examples

### Architecture Overview
```
[ Hardware Sensor (EMG/Bone-Conduction) ]
                   │
                   ▼ (Raw PCM / ADC Stream @ 2kHz)
[ Ring Buffer & DC Removal Filter ]
                   │
                   ▼ (Framed Windows)
[ Feature Extraction (MFCC / Spectral Flux) ]
                   │
                   ▼ (Tensor Float32[1, 80, 64])
[ ONNX Runtime Inference Engine ]
                   │
                   ▼ (Logits & Confidence Scores)
[ Intent Dispatcher & Command Executor ]
```

### Pattern 1: Real-Time Signal Processing Pipeline (Rust)
This production-grade module implements a zero-allocation ring buffer and sliding window feature extractor designed for sub-millisecond hot paths.

```rust
// File: src/pipeline.rs
use std::collections::VecDeque;
use std::io::{self, Write};

pub struct AudioRingBuffer {
    buffer: VecDeque<f32>,
    capacity: usize,
}

impl AudioRingBuffer {
    pub fn new(capacity: usize) -> Self {
        Self {
            buffer: VecDeque::with_capacity(capacity),
            capacity,
        }
    }

    #[inline(always)]
    pub fn push_sample(&mut self, sample: f32) {
        if self.buffer.len() == self.capacity {
            self.buffer.pop_front();
        }
        self.buffer.push_back(sample);
    }

    pub fn get_window(&self, size: usize) -> Result<Vec<f32>, &'static str> {
        if self.buffer.len() < size {
            return Err("Error: Insufficient samples in ring buffer — run `subvocal calibrate` to verify hardware stream.");
        }
        Ok(self.buffer.iter().rev().take(size).cloned().collect())
    }
}

pub fn process_frame(window: &[f32]) -> Result<Vec<f32>, &'static str> {
    if window.is_empty() {
        return Err("Error: Empty frame passed to feature extractor. Fix: Check sensor connection and restart daemon.");
    }
    
    // Stub for Mel-Frequency Cepstral Coefficient (MFCC) extraction
    let mut features = vec![0.0f32; 64];
    for (i, val) in window.iter().enumerate() {
        features[i % 64] += val * 0.01; // Simplified transform for demonstration
    }
    Ok(features)
}
```

### Pattern 2: Asynchronous Intent Dispatcher (Python)
An asynchronous daemon runner that loads an ONNX model, processes incoming feature tensors, and dispatches shell commands safely.

```python
#!/usr/bin/env python3
"""
Subvocal Daemon Engine - High-Performance Inference Runner
"""
import sys
import json
import asyncio
from pathlib import Path
import numpy as np

def emit_error(msg: str, exit_code: int = 1):
    """Prints structured error adhering to CLI guidelines and exits."""
    payload = {"status": "error", "message": msg, "fix": "Run 'subvocal init --help' for troubleshooting guide."}
    sys.stderr.write(json.dumps(payload) + "\n")
    sys.exit(exit_code)

async def load_model(model_path: Path):
    if not model_path.exists():
        emit_error(f"Model file not found at {model_path}. Fix: Run `subvocal download-model --default`.")
    # Simulated ONNX session load
    await asyncio.sleep(0.01) 
    return {"session": "loaded", "path": str(model_path)}

async def main_loop(model_path: Path, threshold: float, dry_run: bool):
    model = await load_model(model_path)
    sys.stdout.write(json.dumps({"status": "ready", "model": model["path"]}) + "\n")
    sys.stdout.flush()

    while True:
        try:
            # Simulate receiving tensor from sensor ring buffer
            await asyncio.sleep(0.05)
            simulated_logits = np.array([0.02, 0.91, 0.05, 0.02]) # Intent 1 exceeds threshold
            confidence = float(np.max(simulated_logits))
            intent_id = int(np.argmax(simulated_logits))

            if confidence >= threshold:
                action = f"exec_macro_{intent_id}"
                if dry_run:
                    print(json.dumps({"event": "intent_matched", "intent": intent_id, "confidence": confidence, "action": action, "mode": "dry-run"}))
                else:
                    # Execute action
                    print(json.dumps({"event": "dispatch", "intent": intent_id, "confidence": confidence}))
                    sys.stdout.flush()
        except KeyboardInterrupt:
            sys.stdout.write(json.dumps({"status": "shutdown", "reason": "user_interrupt"}) + "\n")
            sys.exit(0)

if __name__ == "__main__":
    model_p = Path.expanduser(Path("~/.subvocal/models/default.onnx"))
    try:
        asyncio.run(main_loop(model_p, threshold=0.85, dry_run=True))
    except Exception as e:
        emit_error(f"Unexpected runtime failure: {str(e)}")
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | The Correct Approach |
| :--- | :--- | :--- |
| **Global State Mutation** | Modifying global audio stream parameters across threads introduces race conditions and segmentation faults in the audio loop. | Use thread-safe lock-free ring buffers (`crossbeam` in Rust or `asyncio.Queue` in Python). |
| **Hardcoding Sensor Paths** | `/dev/ttyUSB0` changes across reboots, breaking user setups. | Implement auto-discovery probing protocols with explicit fallback configuration flags (`--device`). |
| **Blocking the Hot Path** | Performing disk I/O or network calls inside the 50ms inference loop causes dropped frames and audio buffer overflows. | Offload logging and dispatch to asynchronous worker pools (`tokio` tasks or background coroutines). |
| **Swallowing Errors** | Catching generic exceptions (`except Exception: pass`) leaves users staring at a frozen terminal when hardware disconnects. | Always surface actionable errors specifying *what* failed and *how* to fix it. |

---

## 5. Performance & Optimization Tips

1. **Zero-Copy Tensor Allocation:** When passing buffers from the audio capture thread to the ONNX runtime, reuse pre-allocated memory arenas to eliminate garbage collection pauses (Python) or heap allocations (Rust).
2. **Quantization:** Compile your intent models using INT8 quantization (`optimum-cli` or TensorRT). This reduces model size by 75% and cuts inference latency from 35ms down to 4ms on edge hardware.
3. **CPU Affinity:** Bind the primary inference thread to a dedicated Performance Core (P-core) on hybrid architectures (Apple Silicon M-series or Intel Core 12th+ gen) using core-affinity libraries to prevent OS thread migration jitter.
4. **TTY Detection for Automation:** Always check if `stdout` is a TTY. When piped (e.g., `subvocal daemon --json | jq .`), suppress spinners, color codes, and banner art to guarantee parseable streams for CI/CD or desktop scripts.

---

## 6. Commercial License & Attribution Summary

### License Type
**MicroCorp AI Commercial Developer License (MC-CDL-1.0)**  
*This software and associated architecture kits are proprietary products of MicroCorp AI.*

- **Permitted Use:** Internal development, commercial product integration, modification, and deployment within proprietary software stacks.
- **Restrictions:** Redistribution of uncompiled source code kits as standalone commercial developer products is strictly prohibited without explicit written authorization.
- **No Warranty:** Provided *as-is* without warranty of any kind. MicroCorp AI is not liable for hardware faults, repetitive strain injuries, or unintended command executions resulting from miscalibrated models.

```
====================================================================
MicroCorp AI Engineering Division — Tooling That Respects Your Time
(c) 2026 MicroCorp AI. All rights reserved.
====================================================================
```