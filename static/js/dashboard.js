/**
 * MicroCorp AI - Real-time Dashboard Controller
 */

let isPaused = false;
let latestTelemetry = null;
let currentInspectSubagentId = null;

async function fetchTelemetry() {
    try {
        const res = await fetch("/api/telemetry");
        if (!res.ok) return;
        const data = await res.json();
        latestTelemetry = data;
        renderDashboard(data);
        
        // If modal is open, refresh inspector live
        if (currentInspectSubagentId) {
            refreshInspectorData(currentInspectSubagentId);
        }
    } catch (e) {
        console.error("Telemetry fetch error:", e);
    }
}

function renderDashboard(data) {
    const hw = data.hardware || {};
    const q = data.queue_stats || {};
    const treasury = data.treasury || {};

    // 1. Hardware meters
    const cpu = hw.cpu_percent || 0;
    const ram = hw.memory_percent || 0;
    const battery = hw.battery_percent || 100;
    const isCharging = hw.is_charging;

    document.getElementById("cpuVal").textContent = `${cpu}%`;
    const cpuBar = document.getElementById("cpuBar");
    cpuBar.style.width = `${Math.min(cpu, 100)}%`;
    cpuBar.style.background = cpu > 80 ? "var(--danger)" : (cpu > 60 ? "var(--warning)" : "var(--primary)");

    document.getElementById("ramVal").textContent = `${ram}%`;
    document.getElementById("ramBar").style.width = `${Math.min(ram, 100)}%`;

    document.getElementById("batteryVal").textContent = `${battery}%`;
    document.getElementById("batteryState").innerHTML = isCharging 
        ? `<i class="fa-solid fa-bolt" style="color: #10b981;"></i> AC Power Connected` 
        : `<i class="fa-solid fa-battery-half"></i> On Battery Power`;

    // 2. Subagent & Queue numbers
    const activeSubs = data.active_subagents || [];
    document.getElementById("subagentVal").textContent = activeSubs.length;
    document.getElementById("pendingCount").textContent = q.total_pending || 0;
    document.getElementById("completedCount").textContent = q.total_completed || 0;

    // 3. Treasury
    document.getElementById("netProfitVal").textContent = `$${treasury.estimated_net_profit || '0.00'}`;
    document.getElementById("treasuryStats").textContent = 
        `Costs: $${treasury.total_api_costs || '0.000'} • Gross: $${treasury.estimated_gross_revenue || '0.00'}`;

    // 4. Departments
    const depts = data.departments || [];
    document.getElementById("deptCountBadge").textContent = `${depts.length} Departments`;
    const deptsContainer = document.getElementById("departmentsContainer");
    deptsContainer.innerHTML = depts.map(d => {
        const isDyn = d.is_dynamic === 1;
        const statusColor = d.status === "busy" ? "#f59e0b" : (d.status === "active" ? "#10b981" : "#64748b");
        return `
            <div class="glass-card dept-card ${isDyn ? 'dynamic' : ''}" onclick="inspectDepartment('${d.dept_id}')" title="Click to inspect department activity & subagents">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <h4 style="font-size: 15px; font-weight: 600;"><i class="${d.icon || 'fa-solid fa-building'}"></i> ${d.name}</h4>
                        <small style="color: var(--text-muted);">${d.head_title}</small>
                    </div>
                    ${isDyn ? '<span class="badge-tag badge-dynamic"><i class="fa-solid fa-bolt"></i> DYNAMIC</span>' : ''}
                </div>
                <p style="font-size: 12px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">${d.description || ''}</p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.05); font-size: 12px;">
                    <span style="color: ${statusColor}; font-weight: 600;">
                        <span class="live-pulse" style="width: 7px; height: 7px; background: ${statusColor}; box-shadow: 0 0 5px ${statusColor};"></span> 
                        ${d.status.toUpperCase()}
                    </span>
                    <span class="badge-tag" style="background: rgba(255,255,255,0.06); cursor: pointer;"><i class="fa-solid fa-robot"></i> ${d.current_subagents_count || 1} subagent(s) <i class="fa-solid fa-chevron-right" style="font-size: 9px; margin-left: 2px;"></i></span>
                </div>
            </div>
        `;
    }).join("");

    // 5. Active Subagents list
    const subagentsList = document.getElementById("subagentsList");
    if (activeSubs.length === 0) {
        subagentsList.innerHTML = `<div style="color: var(--text-muted); font-size: 12px; padding: 10px;">No subagents currently spawned.</div>`;
    } else {
        subagentsList.innerHTML = activeSubs.map(s => {
            const isWorking = s.status === "working";
            const badgeBg = isWorking ? "rgba(245, 158, 11, 0.2)" : "rgba(16, 185, 129, 0.2)";
            const badgeColor = isWorking ? "#fbbf24" : "#34d399";
            const progress = s.progress_percent || (isWorking ? 45 : (s.tasks_completed > 0 ? 100 : 0));
            const taskTitle = s.current_task_title || (isWorking ? "Active Autonomous Sprint" : "Standing by for task queue");
            const phase = s.current_phase || (isWorking ? "In Execution" : "Idle / Standby");

            return `
                <div class="interactive-subagent-row" onclick="openSubagentInspector('${s.subagent_id}')" title="Click to inspect live work, progress & ETA" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); padding: 10px 12px; border-radius: 8px; display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="live-pulse" style="width: 8px; height: 8px; background: ${badgeColor}; box-shadow: 0 0 6px ${badgeColor};"></span>
                            <span style="font-size: 13px; font-weight: 600; color: #f8fafc;">${s.name}</span>
                        </div>
                        <span style="background: ${badgeBg}; color: ${badgeColor}; font-size: 10px; padding: 2px 7px; border-radius: 999px; font-weight: 600;">
                            ${s.status.toUpperCase()}
                        </span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); display: flex; justify-content: space-between;">
                        <span><i class="${s.dept_icon || 'fa-solid fa-robot'}"></i> ${s.role}</span>
                        <span>Done: <strong style="color: #c084fc;">${s.tasks_completed}</strong></span>
                    </div>
                    <div style="font-size: 11px; color: #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        <i class="fa-solid fa-briefcase" style="color: #60a5fa; font-size: 10px;"></i> ${taskTitle}
                    </div>
                    <!-- Mini progress bar -->
                    <div style="display: flex; align-items: center; gap: 8px; margin-top: 2px;">
                        <div style="flex: 1; height: 5px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden;">
                            <div style="width: ${progress}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #10b981); border-radius: 3px; transition: width 0.3s ease;"></div>
                        </div>
                        <span style="font-size: 10px; font-weight: 600; color: #94a3b8; min-width: 28px; text-align: right;">${progress}%</span>
                    </div>
                </div>
            `;
        }).join("");
    }

    // 5b. Autonomous Plans Grid
    const plans = data.recent_plans || [];
    const plansGrid = document.getElementById("plansGrid");
    if (plansGrid) {
        if (plans.length === 0) {
            plansGrid.innerHTML = `<div style="grid-column: 1 / -1; color: var(--text-muted); font-size: 13px; padding: 16px; background: rgba(255,255,255,0.02); border-radius: 8px;">No autonomous work plans generated yet. Click "Self-Run Income Cycle (Full Auto)" to scan feeds and build a turnkey execution plan.</div>`;
        } else {
            plansGrid.innerHTML = plans.map(p => {
                const score = Math.round((p.feasibility_score || 1.0) * 100);
                const isCompleted = p.status === "completed";
                const statusBadge = isCompleted 
                    ? `<span style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 600;"><i class="fa-solid fa-check-double"></i> 100% COMPLETE</span>`
                    : `<span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 600;"><i class="fa-solid fa-spinner fa-spin"></i> EXECUTING</span>`;
                
                const planDetails = p.plan || {};
                const milestonesCount = (planDetails.milestones || []).length || 3;
                const checklistCount = (planDetails.verification_checklist || []).length || 3;

                return `
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); padding: 16px; border-radius: 10px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
                            <strong style="color: #f8fafc; font-size: 14px;">${p.title}</strong>
                            ${statusBadge}
                        </div>
                        <div style="display: flex; gap: 8px; align-items: center; margin-top: 2px;">
                            <span class="badge-tag" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 11px;">
                                <i class="fa-solid fa-shield-halved"></i> ${score}% Feasible
                            </span>
                            <span class="badge-tag" style="font-size: 11px;">${p.domain.replace('_', ' ')}</span>
                        </div>
                        <p style="font-size: 12px; color: var(--text-muted); line-height: 1.4; margin-top: 4px;">
                            ${planDetails.objective ? planDetails.objective.substring(0, 110) + '...' : (p.feasibility_reasons || '').substring(0, 110) + '...'}
                        </p>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.04); font-size: 12px;">
                            <span style="color: var(--text-muted);"><i class="fa-solid fa-list-check"></i> ${milestonesCount} Milestones • ${checklistCount} Checks</span>
                            <a href="/view_plan/${p.plan_id}" target="_blank" class="link-btn"><i class="fa-solid fa-file-lines"></i> View Plan</a>
                        </div>
                    </div>
                `;
            }).join("");
        }
    }

    // 6. Deliverables / Treasury logs
    const deliverables = treasury.recent_logs || [];
    const tableBody = document.getElementById("deliverablesTableBody");
    if (deliverables.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">No deliverables generated yet. Click any button above to launch an autonomous sprint!</td></tr>`;
    } else {
        tableBody.innerHTML = deliverables.map(item => {
            let viewLink = "#";
            if (item.deliverable_path) {
                const parts = item.deliverable_path.split("deliverables/");
                if (parts.length > 1) {
                    viewLink = `/view_deliverable/${parts[1]}`;
                }
            }
            return `
                <tr>
                    <td>
                        <strong style="color: #f8fafc;">${item.title}</strong>
                        <div style="font-size: 11px; color: var(--text-muted);">${item.created_at || ''}</div>
                    </td>
                    <td><span class="badge-tag">${item.category.replace('_', ' ')}</span></td>
                    <td style="color: #34d399; font-weight: 600;">$${Number(item.amount_est_usd).toFixed(2)}</td>
                    <td style="color: #94a3b8; font-size: 12px;">$${Number(item.token_cost_usd).toFixed(4)}</td>
                    <td><span class="badge-tag" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">${item.status}</span></td>
                    <td>
                        <a href="${viewLink}" target="_blank" class="link-btn"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open Asset</a>
                    </td>
                </tr>
            `;
        }).join("");
    }
}

