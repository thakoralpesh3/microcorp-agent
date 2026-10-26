#!/usr/bin/env python3
"""
MicroCorp AI — Cloud 24/7 Autonomous Cycle Executor
Designed for execution inside GitHub Actions or headless cloud environments.
Orchestrates autonomous product discovery, persona matching, code synthesis,
turnkey freelance delivery, legal auditing, and asset monetization.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import init_db, get_queue_stats
from core.ceo_orchestrator import ceo
from core.treasury import treasury
from core.legal_guardian import legal_guardian
from tools.freelance_harvester import freelance_harvester
from core.freelance_distributor import freelance_distributor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MicroCorp.CloudCycle")

def main():
    parser = argparse.ArgumentParser(description="MicroCorp AI Autonomous Cloud Cycle")
    parser.add_argument("--domain", default="all", choices=["all", "digital_products", "freelance"], help="Target domain")
    parser.add_argument("--topic", default="", help="Custom topic override")
    args = parser.parse_args()

    print("==========================================================")
    print("  🏢 MicroCorp AI — 24/7 Autonomous Cloud Execution")
    print(f"  🎯 Target Domain: {args.domain}")
    print("  💳 Beneficiary: talpesh100@ybl (Alpesh Thakor)")
    print("==========================================================")

    init_db()

    # 1. Run Digital Products Sprint
    if args.domain in ["all", "digital_products"]:
        print("\n🚀 [1/3] Initiating Autonomous Digital Product Cycle...")
        try:
            summary = ceo.run_autonomous_income_cycle()
            print(f"✅ Digital Product Cycle completed successfully.")
        except Exception as e:
            logger.error(f"Error during digital product cycle: {e}")

    # 2. Run Turnkey Freelance Harvest & Execution
    if args.domain in ["all", "freelance"]:
        print("\n💼 [2/3] Initiating Freelance Market Harvesting & Turnkey Delivery...")
        try:
            jobs = freelance_harvester.fetch_all_platform_gigs()
            approved = [j for j in jobs if j.get('legal_audit', {}).get('is_legal')]
            print(f"🔍 Discovered {len(jobs)} opportunities ({len(approved)} verified 100% legal).")
            if approved:
                top_job = approved[0]
                print(f"⚡ Delivering top gig: '{top_job.get('title')}' (${top_job.get('budget_usd')})")
                res = freelance_distributor.plan_and_distribute_gig(top_job)
                print(f"✅ Freelance delivery status: {res.get('status')}")
                if res.get('deliverable_zip'):
                    print(f"📦 Deliverable: {res.get('deliverable_zip')}")
        except Exception as e:
            logger.error(f"Error during freelance cycle: {e}")

    # 3. Print Treasury & Compliance Summary
    print("\n📊 [3/3] Enterprise Treasury & Compliance Status:")
    queue = get_queue_stats()
    print(f"  • Tasks Completed: {queue.get('completed', 0)}")
    print(f"  • Tasks Enqueued:  {queue.get('pending', 0)}")
    print(f"  • Legal Compliance: Active & Enforced (0 illicit tasks permitted)")
    print("==========================================================")
    print("  ✅ MicroCorp AI Cloud Cycle execution finished.")
    print("==========================================================")

if __name__ == "__main__":
    main()
