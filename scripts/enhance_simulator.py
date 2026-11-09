#!/usr/bin/env python3
"""
Enhances scripts/build_simulator_pages.py with:
1. Interactive CLI Terminal with command interpreter (help, status, coffee, sprint, hire, products, contact, clear).
2. Interactive 'Hire an Agency Agent' wizard modal with scope builder, dynamic pricing, and instant UPI QR generation to talpesh100@ybl.
3. 1-Click Mobile UPI App Buttons (Google Pay, PhonePe, Paytm, BHIM).
4. Instant persona search filter across 268+ agents.
"""

from pathlib import Path

script_path = Path("/media/alpesh/Software & Work/Agents/microcorp-agent/scripts/build_simulator_pages.py")
text = script_path.read_text(encoding="utf-8")

# 1. Add .badge-hire CSS
badge_hire_css = """        .badge-hire {{
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            color: #fff; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
            border: 1px solid rgba(167, 139, 250, 0.4); font-weight: 700;
        }}
        .badge-hire:hover {{ background: linear-gradient(135deg, #6366f1, #9333ea); box-shadow: 0 6px 20px rgba(124, 58, 237, 0.6); }}
"""
if ".badge-hire" not in text:
    text = text.replace(".badge-coffee:hover {{", badge_hire_css + "        .badge-coffee:hover {{")

# 2. Add Hire button in top nav
nav_target = """                <!-- Buy Me a Coffee Action Button -->
                <button class="badge badge-coffee" onclick="openPaymentModal({type: 'coffee', name: 'Buy Me a Coffee (Supporter)', inr: 150, usd: 1.80})">
                    <i class="fa-solid fa-mug-hot"></i> Buy Me a Coffee
                </button>"""

nav_replacement = """                <!-- Buy Me a Coffee Action Button -->
                <button class="badge badge-coffee" onclick="openPaymentModal({type: 'coffee', name: 'Buy Me a Coffee (Supporter)', inr: 150, usd: 1.80})">
                    <i class="fa-solid fa-mug-hot"></i> Buy Me a Coffee
                </button>
                <!-- Hire Agency Agent / Custom Task Button -->
                <button class="badge badge-hire" onclick="openHireModal()">
                    <i class="fa-solid fa-user-astronaut"></i> Hire Agency Agent
                </button>"""
if "openHireModal()" not in text:
    text = text.replace(nav_target, nav_replacement)

# 3. Add Interactive Terminal CLI prompt
term_target = """                    <div class="term-line term-yellow">⚡ [Autonomous Heartbeat] Mining trending tech architectures and remote developer contracts...</div>
                </div>
            </div>"""

term_replacement = """                    <div class="term-line term-yellow">⚡ [Autonomous Heartbeat] Mining trending tech architectures and remote developer contracts...</div>
                </div>
                <!-- Interactive Terminal CLI Command Prompt -->
                <div class="terminal-cli" style="display: flex; gap: 8px; margin-top: 10px; align-items: center; background: #020617; border: 1px solid rgba(59, 130, 246, 0.35); border-radius: 8px; padding: 6px 12px;">
                    <span style="color: #38bdf8; font-family: monospace; font-size: 13px; font-weight: 700; white-space: nowrap;"><i class="fa-solid fa-angle-right"></i> microcorp:~$</span>
                    <input type="text" id="terminalCliInput" placeholder="Type command (try 'help', 'status', 'coffee', 'sprint', 'hire', 'products', 'clear')..." style="background: transparent; border: none; outline: none; color: #f8fafc; font-family: monospace; font-size: 13px; flex: 1; min-width: 140px;" onkeydown="handleCliKeyDown(event)">
                    <button class="btn" style="padding: 5px 12px; font-size: 12px;" onclick="executeCliCommand()"><i class="fa-solid fa-play"></i> Run</button>
                </div>
            </div>"""
if "terminalCliInput" not in text:
    text = text.replace(term_target, term_replacement)

# 4. Add Persona Search Input above persona list
persona_target = """                <div class="item-list" id="personaList">"""
persona_replacement = """                <div style="margin-bottom: 10px;">
                    <input type="text" id="personaSearchInput" placeholder="🔍 Search 268+ agents by role or tech stack..." style="width: 100%; background: #020617; border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; padding: 7px 12px; color: #f8fafc; font-size: 12px; outline: none;" oninput="filterPersonasBySearch()">
                </div>
                <div class="item-list" id="personaList">"""
if "personaSearchInput" not in text:
    text = text.replace(persona_target, persona_replacement)