// Subagent & Department Inspector Handlers
async function openSubagentInspector(subagentId) {
    currentInspectSubagentId = subagentId;
    const modal = document.getElementById("inspectorModal");
    modal.classList.add("active");
    await refreshInspectorData(subagentId);
}

async function inspectDepartment(deptId) {
    if (latestTelemetry && latestTelemetry.active_subagents) {
        const found = latestTelemetry.active_subagents.find(s => s.dept_id === deptId);
        if (found) {
            return openSubagentInspector(found.subagent_id);
        }
    }
    // If no active subagent, fetch from API or display department card summary
    try {
        const res = await fetch("/api/telemetry");
        const data = await res.json();
        const dept = (data.departments || []).find(d => d.dept_id === deptId);
        if (dept) {
            displayDepartmentModal(dept);
        }
    } catch (e) {
        console.error("Inspect department error:", e);
    }
}

function displayDepartmentModal(dept) {
    const modal = document.getElementById("inspectorModal");
    modal.classList.add("active");
    currentInspectSubagentId = null;

    document.getElementById("modalAvatar").innerHTML = `<i class="${dept.icon || 'fa-solid fa-building'}"></i>`;
    document.getElementById("modalAgentName").textContent = dept.name;
    document.getElementById("modalAgentRole").textContent = `${dept.head_title} • ${dept.is_dynamic ? 'Dynamic Burst Unit' : 'Core Business Unit'}`;
    
    const isBusy = dept.status === "busy";
    const statusBadge = document.getElementById("modalStatusBadge");
    statusBadge.textContent = dept.status.toUpperCase();
    statusBadge.style.background = isBusy ? "rgba(245, 158, 11, 0.2)" : "rgba(16, 185, 129, 0.2)";
    statusBadge.style.color = isBusy ? "#fbbf24" : "#34d399";

    document.getElementById("modalTimeMetric").innerHTML = `<i class="fa-solid fa-microchip"></i> Local Department Engine`;
    document.getElementById("modalTaskTitle").textContent = dept.description || "Standing by for autonomous dispatch.";
    document.getElementById("modalDomainBadge").textContent = dept.dept_id;
    document.getElementById("modalDeptBadge").textContent = `${dept.current_subagents_count || 1} Worker(s) Assigned`;

    const progress = isBusy ? 60 : 100;
    document.getElementById("modalProgressPercent").textContent = `${progress}%`;
    document.getElementById("modalProgressBar").style.width = `${progress}%`;
    document.getElementById("modalPhaseText").textContent = isBusy ? "Executing assigned task queue..." : "Active and healthy • Listening for incoming tasks";

    document.getElementById("modalEtaVal").textContent = isBusy ? "~20s remaining" : "0s (Ready)";
    document.getElementById("modalElapsedVal").textContent = `Subagent allocation: ${dept.current_subagents_count || 1}`;
    document.getElementById("modalCompletedTasks").textContent = "Autonomous Unit";

    updatePipelineSteps(progress);
    document.getElementById("modalDeliverableLink").style.display = "none";
}

