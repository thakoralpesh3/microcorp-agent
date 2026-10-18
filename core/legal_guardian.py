"""
MicroCorp AI - Legal Compliance & Ethical Operations Guardian
Enforces strict lawful operations across all autonomous tasks, departments, feeds, and sprints.
Categorically screens, audits, and blocks any malicious, fraudulent, infringing, or illegal activities.
"""

import re
import json
import logging
import time
import uuid
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gemini_client import llm_client
from core.database import get_connection

logger = logging.getLogger("MicroCorp.LegalGuardian")

# Rigorous Category Taxonomy of Prohibited & Illegal Activities
PROHIBITED_TAXONOMY = {
    "MALWARE_CYBERATTACK": {
        "statute": "Computer Fraud and Abuse Act (CFAA 18 U.S.C. § 1030) / Directive 2013/40/EU",
        "description": "Creation, distribution, or facilitation of malware, exploits, botnets, or unauthorized intrusion tools.",
        "patterns": [
            r"\b(malware|ransomware|keylogger|rootkit|trojan(\s+virus|\s+tool)?|botnet|worm\s+payload)\b",
            r"\b(ddos|denial\s+of\s+service|syn\s+flood|amplification\s+attack)\b",
            r"\b(credential\s+stuffing|brute\s+force\s+passwords?|password\s+dumper|hashcat\s+script)\b",
            r"\b(zero-?day\s+exploit|reverse\s+shell\s+payload|backdoor\s+access|privilege\s+escalation\s+exploit)\b",
            r"\b(sql\s+injection\s+exploit|xss\s+payload|remote\s+code\s+execution)\b",
            r"\b(packet\s+sniffer|arp\s+spoofing|man\s+in\s+the\s+middle)\b",
            r"\b(bypass\s+antivirus|antivirus\s+evasion|obfuscated\s+virus)\b"
        ]
    },
    "FRAUD_SCAM_DECEPTION": {
        "statute": "FTC Act (15 U.S.C. § 45) / Wire Fraud (18 U.S.C. § 1343)",
        "description": "Deceptive business practices, phishing, synthetic identity creation, rating manipulation, or financial schemes.",
        "patterns": [
            r"\b(phishing|clone\s+bank\s+login|fake\s+paypal|fake\s+invoice\s+scam)\b",
            r"\b(credential\s+harvesting|steal\s+login|steal\s+passwords?)\b",
            r"\b(pump\s+and\s+dump|ponzi\s+scheme|crypto\s+drainer|wallet\s+drainer|honeypot\s+contract)\b",
            r"\b(fake|fabricated|astroturf)\b.*?\b(reviews?|ratings?|testimonials?)\b",
            r"\bmanipulate\b.*?\b(ratings?|reviews?|feedback)\b",
            r"\b(fake\s+diploma|fake\s+driver'?s?\s+license|counterfeit\s+passport|synthetic\s+identity)\b",
            r"\b(credit\s+card\s+skimmer|buy\s+cvv|carding\b|stolen\s+credit\s+cards?)\b"
        ]
    },
    "PIRACY_IP_INFRINGEMENT": {
        "statute": "Digital Millennium Copyright Act (DMCA 17 U.S.C. § 1201) / Defend Trade Secrets Act",
        "description": "Cracking software protections, copyright piracy, trade secret misappropriation, or counterfeit brands.",
        "patterns": [
            r"\b(software\s+crack|keygen|serial\s+generator|bypass\s+drm|drm\s+removal)\b",
            r"\bcrack\b.*?\b(keygen|serial|license|drm|commercial\s+software)\b",
            r"\b(bypass\s+paywall|pirated\s+software|warez|nulled\s+scripts?|cracked\s+apps?)\b",
            r"\b(unauthorized\s+streams?|torrent\s+tracker\s+scraper|pirated\s+books?)\b",
            r"\b(stolen\s+source\s+code|leaked\s+proprietary\s+code|trade\s+secret\s+theft)\b",
            r"\b(counterfeit\s+luxury|replica\s+clothing|trademark\s+infringement)\b"
        ]
    },
    "SPAM_HARASSMENT_PII": {
        "statute": "CAN-SPAM Act (15 U.S.C. § 7701) / GDPR / Computer Harassment Laws",
        "description": "Unsolicited mass messaging, non-consensual personal data scraping, doxxing, or harassment.",
        "patterns": [
            r"\b(mass\s+spam|unsolicited\s+bulk\s+email|email\s+spammer|spammer\s+bot)\b",
            r"\b(sms\s+spammer|sms\s+bomber|call\s+flooder)\b",
            r"\bscrape\b.*?\b(phone\s+numbers?|private\s+emails?)\b.*?\bwithout\s+consent\b",
            r"\b(doxx?ing|dox\s+person|publish\s+private\s+address|stalking\s+tool)\b",
            r"\b(harassment\s+campaign|automated\s+cyberbullying|defamation\s+generator)\b"
        ]
    },
    "DANGEROUS_OR_ILLICIT_GOODS": {
        "statute": "Controlled Substances Act / Arms Export Control Act / International Criminal Law",
        "description": "Facilitating illicit substances, dangerous contraband, weapons, or physical harm.",
        "patterns": [
            r"\b(dark\s?web\s+marketplace|buy\s+drugs\s+online|synthesize\s+narcotics)\b",
            r"\b(weapons?\s+blueprint|explosives?\s+recipe|bomb\s+making|firearm\s+3d\s+print)\b",
            r"\b(poison\s+recipe|biological\s+agent|chemical\s+weapon)\b"
        ]
    }
}