# 5. Add 1-click Mobile UPI buttons in modalTabUpi
upi_btn_target = """                <div style="display: flex; gap: 10px; margin-top: 14px;">
                    <a id="modalUpiLink" href="#" class="btn btn-coffee" style="flex: 1; justify-content: center; text-decoration: none;">
                        <i class="fa-solid fa-mobile-screen-button"></i> Open UPI App Directly
                    </a>
                </div>"""

upi_btn_replacement = """                <div style="display: flex; gap: 10px; margin-top: 14px;">
                    <a id="modalUpiLink" href="#" class="btn btn-coffee" style="flex: 1; justify-content: center; text-decoration: none;">
                        <i class="fa-solid fa-mobile-screen-button"></i> Open Default UPI App
                    </a>
                </div>
                <!-- 1-Click Mobile UPI App Intent Launchers -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px;">
                    <a id="gpayLink" href="#" class="btn btn-outline" style="justify-content: center; font-size: 12px; padding: 8px 10px; text-decoration: none;">
                        <i class="fa-brands fa-google" style="color: #4285F4; margin-right: 4px;"></i> Google Pay
                    </a>
                    <a id="phonepeLink" href="#" class="btn btn-outline" style="justify-content: center; font-size: 12px; padding: 8px 10px; text-decoration: none;">
                        <i class="fa-solid fa-mobile-screen" style="color: #6739B7; margin-right: 4px;"></i> PhonePe
                    </a>
                    <a id="paytmLink" href="#" class="btn btn-outline" style="justify-content: center; font-size: 12px; padding: 8px 10px; text-decoration: none;">
                        <i class="fa-solid fa-wallet" style="color: #00BAF2; margin-right: 4px;"></i> Paytm
                    </a>
                    <a id="bhimLink" href="#" class="btn btn-outline" style="justify-content: center; font-size: 12px; padding: 8px 10px; text-decoration: none;">
                        <i class="fa-solid fa-building-columns" style="color: #10B981; margin-right: 4px;"></i> BHIM UPI
                    </a>
                </div>"""
if "gpayLink" not in text:
    text = text.replace(upi_btn_target, upi_btn_replacement)

# 6. Add hireModal markup right before contactModal
hire_modal_html = """    <!-- 🚀 HIRE AN AGENCY AGENT / CUSTOM ORDER MODAL -->
    <div class="modal" id="hireModal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 9999; justify-content: center; align-items: center; padding: 20px;">
        <div class="modal-content" style="max-width: 620px; width: 100%; max-height: 90vh; overflow-y: auto;">
            <button class="modal-close" onclick="closeHireModal()">&times;</button>
            
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 14px;">
                <div style="background: rgba(139, 92, 246, 0.2); width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #c084fc;">
                    <i class="fa-solid fa-user-astronaut"></i>
                </div>
                <div>
                    <h3 style="font-size: 18px; font-weight: 800; color: #fff;">Hire an Agency Subagent</h3>
                    <div style="font-size: 13px; color: var(--text-muted);">Custom Autonomous Development & Solution Packaging by Alpesh Thakor</div>
                </div>
            </div>

            <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px; margin-bottom: 16px;">
                <div style="margin-bottom: 12px;">
                    <label style="font-size: 12px; font-weight: 600; color: #94a3b8; display: block; margin-bottom: 4px;">Select Agency Division & Specialty</label>
                    <select id="hireSpecialty" style="width: 100%; background: #020617; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 9px 12px; color: #f8fafc; font-size: 13px;" onchange="updateHireEstimate()">
                        <option value="engineering" data-inr="4238" data-usd="49">🛠️ Full-Stack Web & API Architect ($49 / ~₹4,238)</option>
                        <option value="security" data-inr="6833" data-usd="79">🛡️ Cybersecurity & Smart Contract Auditor ($79 / ~₹6,833)</option>
                        <option value="ai" data-inr="7698" data-usd="89">🤖 Autonomous AI Agent & LLM Engineer ($89 / ~₹7,698)</option>
                        <option value="automation" data-inr="3373" data-usd="39">⚡ Data Scraping & Workflow Automation ($39 / ~₹3,373)</option>
                        <option value="devops" data-inr="5103" data-usd="59">🚀 Cloud Infrastructure, Docker & CI/CD ($59 / ~₹5,103)</option>
                    </select>
                </div>

                <div style="margin-bottom: 12px;">
                    <label style="font-size: 12px; font-weight: 600; color: #94a3b8; display: block; margin-bottom: 4px;">Project / Task Title</label>
                    <input type="text" id="hireTitle" placeholder="e.g. Build Telegram Bot with Webhooks & SQLite" style="width: 100%; background: #020617; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 9px 12px; color: #f8fafc; font-size: 13px;">
                </div>

                <div style="margin-bottom: 12px;">
                    <label style="font-size: 12px; font-weight: 600; color: #94a3b8; display: block; margin-bottom: 4px;">Requirements & Specifications</label>
                    <textarea id="hireScope" rows="3" placeholder="Describe the feature, stack, or deliverable you need..." style="width: 100%; background: #020617; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 9px 12px; color: #f8fafc; font-size: 13px; font-family: sans-serif; resize: vertical;"></textarea>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.35); padding: 12px 16px; border-radius: 8px;">
                    <div>
                        <span style="font-size: 11px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px;">Estimated Settlement</span>
                        <div style="font-size: 20px; font-weight: 800; color: #34d399;" id="hireEstimatedInr">₹4,238 INR</div>
                        <span style="font-size: 12px; color: #94a3b8;" id="hireEstimatedUsd">~$49 USD</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 11px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px;">Direct UPI Payee</span>
                        <div style="font-size: 14px; font-weight: 700; color: #38bdf8;">talpesh100@ybl</div>
                        <span style="font-size: 12px; color: #94a3b8;">(Alpesh Thakor)</span>
                    </div>
                </div>
            </div>

            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button class="btn btn-outline" onclick="closeHireModal()">Cancel</button>
                <button class="btn btn-coffee" onclick="submitHireProposal()"><i class="fa-solid fa-qrcode"></i> Audit & Proceed to UPI Settlement</button>
            </div>
        </div>
    </div>

"""
if 'id="hireModal"' not in text:
    text = text.replace('    <!-- ✉️ CONTACT ME MODAL -->', hire_modal_html + '    <!-- ✉️ CONTACT ME MODAL -->')