async function refreshInspectorData(subagentId) {
    try {
        const res = await fetch(`/api/subagent/${subagentId}`);
        if (!res.ok) return;
        const sub = await res.json();

        document.getElementById("modalAvatar").innerHTML = `<i class="${sub.dept_icon || 'fa-solid fa-robot'}"></i>`;
        document.getElementById("modalAgentName").textContent = sub.name;
        document.getElementById("modalAgentRole").textContent = `${sub.role} • ${sub.department_name || sub.dept_id}`;

        const isWorking = sub.status === "working";
        const statusBadge = document.getElementById("modalStatusBadge");
        statusBadge.textContent = sub.status.toUpperCase();
        statusBadge.style.background = isWorking ? "rgba(245, 158, 11, 0.2)" : "rgba(16, 185, 129, 0.2)";
        statusBadge.style.color = isWorking ? "#fbbf24" : "#34d399";

        // Timing calculations
        let startedText = "Standby";
        let elapsedSec = 0;
        if (sub.started_at) {
            const startedDate = new Date(sub.started_at + "Z");
            const now = new Date();
            elapsedSec = Math.max(0, Math.floor((now - startedDate) / 1000));
            startedText = `${elapsedSec}s ago`;
        }
        document.getElementById("modalTimeMetric").innerHTML = `<i class="fa-solid fa-clock"></i> Started: ${startedText}`;

        // Task & Domain
        const taskTitle = sub.current_task_title || (isWorking ? "Active Autonomous Sprint" : "Standing by for queue");
        document.getElementById("modalTaskTitle").textContent = taskTitle;
        document.getElementById("modalDomainBadge").textContent = sub.task_domain || sub.dept_id;
        document.getElementById("modalDeptBadge").textContent = sub.department_name || "MicroCorp Unit";

        // Progress & Phase
        let progress = sub.progress_percent || (isWorking ? 45 : (sub.tasks_completed > 0 ? 100 : 0));
        document.getElementById("modalProgressPercent").textContent = `${progress}%`;
        document.getElementById("modalProgressBar").style.width = `${progress}%`;
        document.getElementById("modalPhaseText").textContent = `Phase: ${sub.current_phase || (isWorking ? "Processing task..." : "Idle / Standby")}`;

        // ETA calculation
        const estTotal = sub.estimated_duration_seconds || 45;
        const remainingSec = Math.max(0, estTotal - elapsedSec);
        if (isWorking) {
            document.getElementById("modalEtaVal").textContent = `~${remainingSec > 0 ? remainingSec : 5}s remaining`;
            document.getElementById("modalElapsedVal").textContent = `Elapsed: ${elapsedSec}s • Target: ${estTotal}s`;
        } else {
            document.getElementById("modalEtaVal").textContent = "Completed / Standby";
            document.getElementById("modalElapsedVal").textContent = `Ready for next task`;
        }

        document.getElementById("modalCompletedTasks").textContent = `${sub.tasks_completed} Finished`;

        // Pipeline steps visual
        updatePipelineSteps(progress);

        // Deliverable Link if available
        const delivLink = document.getElementById("modalDeliverableLink");
        if (sub.result_deliverable_path) {
            const parts = sub.result_deliverable_path.split("deliverables/");
            if (parts.length > 1) {
                delivLink.href = `/view_deliverable/${parts[1]}`;
                delivLink.style.display = "inline-flex";
            } else {
                delivLink.style.display = "none";
            }
        } else {
            delivLink.style.display = "none";
        }
    } catch (e) {
        console.error("Error refreshing inspector:", e);
    }
}

