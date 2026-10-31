# Developer Toolkit: GPT-5.6 Sol can beat Factorio on peaceful mode
**Product Type:** Developer Reference & Architecture Kit  
**Target Audience:** AI Systems Engineers, LLM Agent Architects, Autonomous Automation Developers  
**Version:** 1.0.0-sol  

---

## 1. Product Title & Value Proposition

### Title
**GPT-5.6 Sol Factorio Autonomous Agent Kit: The Deterministic Automation Architecture**

### Value Proposition
Building autonomous agents that operate in complex, infinite-state environments usually results in high token burn, infinite loops, and catastrophic drift. This architecture kit provides the production-grade scaffolding, deterministic state-tracking schemas, and hierarchical planning loops required to let **GPT-5.6 Sol** autonomously design, bootstrap, scale, and optimize a running Factorio automation base (Peaceful Mode) from a raw crash site to a self-sustaining rocket launch.

Whether you are selling automation bots, building synthetic evaluators for general-purpose reasoning models, or exploring reinforcement learning through language models, this toolkit cuts integration time from weeks to hours by replacing loose prompt-chaining with strict parser-validated execution pipelines.

---

## 2. Quick Start & Core Concepts

### Core Concepts Matrix
| Concept | Description | Implementation Target |
| :--- | :--- | :--- |
| **Sol Hierarchical Reasoner** | Decouples strategic goal formulation from tactical tick-level execution. | `sol-planner.py` |
| **RLE (Runtime Lua Engine)** | A secure, sandboxed Remote Procedure Call (RPC) bridge into the Factorio Headless Lua API. | `rcon-bridge.go` |
| **Deterministic State Snapshots** | Compresses a 256MB map state into a token-efficient JSON topology graph. | `state-compressor.ts` |
| **Self-Healing Loop** | Catches entity collision errors, deadlocks, and resource starvation, generating automated fixes. | `guardrail-agent.py` |

### CLI Quick Start (`sol-ctl`)
```bash
# Initialize a local agent workspace
sol-ctl init --env production

# Validate connection to Factorio headless RCON instance
sol-ctl ping --host 127.0.0.1 --port 34156 --token-file ./secret.key

# Start the GPT-5.6 Sol autonomous execution loop with dry-run protection
sol-ctl run --model gpt-5.6-sol --mode peaceful --dry-run
```

> **Error Handling Rule:** If `sol-ctl` fails to connect, it never dumps a raw Python traceback. It returns:  
> `Error: RCON connection refused at 127.0.0.1:34156 — run 'sol-ctl config --verify' to check firewall settings and auth tokens.`

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Hierarchical Goal Decomposition (`sol-planner.py`)
This script demonstrates how to prompt GPT-5.6 Sol to output structured JSON action graphs rather than raw conversational text, ensuring zero syntax drift when communicating with game engines.

```python
#!/usr/bin/env python3
"""
Sol Hierarchical Planner - Core reasoning loop for GPT-5.6 Sol.
Ensures deterministic JSON schema output for Factorio RCON commands.
"""

import sys
import json
from typing import Dict, Any
from pydantic import BaseModel, Field, ValidationError

class FactorioAction(BaseModel):
    action_type: str = Field(..., description="e.g., BUILD,CRAFT,RESEARCH,LOGISTICS")
    target_entity: str = Field(..., description="Exact entity name in Factorio data raw")
    coordinates: Dict[str, int] = Field(..., description="{'x': int, 'y': int}")
    parameters: Dict[str, Any] = Field(default_factory=dict)

class SolExecutionPlan(BaseModel):
    current_objective: str
    reasoning: str
    actions: list[FactorioAction]

def parse_sol_response(raw_llm_output: str) -> SolExecutionPlan:
    """
    Parses LLM output against the strict execution schema.
    Fails with an actionable remediation message if validation fails.
    """
    try:
        data = json.loads(raw_llm_output)
        return SolExecutionPlan(**data)
    except json.JSONDecodeError as jde:
        print(f"Error: Malformed JSON from model — line {jde.lineno}, column {jde.colno}.", file=sys.stderr)
        print("Fix: Ensure model temperature is set <= 0.2 and system prompt enforces strict JSON mode.", file=sys.stderr)
        sys.exit(2)
    except ValidationError as ve:
        print(f"Error: Sol execution plan violates structural contract.", file=sys.stderr)
        print(f"Details: {ve.errors()}", file=sys.stderr)
        print("Fix: Review prompt engineering schema constraints in './prompts/sol-base.toml'.", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    # Mocking a validated Sol response stream
    mock_sol_payload = """
    {
        "current_objective": "Bootstrap initial iron plate production line",
        "reasoning": "Burner mining drills require coal fuel feed loop connected to stone furnaces.",
        "actions": [
            {
                "action_type": "BUILD",
                "target_entity": "burner-mining-drill",
                "coordinates": {"x": 12, "y": -4},
                "parameters": {"facing": "NORTH", "fuel_target": "coal"}
            },
            {
                "action_type": "BUILD",
                "target_entity": "stone-furnace",
                "coordinates": {"x": 12, "y": -2},
                "parameters": {"output": "iron-plate"}
            }
        ]
    }
    """
    plan = parse_sol_response(mock_sol_payload)
    print(f"[Sol-Engine] Objective Loaded: {plan.current_objective}")
    print(f"[Sol-Engine] Executing {len(plan.actions)} atomic actions via RCON...")
    sys.exit(0)
```

