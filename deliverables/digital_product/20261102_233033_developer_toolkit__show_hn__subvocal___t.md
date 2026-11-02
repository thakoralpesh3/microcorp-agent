# Developer Reference & Architecture Kit: Subvocal Integration
**Product Version:** 1.0.0-enterprise  
**Target Audience:** Systems Engineers, AI Developers, Accessibility Tooling Authors  
**License:** Commercial / Proprietary (See Section 6)

---

## 1. Product Title & Value Proposition

### Subvocal: Silent Neural-Text Interface Architecture Kit
Subvocal allows developers and power users to interface with their computers using silent, sub-audible speech patterns, surface EMG (electromyography) sensors, and edge-deployed transformer models. By capturing micro-muscular activations in the vocal tract without producing acoustic sound, Subvocal opens up new paradigms for hands-free, private, and high-throughput human-computer interaction.

```
+-------------------------------------------------------------------------+
                    SUBVOCAL ARCHITECTURE PIPELINE
+-------------------------------------------------------------------------+
 [ EMG Sensors ] ---> [ Signal Conditioning ] ---> [ Quantized Edge Model ]
      │                        │                           │
      ▼                        ▼                           ▼
 (Raw Voltages)        (Notch / Bandpass)         (Sub-token Outputs)
                                                           │
                                                           ▼
 [ OS Shell / App ] <--- [ Action Dispatcher ] <--- [ Context Resolver ]
+-------------------------------------------------------------------------+
```

### Key Value Propositions
- **Absolute Privacy in Public Spaces:** Execute terminal commands, dictate code, and control applications in open offices, flights, or confidential environments without emitting sound.
- **Ultra-Low Latency Edge Inference:** Sub-50ms round-trip from sensor acquisition to command dispatch via heavily quantized ONNX / TensorRT runtimes.
- **Developer-First CLI & SDK:** Zero-friction integration with existing Unix toolchains, IDEs, and custom automation scripts.
- **Deterministic State Machine:** Avoid hallucinating LLM interfaces by coupling intent recognition with strict grammar-constrained decoding.

---

## 2. Quick Start & Core Concepts

### Installation & CLI Verification
```bash
# Install the core CLI and daemon tooling
curl -sSL https://raw.githubusercontent.com/microcorp-ai/subvocal/main/install.sh | sh

# Verify installation and inspect version (must start in <30ms)
subvocal --version
```

### Core Concepts Syntax Reference

| Concept | Description | CLI / Code Equivalent |
| :--- | :--- | :--- |
| **Stream Session** | An active hardware-to-buffer pipeline capturing sensor metrics. | `subvocal session start --device /dev/emg0` |
| **Intent Grammar** | A BNF/JSON grammar constraining model outputs to valid system tokens. | `subvocal grammar load ./configs/terminal.json` |
| **Micro-Gesture** | A distinct muscular twitch mapped to a high-priority interrupt (e.g., Escape, Enter). | `subvocal bind gesture:jaw_clench --action "KEY_ESC"` |
| **Calibration Profile** | User-specific muscle voltage baseline ensuring cross-session accuracy. | `subvocal calibrate --profile dev_office` |
| **Confidence Threshold** | Minimum probability required before executing a triggered macro. | `--threshold 0.87` |

---

## 3. Production Code Patterns & Architecture Examples

The following implementation provides a complete, copy-paste ready Python module for initializing the Subvocal daemon, attaching a custom signal processor, and handling command execution with strict error boundaries and exit codes.