function updatePipelineSteps(progress) {
    const setStep = (id, iconClass, color, active) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.style.color = color;
        el.style.opacity = active ? "1" : "0.5";
        const icon = el.querySelector("i");
        if (icon) icon.className = iconClass;
    };

    if (progress >= 100) {
        setStep("modalStep1", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep2", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep3", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep4", "fa-solid fa-circle-check", "#34d399", true);
    } else if (progress >= 80) {
        setStep("modalStep1", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep2", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep3", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep4", "fa-solid fa-spinner fa-spin", "#60a5fa", true);
    } else if (progress >= 50) {
        setStep("modalStep1", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep2", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep3", "fa-spinner fa-spin", "#60a5fa", true);
        setStep("modalStep4", "fa-regular fa-circle", "#64748b", false);
    } else if (progress >= 20) {
        setStep("modalStep1", "fa-solid fa-circle-check", "#34d399", true);
        setStep("modalStep2", "fa-solid fa-spinner fa-spin", "#60a5fa", true);
        setStep("modalStep3", "fa-regular fa-circle", "#64748b", false);
        setStep("modalStep4", "fa-regular fa-circle", "#64748b", false);
    } else {
        setStep("modalStep1", "fa-regular fa-circle", "#64748b", true);
        setStep("modalStep2", "fa-regular fa-circle", "#64748b", false);
        setStep("modalStep3", "fa-regular fa-circle", "#64748b", false);
        setStep("modalStep4", "fa-regular fa-circle", "#64748b", false);
    }
}

function closeInspector(event) {
    if (event && event.target && event.target.id !== "inspectorModal" && !event.target.classList.contains("modal-close")) {
        return;
    }
    const modal = document.getElementById("inspectorModal");
    modal.classList.remove("active");
    currentInspectSubagentId = null;
}

async function triggerSprint(domain, title) {
    try {
        const res = await fetch("/api/sprint", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain: domain, title: title })
        });
        const d = await res.json();
        if (!res.ok) {
            alert(`⚖️ Task Blocked by Legal Compliance Guardian:\n\n${d.detail || "Violates legal and ethical operations policy. MicroCorp AI performs strictly lawful work."}`);
            return;
        }
        alert(`🚀 Sprint dispatched: ${title}`);
        fetchTelemetry();
    } catch (e) {
        alert(`Error triggering sprint: ${e}`);
    }
}