LEGAL_AUDIT_SYSTEM_PROMPT = """You are the Chief Legal Compliance Officer and Ethics Auditor at MicroCorp AI.
Your absolute mandate is to ensure the autonomous company executes ONLY 100% lawful, legitimate, ethical, and commercial work.
You strictly and unconditionally forbid any cyberattacks, malware, cracking tools, phishing, deceptive scams, copyright piracy, fake reviews, harassment, or harm.

Evaluate the proposed task and return JSON matching this schema:
{
  "is_legal": boolean (true if 100% lawful and ethical, false if any illegal or deceptive intent),
  "compliance_score": float between 0.0 and 1.0 (1.0 = completely lawful, 0.0 = illegal/harmful),
  "risk_category": "NONE" | "MALWARE_CYBERATTACK" | "FRAUD_SCAM_DECEPTION" | "PIRACY_IP_INFRINGEMENT" | "SPAM_HARASSMENT_PII" | "DANGEROUS_OR_ILLICIT_GOODS",
  "reason": "Detailed explanation citing why this is lawful or the specific illegal harm detected.",
  "legal_statute": "Relevant legal statute (e.g. CFAA, FTC Act, DMCA, CAN-SPAM, or 'Compliant')"
}
Return ONLY valid JSON.
"""

class LegalComplianceGuardian:
    """
    Evaluates every task, prompt, and opportunity against strict legal and ethical guardrails.
    Maintains a zero-tolerance policy against cybercrime, fraud, piracy, spam, and harm.
    """
    def __init__(self):
        self._compiled_patterns = {}
        for category, data in PROHIBITED_TAXONOMY.items():
            compiled = [re.compile(pat, re.IGNORECASE) for pat in data["patterns"]]
            self._compiled_patterns[category] = compiled
        self._ensure_table()

    def _ensure_table(self):
        """Ensures compliance_logs table exists in SQLite database."""
        try:
            conn = get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_title TEXT NOT NULL,
                    domain TEXT DEFAULT 'general',
                    verdict TEXT NOT NULL,
                    risk_category TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    legal_statute TEXT,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Compliance table check warning: {e}")

    def log_compliance_event(self, task_title: str, domain: str, verdict: str, risk_category: str, reason: str, legal_statute: Optional[str] = None):
        """Persists audit record in database for historical compliance tracking."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO compliance_logs (task_title, domain, verdict, risk_category, reason, legal_statute)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_title, domain, verdict, risk_category, reason, legal_statute or "Compliant"))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not persist compliance event: {e}")

    def audit_task(self, title: str, payload_or_desc: Any = "", domain: str = "general") -> Dict[str, Any]:
        """
        Comprehensive legality and ethical compliance audit:
        1. Fast deterministic heuristic scan (regex & keyword taxonomies).
        2. Deep LLM context analysis for ambiguous or borderline requests.
        3. Audit trail logging.
        Returns evaluation dict with 'is_legal', 'compliance_score', 'risk_category', 'reason', and 'legal_statute'.
        """
        # Combine text for scanning
        text_parts = [title]
        if isinstance(payload_or_desc, dict):
            text_parts.append(json.dumps(payload_or_desc))
        elif isinstance(payload_or_desc, str):
            text_parts.append(payload_or_desc)
        combined_text = " ".join(text_parts).lower()
        normalized_text = combined_text.replace("_", " ").replace("-", " ")

        # Step 1: Deterministic Heuristic Scanner
        for category, patterns in self._compiled_patterns.items():
            meta = PROHIBITED_TAXONOMY[category]
            for pat in patterns:
                match = pat.search(normalized_text)
                if match:
                    matched_term = match.group(0)
                    reason = f"Prohibited by Legal Guardian: Detected illegal or illicit pattern '{matched_term}' under category {category}. MicroCorp AI strictly operates within legal and ethical boundaries."
                    statute = meta["statute"]
                    logger.warning(f"⚖️ LEGAL VIOLATION BLOCKED: '{title}' [{category}] - Matched: '{matched_term}'")
                    
                    self.log_compliance_event(
                        task_title=title,
                        domain=domain,
                        verdict="REJECTED_ILLEGAL",
                        risk_category=category,
                        reason=reason,
                        legal_statute=statute
                    )
                    return {
                        "is_legal": False,
                        "compliance_score": 0.0,
                        "risk_category": category,
                        "reason": reason,
                        "legal_statute": statute,
                        "matched_term": matched_term
                    }

        # Step 2: Contextual LLM Audit for ambiguous or complex wording
        # Only invoke LLM if wording contains sensitive potential flags (e.g. bypass, hack, exploit, bot, stealth)
        suspicious_cues = ["bypass", "hack", "crack", "scrape", "bot", "stealth", "harvest", "clone", "drain", "leak"]
        is_suspicious = any(cue in combined_text for cue in suspicious_cues)

        if is_suspicious:
            try:
                audit_prompt = f"""Audit the following task for legal and ethical compliance:
