"""
MicroCorp AI - Laptop Resource Guardian
Monitors CPU, RAM, battery status, and thermals to prevent laptop overheating and throttling.
"""

import time
import psutil
from typing import Dict, Any, Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MAX_CPU_PERCENT, MAX_MEMORY_PERCENT, MIN_BATTERY_PERCENT
from core.database import record_metrics

class ResourceGuardian:
    def __init__(self):
        self.last_check_time = 0
        self._cached_status: Dict[str, Any] = {}

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Reads current hardware telemetry from the laptop."""
        now = time.time()
        # Cache for 2 seconds to avoid excessive psutil calls
        if now - self.last_check_time < 2 and self._cached_status:
            return self._cached_status

        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        mem_percent = mem.percent

        battery = psutil.sensors_battery()
        if battery:
            battery_percent = battery.percent
            is_charging = battery.power_plugged
            secs_left = battery.secsleft
        else:
            # Desktop or battery sensor unavailable
            battery_percent = 100.0
            is_charging = True
            secs_left = -1

        status = {
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(mem_percent, 1),
            "memory_available_gb": round(mem.available / (1024 ** 3), 2),
            "battery_percent": round(battery_percent, 1),
            "is_charging": is_charging,
            "battery_seconds_left": secs_left,
            "timestamp": now
        }
        self._cached_status = status
        self.last_check_time = now
        return status

    def evaluate_safety(self) -> Tuple[bool, str]:
        """
        Determines if the laptop has sufficient headroom to spawn or run tasks.
        Returns (is_safe, reason).
        """
        telemetry = self.get_system_telemetry()
        
        import gc
        if telemetry["memory_percent"] > 82.0 or telemetry["cpu_percent"] > 75.0:
            gc.collect()

        if telemetry["cpu_percent"] > MAX_CPU_PERCENT:
            return False, f"CPU critical ({telemetry['cpu_percent']}% > {MAX_CPU_PERCENT}%). Throttling subagents."

        if telemetry["memory_percent"] > MAX_MEMORY_PERCENT:
            return False, f"Memory critical ({telemetry['memory_percent']}% > {MAX_MEMORY_PERCENT}%). Pausing spawns."

        if not telemetry["is_charging"] and telemetry["battery_percent"] < MIN_BATTERY_PERCENT:
            return False, f"Battery critical ({telemetry['battery_percent']}% and unplugged). Conserving laptop power."

        if telemetry["memory_percent"] > 80.0 or telemetry["cpu_percent"] > 70.0:
            return True, "Eco-Mode active: Low-footprint sequential execution enabled."

        return True, "Hardware operating smoothly within nominal thresholds."

    def compute_max_concurrent_workers(self, base_cap: int = 4) -> int:
        """Dynamically scales allowed parallel workers based on laptop load."""
        telemetry = self.get_system_telemetry()
        cpu = telemetry["cpu_percent"]
        mem = telemetry["memory_percent"]
        is_charging = telemetry["is_charging"]

        if cpu > 80 or mem > 85:
            return 1  # Low-footprint Eco mode
        elif cpu > 65 or mem > 75:
            return 2  # Moderate load mode
        elif not is_charging and telemetry["battery_percent"] < 30:
            return 2  # Battery saver mode
        
        return base_cap

    def log_telemetry_snapshot(self, active_subagents: int, queue_depth: int):
        """Persists snapshot into SQLite for dashboard charts."""
        t = self.get_system_telemetry()
        record_metrics(
            cpu=t["cpu_percent"],
            mem=t["memory_percent"],
            battery=t["battery_percent"],
            charging=t["is_charging"],
            active_subagents=active_subagents,
            queue_depth=queue_depth
        )

# Global singleton
guardian = ResourceGuardian()