```python
#!/usr/bin/env python3
"""
Subvocal Daemon Listener & Command Dispatcher
Production-ready boilerplate for MicroCorp AI Subvocal integrations.
"""

import sys
import time
import json
import signal
from pathlib import Path
from typing import Dict, Any, Generator

# Exit code constants (Strict API contract)
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 64
EXIT_DEVICE_ERROR = 69
EXIT_INTERRUPT = 130

class SubvocalError(Exception):
    """Base exception for all Subvocal runtime errors."""
    def __init__(self, message: str, fix: str, exit_code: int):
        super().__init__(message)
        self.message = message
        self.fix = fix
        self.exit_code = exit_code

class DeviceNotFoundError(SubvocalError):
    def __init__(self, device_path: str):
        super().__init__(
            message=f"EMG sensor device not found at '{device_path}'.",
            fix=f"Check hardware connection or run `subvocal devices list` to find valid endpoints.",
            exit_code=EXIT_DEVICE_ERROR
        )

class ConfigNotFoundError(SubvocalError):
    def __init__(self, config_path: str):
        super().__init__(
            message=f"Configuration file not found at '{config_path}'.",
            fix=f"Run `subvocal init` to generate a default configuration file.",
            exit_code=EXIT_CONFIG_ERROR
        )


def load_config(path: str) -> Dict[str, Any]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise ConfigNotFoundError(str(cfg_path))
    
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SubvocalError(
            message=f"Malformed configuration JSON: {e.msg} at line {e.lineno}.",
            fix=f"Validate your JSON syntax or regenerate using `subvocal init --force`.",
            exit_code=EXIT_CONFIG_ERROR
        )


def mock_sensor_stream(device_path: str) -> Generator[Dict[str, float], None, None]:
    """Simulates real-time EMG sensor data streaming."""
    if device_path == "/dev/null-device":
        raise DeviceNotFoundError(device_path)
    
    # Simulation loop for demonstration purposes
    while True:
        yield {"timestamp": time.time(), "channel_1": 0.12, "channel_2": 0.85}
        time.sleep(0.05)


def handle_shutdown(signum, frame):
    sys.stderr.write("\n[Subvocal] Graceful shutdown initiated by user.\n")
    sys.exit(EXIT_SUCCESS)


def main() -> int:
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    config_path = "./subvocal.json"
    
    try:
        config = load_config(config_path)
        device = config.get("device_path", "/dev/emg0")
        
        print(f"[Subvocal] Initializing stream on {device}...", file=sys.stderr)
        
        for sample in mock_sensor_stream(device):
            # Hot path: Process sample, run inference, dispatch command
            if sample["channel_2"] > 0.80:
                print(json.dumps({"event": "trigger", "action": "cmd_execute", "confidence": 0.92}))
                sys.stdout.flush()

    except SubvocalError as err:
        sys.stderr.write(f"Error: {err.message}\n")
        sys.stderr.write(f"Fix:   {err.fix}\n")
        return err.exit_code
    except Exception as exc:
        sys.stderr.write(f"Error: Unexpected runtime failure: {exc}\n")
        sys.stderr.write(f"Fix:   Please report this stack trace to support@microcorp.ai\n")
        return 1
        
    return EXIT_SUCCESS

if __name__ == "__main__":
    sys.exit(main())
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Unbounded Floating-Point Thresholds
**The Mistake:** Hardcoding raw voltage thresholds (`> 3.3V`) across different users and environmental conditions.  
**Why it fails:** Muscle mass, skin hydration, and impedance shift hourly. A hardcoded threshold results in constant false triggers or total unresponsiveness.  
**The Fix:** Always utilize dynamic baseline normalization pipelines provided by the SDK:
```bash
# Correct: Calibrate per session to establish relative delta vectors
subvocal calibrate --duration 10s --output ./profiles/user_session.json
```

### ❌ Anti-Pattern 2: Raw Stack Traces on User Error
**The Mistake:** Allowing Python or C++ runtimes to dump uncaught tracebacks when a configuration file is missing or a device is disconnected.  
**Why it fails:** Destroys user trust, clutters CI logs, and violates modern CLI design principles.  
**The Fix:** Wrap all entrypoints in structured error handlers that explicitly state **what happened**, **why**, and **the exact command to run**.

### ❌ Anti-Pattern 3: Unconstrained Generative Inference
**The Mistake:** Feeding raw audio/EMG embeddings directly into an unconstrained 7B+ Large Language Model to guess terminal commands.  
**Why it fails:** Introduces massive latency (>800ms) and leads to catastrophic hallucinations (e.g., executing `rm -rf /` due to a stray muscle twitch).  
**The Fix:** Constrain output token generation using strict finite-state grammars or regex masks matched directly to allowed CLI verbs.

---

## 5. Performance & Optimization Tips

1. **Bypass the Python Interpreter on the Hot Path:** For maximum throughput, implement signal conditioning and digital filtering (Bandpass / Notch filters) in Rust or C++, communicating with consumers via Unix Domain Sockets or shared memory rings.
2. **Quantize to INT8 / FP16:** Ensure your inference models are compiled via TensorRT or ONNX Runtime with INT8 quantization enabled. This drops memory footprint below 45MB and guarantees inference times under 12ms on modern NPUs.
3. **TTY Detection for Automation Scripts:** Always check if stdout is attached to a TTY. Suppress progress bars, spinners, and ANSI color codes when piping output into another utility:
   ```python
   import sys
   if sys.stdout.isatty():
       # Render rich interactive status UI
       pass
   else:
       # Emit clean, stable JSON lines for parsing
       pass
   ```

---

## 6. Commercial License & Attribution Summary

```
====================================================================
MICROCORP AI COMMERCIAL LICENSE AGREEMENT (MACL-v1.4)
====================================================================
Copyright (c) 2026 MicroCorp AI. All rights reserved.

1. GRANT OF LICENSE: MicroCorp AI grants the licensee a perpetual,
   non-exclusive, non-transferable commercial right to integrate this 
   Developer Reference & Architecture Kit into internal production 
   systems, proprietary software applications, and device drivers.
2. RESTRICTIONS: Redistribution of this document or its accompanying 
   source code snippets as a standalone commercial developer product 
   without express written consent from MicroCorp AI is strictly prohibited.
3. NO WARRANTY: THIS PRODUCT IS PROVIDED "AS IS" WITHOUT WARRANTY OF 
   ANY KIND, EXPRESS OR IMPLIED. THE ENTIRE RISK AS TO THE QUALITY 
   AND PERFORMANCE OF THE PROGRAM IS WITH YOU.
====================================================================
```