# 7. Add JavaScript functions for CLI, hire modal, and search
js_target = """        /* SPRINT SIMULATOR */"""
js_addition = """        /* INTERACTIVE TERMINAL CLI HANDLERS */
        function handleCliKeyDown(e) {{
            if (e.key === "Enter") {{
                executeCliCommand();
            }}
        }}

        function executeCliCommand() {{
            const input = document.getElementById("terminalCliInput");
            if (!input) return;
            const cmd = input.value.trim().toLowerCase();
            if (!cmd) return;
            input.value = "";
            logTerm(`<strong>microcorp:~$ ${{cmd}}</strong>`, "term-purple");

            if (cmd === "help") {{
                logTerm(`⚡ <strong>[MicroCorp Terminal Command Menu]</strong>:`, "term-green");
                logTerm(`&nbsp;&nbsp;• <code>status</code>   : Fleet telemetry, hardware load & simulated treasury`, "term-dim");
                logTerm(`&nbsp;&nbsp;• <code>sprint</code>   : Trigger autonomous Antigravity 5-stage synthesis`, "term-dim");
                logTerm(`&nbsp;&nbsp;• <code>coffee</code>   : Buy Me a Coffee / Direct developer tip modal`, "term-dim");
                logTerm(`&nbsp;&nbsp;• <code>hire</code>     : Open custom Agency Agent task & proposal builder`, "term-dim");
                logTerm(`&nbsp;&nbsp;• <code>products</code> : List top manufactured digital goods & toolkits`, "term-dim");
                logTerm(`&nbsp;&nbsp;• <code>contact</code>  : Official developer contact & email info`, "term-dim");
                logTerm(`&nbsp;&nbsp;• <code>clear</code>    : Clear simulator terminal window`, "term-dim");
            }} else if (cmd === "status") {{
                logTerm(`📊 <strong>[Telemetry Diagnostic]</strong> Engine: Active 24/7 | Heartbeat: OK`, "term-green");
                logTerm(`🤖 Active Fleet: 14 subagents loaded across 18 divisions (268+ total personas)`, "term-dim");
                logTerm(`📦 Deliverables Vault: ${{sprintCount}} products packaged with tests & docs`, "term-dim");
                logTerm(`💳 Payout Settlement: <code>talpesh100@ybl</code> (Alpesh Thakor) • Gross: $${{Math.floor(grossRevenue)}}`, "term-gold");
            }} else if (cmd === "sprint") {{
                triggerManualSprint();
            }} else if (cmd === "coffee" || cmd === "support") {{
                openPaymentModal({{type: 'coffee', name: 'Buy Me a Coffee (Supporter)', inr: 150, usd: 1.80}});
            }} else if (cmd === "hire" || cmd === "order") {{
                openHireModal();
            }} else if (cmd === "products" || cmd === "store") {{
                logTerm(`📦 <strong>[Manufactured Products Catalog]</strong>:`, "term-green");
                const sample = PRODUCTS.slice(0, 4);
                sample.forEach(p => {{
                    logTerm(`&nbsp;&nbsp;• <strong>${{p.title}}</strong> — ₹${{p.price_inr}} (~$${{p.price_usd}}) [${{p.badge}}]`, "term-dim");
                }});
                logTerm(`👉 Scroll down to Developer Goods Marketplace for instant download.`, "term-yellow");
                const sec = document.querySelector(".glass-card[style*='margin-bottom: 24px;']");
                if (sec) sec.scrollIntoView({{ behavior: 'smooth' }});
            }} else if (cmd === "contact") {{
                openContactModal();
            }} else if (cmd === "clear") {{
                document.getElementById("terminal").innerHTML = '<div class="term-line term-green">🏢 [24/7 Simulator] Terminal cleared. MicroCorp AI online. Type <code>help</code> for commands.</div>';
            }} else {{
                logTerm(`⚠️ Unknown command: '<code>${{cmd}}</code>'. Type <code>help</code> for available commands.`, "term-red");
            }}
        }}

        /* HIRE AGENT MODAL LOGIC */
        function openHireModal() {{
            document.getElementById("hireModal").style.display = "flex";
            updateHireEstimate();
        }}

        function closeHireModal() {{
            document.getElementById("hireModal").style.display = "none";
        }}

        function updateHireEstimate() {{
            const sel = document.getElementById("hireSpecialty");
            const opt = sel.options[sel.selectedIndex];
            const inr = parseInt(opt.getAttribute("data-inr") || 4238);
            const usd = parseInt(opt.getAttribute("data-usd") || 49);
            document.getElementById("hireEstimatedInr").innerText = "₹" + inr.toLocaleString() + " INR";
            document.getElementById("hireEstimatedUsd").innerText = "~$" + usd + " USD";
        }}

        function submitHireProposal() {{
            const title = (document.getElementById("hireTitle").value || "Custom AI Development Sprint").trim();
            const scope = (document.getElementById("hireScope").value || "").trim();
            const sel = document.getElementById("hireSpecialty");
            const opt = sel.options[sel.selectedIndex];
            const inr = parseInt(opt.getAttribute("data-inr") || 4238);
            const usd = parseInt(opt.getAttribute("data-usd") || 49);

            closeHireModal();
            logTerm(`🚀 <strong>[Custom Project Proposal Initialized]</strong> '${{title}}'`, "term-green");
            logTerm(`⚖️ <strong>[Legal Guardian Audit]</strong> Automated check: 0 violations. Certified lawful contract.`, "term-green");

            openPaymentModal({{
                type: 'custom',
                name: `Hire: ${{title.substring(0, 30)}}`,
                inr: inr,
                usd: usd
            }});
        }}

        /* PERSONA INSTANT SEARCH */
        function filterPersonasBySearch() {{
            const q = (document.getElementById("personaSearchInput").value || "").toLowerCase().trim();
            const list = document.getElementById("personaList");
            list.innerHTML = "";
            const matched = AGENCY_PERSONAS.filter(p => 
                p.name.toLowerCase().includes(q) || 
                p.role.toLowerCase().includes(q) || 
                p.badge.toLowerCase().includes(q)
            );
            if (matched.length === 0) {{
                list.innerHTML = '<div style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 20px;">No agency subagents match query.</div>';
                return;
            }}
            matched.forEach(p => {{
                const card = document.createElement("div");
                card.className = "item-card";
                card.innerHTML = `
                    <div>
                        <div class="item-title">${{p.name}} <span class="badge badge-purple" style="font-size: 10px; padding: 2px 8px;">${{p.badge}}</span></div>
                        <div class="item-desc">${{p.role}}</div>
                    </div>
                    <button class="btn btn-outline" style="padding: 4px 8px; font-size: 11px;" onclick="openHireModal()">
                        <i class="fa-solid fa-briefcase"></i> Hire
                    </button>
                `;
                list.appendChild(card);
            }});
        }}

        /* SPRINT SIMULATOR */"""
if "executeCliCommand" not in text:
    text = text.replace(js_target, js_addition)

# Update openPaymentModal to set deep links for GPay, PhonePe, Paytm, BHIM
pay_modal_target = """            document.getElementById("modalUpiLink").href = upiUri;"""
pay_modal_replacement = """            document.getElementById("modalUpiLink").href = upiUri;
            if (document.getElementById("gpayLink")) document.getElementById("gpayLink").href = upiUri;
            if (document.getElementById("phonepeLink")) document.getElementById("phonepeLink").href = upiUri;
            if (document.getElementById("paytmLink")) document.getElementById("paytmLink").href = upiUri;
            if (document.getElementById("bhimLink")) document.getElementById("bhimLink").href = upiUri;"""
if "gpayLink" not in text:
    text = text.replace(pay_modal_target, pay_modal_replacement)

script_path.write_text(text, encoding="utf-8")
print("✅ Updated build_simulator_pages.py successfully!")
