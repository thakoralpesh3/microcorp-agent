"""
MicroCorp AI - The Agency Agents Integration Manager
Indexes and orchestrates 327+ specialized AI agent personas across 18 professional divisions
from the 'agency-agents' repository (msitarzewski/agency-agents).
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MicroCorp.AgencyAgentsManager")

BASE_DIR = Path(__file__).parent.parent.resolve()
AGENCY_DIR = BASE_DIR / "agency_agents"
DIVISIONS_JSON_PATH = AGENCY_DIR / "divisions.json"

class AgencyAgentsManager:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or AGENCY_DIR
        self.divisions_file = self.root_dir / "divisions.json"
        self.divisions: Dict[str, Dict[str, Any]] = {}
        self.agents: Dict[str, Dict[str, Any]] = {}
        self._is_indexed = False
        self._ensure_indexed()

    def _ensure_indexed(self):
        """Indexes all divisions and agent persona files into fast memory cache."""
        if self._is_indexed:
            return

        if not self.root_dir.exists():
            logger.warning(f"Agency agents root directory not found at {self.root_dir}")
            return

        # 1. Load divisions metadata
        if self.divisions_file.exists():
            try:
                with open(self.divisions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.divisions = data.get("divisions", {})
            except Exception as e:
                logger.error(f"Failed to load divisions.json: {e}")

        # 2. Index all agent markdown files across all divisions
        count = 0
        for md_path in self.root_dir.glob("*/*.md"):
            # Exclude non-division utility folders
            parts = md_path.relative_to(self.root_dir).parts
            if len(parts) < 2:
                continue
            division_slug = parts[0]
            if division_slug in ["scripts", "examples", "integrations", "strategy"]:
                continue

            try:
                content = md_path.read_text(encoding="utf-8")
                agent_info = self._parse_agent_markdown(md_path, division_slug, content)
                if agent_info:
                    self.agents[agent_info["id"]] = agent_info
                    count += 1
            except Exception as e:
                logger.warning(f"Error parsing agent at {md_path}: {e}")

        # Also populate agent counts per division
        for div_id, div_data in self.divisions.items():
            matching_count = sum(1 for a in self.agents.values() if a["division"] == div_id)
            div_data["agent_count"] = matching_count

        self._is_indexed = True
        logger.info(f"Loaded {len(self.divisions)} Agency divisions and {len(self.agents)} specialized agent personas.")

    def _parse_agent_markdown(self, path: Path, division: str, content: str) -> Optional[Dict[str, Any]]:
        """Parses frontmatter and structured sections from an agent markdown file."""
        frontmatter = {}
        body = content

        if content.startswith("---"):
            fm_parts = content.split("---", 2)
            if len(fm_parts) >= 3:
                raw_fm = fm_parts[1].strip()
                body = fm_parts[2].strip()
                for line in raw_fm.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        frontmatter[k.strip()] = v.strip().strip('"').strip("'")

        name = frontmatter.get("name") or path.stem.replace(f"{division}-", "").replace("-", " ").title()
        description = frontmatter.get("description", "")
        color = frontmatter.get("color", "blue")
        emoji = frontmatter.get("emoji", "🤖")
        vibe = frontmatter.get("vibe", "")

        # Extract Mission and Critical Rules sections if present
        mission = ""
        rules = ""

        mission_match = re.search(r'## 🎯 Your Core Mission.*?(?=##|\Z)', body, re.DOTALL | re.IGNORECASE)
        if mission_match:
            mission = mission_match.group(0).strip()

        rules_match = re.search(r'## 🚨 Critical Rules You Must Follow.*?(?=##|\Z)', body, re.DOTALL | re.IGNORECASE)
        if rules_match:
            rules = rules_match.group(0).strip()

        agent_id = path.stem

        return {
            "id": agent_id,
            "name": name,
            "division": division,
            "description": description,
            "color": color,
            "emoji": emoji,
            "vibe": vibe,
            "file_name": path.name,
            "relative_path": str(path.relative_to(self.root_dir)),
            "mission": mission,
            "rules": rules,
            "full_content": content
        }

    def get_divisions(self) -> Dict[str, Dict[str, Any]]:
        """Returns metadata dictionary for all 18 divisions keyed by division id."""
        self._ensure_indexed()
        result = {}
        for div_id, d in sorted(self.divisions.items(), key=lambda x: x[1].get("label", x[0])):
            label = d.get("label", div_id.replace("-", " ").title())
            result[div_id] = {
                "id": div_id,
                "name": label,
                "label": label,
                "description": d.get("description", f"Specialized {label} Division"),
                "icon": d.get("icon", "Folder"),
                "color": d.get("color", "#3B82F6"),
                "agent_count": d.get("agent_count", 0)
            }
        return result

    def get_division(self, division_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single division by id or slug."""
        self._ensure_indexed()
        divs = self.get_divisions()
        return divs.get(division_id.lower().replace("_", "-"))

    def get_agents(self, division: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns a list of agents matching division or search query."""
        self._ensure_indexed()
        agents_list = list(self.agents.values())

        if division:
            agents_list = [a for a in agents_list if a["division"].lower() == division.lower()]

        if search:
            q = search.lower().strip()
            agents_list = [
                a for a in agents_list
                if q in a["name"].lower() or q in a["description"].lower() or q in a["id"].lower() or q in a["vibe"].lower()
            ]

        # Return lightweight representations
        return [
            {
                "id": a["id"],
                "name": a["name"],
                "division": a["division"],
                "description": a["description"],
                "color": a["color"],
                "emoji": a["emoji"],
                "vibe": a["vibe"]
            }
            for a in sorted(agents_list, key=lambda x: x["name"])
        ]

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Returns full agent details including mission and rules."""
        self._ensure_indexed()
        # Direct key match
        if agent_id in self.agents:
            return self.agents[agent_id]
        # Match by stem or without prefix
        for aid, a in self.agents.items():
            if aid.endswith(agent_id) or a["name"].lower() == agent_id.lower().replace("-", " "):
                return a
        return None

    def match_agent_for_task(self, title: str, domain: str = "", requirements: str = "") -> Dict[str, Any]:
        """
        Intelligently matches a project, sprint, or task to the best specialized Agency Agent persona.
        """
        self._ensure_indexed()
        text = f"{title} {domain} {requirements}".lower()

        # Specific high-priority keyword rules
        if any(w in text for w in ["security", "audit", "threat", "vulnerability", "cve", "auth bypass"]):
            agent = self.get_agent("security-code-reviewer") or self.get_agent("security-threat-modeler")
            if agent: return agent

        if any(w in text for w in ["fastapi", "backend", "api", "microservice", "rest api", "endpoint"]):
            agent = self.get_agent("engineering-backend-architect") or self.get_agent("engineering-api-platform-engineer")
            if agent: return agent

        if any(w in text for w in ["frontend", "react", "vue", "ui", "css", "tailwind", "component"]):
            agent = self.get_agent("engineering-frontend-developer") or self.get_agent("design-ui-designer")
            if agent: return agent

        if any(w in text for w in ["database", "sql", "postgres", "mysql", "indexing", "sqlite"]):
            agent = self.get_agent("engineering-database-optimizer")
            if agent: return agent

        if any(w in text for w in ["docker", "devops", "kubernetes", "ci/cd", "pipeline", "deploy"]):
            agent = self.get_agent("engineering-devops-automator")
            if agent: return agent

        if any(w in text for w in ["proposal", "bid", "quote", "client pitch", "rfp"]):
            agent = self.get_agent("sales-proposal-writer") or self.get_agent("sales-sales-engineer")
            if agent: return agent

        if any(w in text for w in ["marketing", "growth", "newsletter", "copywriting", "seo", "traffic"]):
            agent = self.get_agent("marketing-growth-hacker") or self.get_agent("marketing-content-strategist")
            if agent: return agent

        if any(w in text for w in ["data pipeline", "etl", "scraping", "crawler", "pandas"]):
            agent = self.get_agent("engineering-data-engineer")
            if agent: return agent

        if any(w in text for w in ["mobile", "android", "ios", "apk", "flutter", "react native"]):
            agent = self.get_agent("engineering-mobile-app-builder")
            if agent: return agent

        if any(w in text for w in ["ai", "llm", "rag", "embedding", "vector", "gemini"]):
            agent = self.get_agent("engineering-ai-engineer") or self.get_agent("engineering-rag-pipeline-engineer")
            if agent: return agent

        # General scoring algorithm across all agents
        best_agent = None
        best_score = -1

        for a in self.agents.values():
            score = 0
            name_words = a["name"].lower().split()
            desc_words = a["description"].lower().split()

            for w in name_words:
                if len(w) > 3 and w in text:
                    score += 10

            for w in desc_words:
                if len(w) > 4 and w in text:
                    score += 2

            if a["division"].lower() in text:
                score += 5

            if score > best_score:
                best_score = score
                best_agent = a

        if best_agent and best_score > 0:
            return best_agent

        # Default fallback persona
        return self.get_agent("engineering-backend-architect") or list(self.agents.values())[0]

    def build_persona_system_prompt(self, agent_dict: Dict[str, Any], base_prompt: str = "") -> str:
        """
        Synthesizes the Agency persona's identity, core mission, and critical rules
        directly into the LLM system prompt.
        """
        name = agent_dict.get("name", "Senior Systems Specialist")
        emoji = agent_dict.get("emoji", "🤖")
        division = agent_dict.get("division", "Engineering").title()
        vibe = agent_dict.get("vibe", "")
        mission = agent_dict.get("mission", "")
        rules = agent_dict.get("rules", "")

        persona_header = f"""# THE AGENCY SPECIALIZED AI SPECIALIST PERSONA
You are executing this task as **{name}** {emoji} from The Agency's **{division} Division**.
{f"Vibe / Philosophy: {vibe}" if vibe else ""}

{mission if mission else f"## 🎯 Your Core Mission\nExecute {name} responsibilities with extreme structural discipline, clean code, and production reliability."}

{rules if rules else "## 🚨 Critical Rules You Must Follow\n- Maintain defensive programming and zero unhandled errors\n- Never produce non-functional placeholders or half-finished code\n- Adhere to strict type hints and documentation standards"}
"""
        if base_prompt:
            return f"{persona_header}\n\n==================================================\n# ENTERPRISE CONTEXT\n{base_prompt}"
        return persona_header

# Global singleton
agency_agents_manager = AgencyAgentsManager()