async function submitCustomTask() {
    const title = document.getElementById("customTaskTitle").value.trim();
    const domain = document.getElementById("customTaskDomain").value;
    if (!title) {
        alert("Please enter a task title.");
        return;
    }
    await triggerSprint(domain, title);
    document.getElementById("customTaskTitle").value = "";
}

async function submitCustomerOrder() {
    const clientName = document.getElementById("customerName").value.trim() || "Client";
    const title = document.getElementById("customerOrderTitle").value.trim();
    const requirements = document.getElementById("customerRequirements").value.trim();
    const banner = document.getElementById("customerNoticeBanner");

    if (!title || !requirements) {
        alert("Please provide both a project title and requirements.");
        return;
    }

    try {
        const res = await fetch("/api/customer/order", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_name: clientName,
                project_title: title,
                project_requirements: requirements
            })
        });

        const data = await res.json();
        banner.style.display = "block";

        if (data.verdict === "REJECTED") {
            banner.style.background = "rgba(239, 68, 68, 0.15)";
            banner.style.border = "1px solid rgba(239, 68, 68, 0.4)";
            let docLink = "#";
            if (data.rejection_document_path) {
                const parts = data.rejection_document_path.split("deliverables/");
                if (parts.length > 1) {
                    docLink = `/view_deliverable/${parts[1]}`;
                }
            }
            banner.innerHTML = `
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <i class="fa-solid fa-ban" style="color: #f87171; font-size: 24px; margin-top: 2px;"></i>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: #f87171; font-size: 14px;">🛑 CUSTOMER WORK REJECTED — UNLAWFUL REQUEST</strong>
                            <a href="${docLink}" target="_blank" class="link-btn" style="color: #fca5a5; font-size: 12px;"><i class="fa-solid fa-file-pdf"></i> View Official Refusal Notice</a>
                        </div>
                        <div style="color: #fca5a5; font-size: 12px; margin-top: 4px; line-height: 1.5;">${data.reason}</div>
                        <div style="margin-top: 6px; font-size: 11px; color: var(--text-muted);">
                            Governing Legal Statute: <span style="color: #f8fafc; font-weight: 500;">${data.legal_statute}</span> • Classification: <span style="color: #c084fc;">${data.risk_category}</span>
                        </div>
                        <div style="margin-top: 8px; font-size: 12px; color: #e2e8f0; background: rgba(0,0,0,0.3); padding: 8px 10px; border-radius: 6px; border-left: 3px solid #ef4444;">
                            <strong>Customer Advisory:</strong> ${data.advisory_summary}
                        </div>
                    </div>
                </div>
            `;
        } else {
            banner.style.background = "rgba(16, 185, 129, 0.15)";
            banner.style.border = "1px solid rgba(16, 185, 129, 0.4)";
            banner.innerHTML = `
                <div style="display: flex; gap: 10px; align-items: center;">
                    <i class="fa-solid fa-circle-check" style="color: #34d399; font-size: 20px;"></i>
                    <div>
                        <strong style="color: #34d399; font-size: 14px;">✅ CUSTOMER ORDER ACCEPTED — 100% LAWFUL & ETHICAL</strong>
                        <div style="color: #cbd5e1; font-size: 12px; margin-top: 2px;">${data.message}</div>
                    </div>
                </div>
            `;
            document.getElementById("customerOrderTitle").value = "";
            document.getElementById("customerRequirements").value = "";
        }
        fetchTelemetry();
    } catch (e) {
        alert("Error submitting customer order: " + e);
    }
}