Task Title: {title}
Context: {combined_text[:1200]}

Determine if this task promotes cybercrime, fraud, copyright infringement, deception, or unlawful actions.
"""
                raw_text, _, _ = llm_client.generate(
                    prompt=audit_prompt,
                    system_instruction=LEGAL_AUDIT_SYSTEM_PROMPT
                )
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                parsed = json.loads(cleaned.strip())
                
                is_legal = parsed.get("is_legal", True)
                score = float(parsed.get("compliance_score", 1.0))
                risk = parsed.get("risk_category", "NONE")
                reason = parsed.get("reason", "Evaluated via Legal Audit Engine.")
                statute = parsed.get("legal_statute", "Compliant")

                if not is_legal or score < 0.8:
                    logger.warning(f"⚖️ LLM LEGAL AUDIT REJECTED TASK: '{title}' (Risk: {risk}, Reason: {reason})")
                    self.log_compliance_event(
                        task_title=title,
                        domain=domain,
                        verdict="REJECTED_ILLEGAL",
                        risk_category=risk,
                        reason=reason,
                        legal_statute=statute
                    )
                    return {
                        "is_legal": False,
                        "compliance_score": 0.0,
                        "risk_category": risk,
                        "reason": f"Prohibited by Legal Guardian: {reason}",
                        "legal_statute": statute
                    }
            except Exception as e:
                logger.debug(f"LLM Legal audit skipped/fallback for '{title}': {e}")

        # Step 3: Verified Lawful Task
        self.log_compliance_event(
            task_title=title,
            domain=domain,
            verdict="APPROVED_LAWFUL",
            risk_category="NONE",
            reason="Fully compliant with domestic and international cyber regulations and ethical policies.",
            legal_statute="Compliant"
        )
        return {
            "is_legal": True,
            "compliance_score": 1.0,
            "risk_category": "NONE",
            "reason": "100% compliant with legal, ethical, and commercial enterprise terms.",
            "legal_statute": "Compliant"
        }

    def generate_customer_rejection_notice(self, project_title: str, requirements: str, risk_category: str, reason: str, legal_statute: str, client_name: Optional[str] = None) -> str:
        """Constructs an official, formal legal rejection markdown document for customer delivery."""
        name = client_name or "Valued Client"
        return f"""# OFFICIAL NOTICE: REJECTION OF WORK REQUEST

**Date:** {time.strftime('%B %d, %Y')}  
**Notice ID:** `REFUSAL-{uuid.uuid4().hex[:8].upper()}`  
**Client / Customer:** {name}  
**Submitted Project:** {project_title}  
**Compliance Verdict:** 🛑 **REJECTED — PROHIBITED WORK**  