### Pattern 2: State Compression & Token Optimization (`state-compressor.ts`)
Raw game states contain gigabytes of tile, entity, and inventory data. This TypeScript module distills the environment into semantic spatial summaries for GPT-5.6 Sol's context window.

```typescript
/**
 * State Compressor for GPT-5.6 Sol
 * Reduces Factorio map dumps into high-density semantic markers.
 */

export interface EntityNode {
    name: string;
    pos: [number, number];
    status: 'active' | 'starved' | 'idle' | 'full';
}

export interface MapSnapshot {
    tick: number;
    inventory: Record<string, number>;
    power: {
        satisfaction: number; // 0.0 to 1.0
        production_kw: number;
        capacity_kw: number;
    };
    bottlenecks: string[];
    critical_nodes: EntityNode[];
}

export function compressGameState(rawDump: any): MapSnapshot {
    if (!rawDump || !rawDump.tick) {
        console.error("Error: Invalid map dump structure received from RCON bridge.");
        console.error("Fix: Verify Factorio headless mod 'sol-telemetry' is installed and active.");
        process.exit(10);
    }

    // Filter out cosmetic tiles, focus strictly on logistics and production entities
    const criticalNodes: EntityNode[] = (rawDump.entities || []).map((e: any) => ({
        name: e.name,
        pos: [Math.round(e.position.x), Math.round(e.position.y)],
        status: e.energy < 10 ? 'starved' : 'active'
    }));

    return {
        tick: rawDump.tick,
        inventory: rawDump.player_inventory || {},
        power: {
            satisfaction: rawDump.electric_network_stats?.satisfaction ?? 1.0,
            production_kw: rawDump.electric_network_stats?.production ?? 0,
            capacity_kw: rawDump.electric_network_stats?.capacity ?? 0
        },
        bottlenecks: rawDump.detected_bottlenecks || [],
        critical_nodes: criticalNodes
    };
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### 🚫 Anti-Pattern 1: Raw Conversational Prompting for Game Control
* **The Mistake:** Asking GPT-5.6 Sol *"Can you build a red science pack assembly line for me?"* and letting it output markdown paragraphs that you attempt to parse with regex.
* **Why it fails:** LLMs hallucinate coordinates and entity names (`assembler-1` instead of `assembling-machine-1`).
* **The Fix:** Always use JSON-mode enforcement, Pydantic/Zod schemas, and a hardcoded dictionary of valid Factorio entity prototypes.

### 🚫 Anti-Pattern 2: Tick-Rate Polling Overload
* **The Mistake:** Querying the game state via RCON every single game tick (60 times per second) to feed the model.
* **Why it fails:** Floods the network socket, causes massive CPU stalls in the game engine, and burns tokens uselessly.
* **The Fix:** Sample state changes using event-driven triggers (e.g., every 300 ticks, or when a research queue completes / production drops below 80%).

### 🚫 Anti-Pattern 3: Ignoring Peaceful Mode Resource Depletion Loops
* **The Mistake:** Assuming peaceful mode means infinite safety without supply chain planning, leading to deadlocks when initial coal patches run dry.
* **Why it fails:** Sol gets stuck trying to mine from depleted patches because it lacks automatic exploration and train-network expansion triggers.
* **The Fix:** Implement an automated ore-patch scanner that alerts Sol when reserves drop below 15,000 units, forcing a transition to automated rail logistics.

---

## 5. Performance & Optimization Tips

1. **Context Window Caching:** Leverage prompt caching for the immutable ruleset (Factorio recipe trees, crafting ratios, belt throughput limits). Only append the dynamic state snapshot (`MapSnapshot`) on each inference turn.
2. **Asynchronous RCON Batching:** Bundle multiple placement and configuration commands into a single Lua chunk execution payload (`rcon.print(game.forces[1].sol_execute(...))`) rather than sending sequential TCP packets.
3. **Deterministic Seed Locking:** Run evaluation benchmarks on fixed map seeds (e.g., Seed `13371337`) to measure Sol's time-to-automation metrics accurately across model iterations.
4. **Token Budgeting:** Restrict maximum completion tokens to `512` per planning cycle. A well-prompted Sol agent does not need to write essays; it needs to output compact array indices and coordinates.

---

## 6. Commercial License & Attribution Summary

### License Type
**Enterprise Developer Commercial License (EDCL-1.0)**

### Terms of Use
* **Permitted:** You may use, fork, adapt, and embed this architecture kit into commercial AI applications, agent platforms, internal engineering tools, and automated gaming bots.
* **Prohibited:** Redistribution of this toolkit as a standalone paid product, training dataset, or proprietary template without explicit written authorization from MicroCorp AI.
* **Warranty Disclaimer:** Provided *as-is* without warranty of any kind. MicroCorp AI assumes no liability for factory deadlocks, nuclear meltdowns, or infinite logistic loops generated by autonomous LLM agents.

> **Attribution Requirement:** Any published work, benchmark score, or commercial wrapper utilizing this kit must include the following notice in documentation:  
> *"Powered by the GPT-5.6 Sol Factorio Autonomous Agent Kit by MicroCorp AI."*