async function triggerAutonomousCycle() {
    try {
        const res = await fetch("/api/autonomous_cycle", { method: "POST" });
        alert("✨ Autonomous Income Cycle Initiated! The CEO is harvesting signals, identifying high-yield assets, and deploying worker subagents.");
        fetchTelemetry();
    } catch (e) {
        alert("Error initiating autonomous cycle: " + e);
    }
}

async function testDynamicBurst() {
    const tasks = [
        { domain: "digital_products", title: "Docker & Kubernetes Production Cheatsheet" },
        { domain: "digital_products", title: "FastAPI Clean Architecture Template Pack" },
        { domain: "digital_products", title: "PostgreSQL Indexing & Performance Guide" },
        { domain: "seo_growth", title: "Top 10 Autonomous Coding Tools Comparison Review" }
    ];
    for (const t of tasks) {
        await fetch("/api/sprint", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(t)
        });
    }
    alert("⚡ High-load task surge dispatched! Watch the auto-scaler spawn subagents and departments.");
    fetchTelemetry();
}

async function togglePause() {
    try {
        const res = await fetch("/api/toggle_pause", { method: "POST" });
        const d = await res.json();
        isPaused = d.is_paused;
        document.getElementById("pauseText").textContent = isPaused ? "Resume Loop" : "Pause Loop";
        fetchTelemetry();
    } catch (e) {
        console.error("Pause toggle failed:", e);
    }
}

// Initial fetch & loop every 2.5 seconds
fetchTelemetry();
setInterval(fetchTelemetry, 2500);