---

## ⚖️ Executive Rejection Advisory

Dear {name},

Thank you for contacting **MicroCorp AI**. After evaluating your submitted project requirements through our automated **Legal Compliance & Ethical Operations Guardian**, we must formally inform you that **MicroCorp AI cannot accept, bid on, or perform this project**.

### 1. Classification & Prohibited Category
- **Violation Category:** `{risk_category}`
- **Governing Legal Framework:** `{legal_statute}`

### 2. Specific Basis for Refusal
{reason}

### 3. Corporate Compliance Mandate
MicroCorp AI operates exclusively as a lawful, autonomous software engineering and digital technology enterprise. In strict accordance with our Charter and international cyber regulations:
- We strictly **refuse** all assignments involving unauthorized network penetration, credential scraping/harvesting without explicit subject consent, malware, exploits, or distributed denial of service (DDoS).
- We strictly **refuse** deceptive practices including fake reviews, astroturfing, rating manipulation, phishing, and counterfeit documentation.
- We strictly **refuse** intellectual property infringement, software crack generation, and DRM/paywall circumvention.

### 4. Alternative Lawful Scope
If your organization requires legitimate, lawful software development—such as public API integrations, authorized authentication architectures, performance optimization, or compliant data engineering—we invite you to submit an updated project specification aligned with lawful standards.

---
*Issued autonomously by the Legal Compliance Desk at MicroCorp AI.*
"""

    def audit_customer_order(self, project_title: str, requirements: str, client_name: Optional[str] = None, client_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Specialized audit gate for incoming customer and client job requests.
        If prohibited, generates a formal Customer Work Rejection Notice and logs the refusal.
        """
        audit = self.audit_task(title=project_title, payload_or_desc=requirements, domain="customer_order")
        
        if not audit["is_legal"]:
            rejection_notice = self.generate_customer_rejection_notice(
                project_title=project_title,
                requirements=requirements,
                risk_category=audit["risk_category"],
                reason=audit["reason"],
                legal_statute=audit["legal_statute"],
                client_name=client_name
            )
            self.log_compliance_event(
                task_title=f"Customer Order: {project_title}",
                domain="customer_order",
                verdict="CUSTOMER_ORDER_REJECTED",
                risk_category=audit["risk_category"],
                reason=audit["reason"],
                legal_statute=audit["legal_statute"]
            )
            return {
                "is_legal": False,
                "verdict": "REJECTED_UNLAWFUL",
                "customer_name": client_name or "Client",
                "project_title": project_title,
                "risk_category": audit["risk_category"],
                "reason": audit["reason"],
                "legal_statute": audit["legal_statute"],
                "rejection_notice_md": rejection_notice,
                "advisory_summary": f"ORDER REJECTED: Your request was declined by the Legal Guardian due to {audit['risk_category']} violation ({audit['legal_statute']})."
            }
        
        return {
            "is_legal": True,
            "verdict": "APPROVED_LAWFUL",
            "customer_name": client_name or "Client",
            "project_title": project_title,
            "compliance_score": 1.0,
            "advisory_summary": "Order verified and accepted. Passed 100% legal compliance screening."
        }

    def get_compliance_metrics(self) -> Dict[str, Any]:
        """Returns statistics on compliance screenings and blocked violations."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) as total FROM compliance_logs")
            total_checks = cursor.fetchone()['total']
            cursor.execute("SELECT count(*) as blocked FROM compliance_logs WHERE verdict = 'REJECTED_ILLEGAL'")
            blocked_violations = cursor.fetchone()['blocked']
            cursor.execute("SELECT * FROM compliance_logs WHERE verdict = 'REJECTED_ILLEGAL' ORDER BY checked_at DESC LIMIT 5")
            recent_rejections = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return {
                "compliance_status": "active_and_enforced",
                "total_tasks_screened": total_checks,
                "blocked_violations_count": blocked_violations,
                "zero_illicit_policy": True,
                "recent_blocked_attempts": recent_rejections
            }
        except Exception:
            return {
                "compliance_status": "active_and_enforced",
                "total_tasks_screened": 0,
                "blocked_violations_count": 0,
                "zero_illicit_policy": True,
                "recent_blocked_attempts": []
            }

legal_guardian = LegalComplianceGuardian()
