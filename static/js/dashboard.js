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

    // 3b. GitHub Sync State
    const git = data.git_status || {};
    const gitBadge = document.getElementById("githubStatusBadge");
    if (gitBadge && git.is_git_repo) {
        const isClean = git.is_clean;
        const branch = git.branch || "main";
        const commitHash = (git.last_commit && git.last_commit.hash) || "";
        const changedCount = git.changed_files_count || 0;
        document.getElementById("gitBranchText").textContent = `GitHub: ${branch}@${commitHash}`;
        gitBadge.style.borderColor = isClean ? "rgba(16, 185, 129, 0.4)" : "rgba(245, 158, 11, 0.4)";
        gitBadge.title = isClean ? "100% Synced with GitHub remote" : `${changedCount} local changes pending sync`;
    }

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

// ==========================================
// Freelancing Radar & Work Distributor
// ==========================================
let cachedFreelanceGigs = [];

async function fetchFreelanceRadar() {
    const container = document.getElementById("freelanceJobsContainer");
    const refreshBtn = document.getElementById("refreshFreelanceBtn");
    if (refreshBtn) refreshBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Scanning...`;

    try {
        const res = await fetch("/api/freelance/jobs");
        const gigs = await res.json();
        cachedFreelanceGigs = gigs;

        if (!gigs || gigs.length === 0) {
            container.innerHTML = `<div style="grid-column: 1 / -1; color: var(--text-muted); font-size: 13px; padding: 14px;">No active platform gigs found at this time.</div>`;
            return;
        }

        container.innerHTML = gigs.map(g => {
            const isLegal = g.is_legal;
            const isFeasible = g.is_turnkey_feasible;
            const platform = g.platform || "Fiverr";
            
            // Platform badge styles
            let platBg = "rgba(16, 185, 129, 0.2)";
            let platColor = "#10b981";
            if (platform === "Upwork") { platBg = "rgba(14, 165, 233, 0.2)"; platColor = "#38bdf8"; }
            else if (platform === "Freelancer") { platBg = "rgba(99, 102, 241, 0.2)"; platColor = "#818cf8"; }
            else if (platform === "RemoteOK") { platBg = "rgba(249, 115, 22, 0.2)"; platColor = "#fb923c"; }

            const legalBadge = isLegal 
                ? `<span style="font-size: 10px; background: rgba(16, 185, 129, 0.15); color: #34d399; padding: 2px 7px; border-radius: 999px; font-weight: 600;"><i class="fa-solid fa-shield-halved"></i> LAWFUL</span>`
                : `<span style="font-size: 10px; background: rgba(239, 68, 68, 0.2); color: #f87171; padding: 2px 7px; border-radius: 999px; font-weight: 600;"><i class="fa-solid fa-triangle-exclamation"></i> UNLAWFUL</span>`;

            return `
                <div class="glass-card" style="padding: 14px; display: flex; flex-direction: column; justify-content: space-between; gap: 8px; border: 1px solid rgba(255,255,255,0.08);">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-size: 11px; font-weight: 700; background: ${platBg}; color: ${platColor}; padding: 3px 8px; border-radius: 6px; text-transform: uppercase;">
                                <i class="fa-solid fa-tag"></i> ${platform}
                            </span>
                            <div style="display: flex; gap: 6px; align-items: center;">
                                ${legalBadge}
                                <span style="font-size: 12px; font-weight: 700; color: #34d399;">$${g.budget || 200}</span>
                            </div>
                        </div>
                        <h4 style="font-size: 14px; font-weight: 600; color: #f1f5f9; line-height: 1.4;">${g.title}</h4>
                        <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Client: <span style="color: #cbd5e1;">${g.client_name || 'Verified Client'}</span></div>
                        <p style="font-size: 12px; color: #94a3b8; margin-top: 6px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                            ${g.description || ''}
                        </p>
                    </div>

                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 11px; color: ${isFeasible ? '#60a5fa' : '#94a3b8'};">
                            <i class="fa-solid fa-circle-check"></i> ${isFeasible ? '100% Turnkey Feasible' : 'Requires Review'}
                        </span>
                        <button class="btn-action purple" onclick="distributeGig('${g.job_id}')" style="padding: 5px 12px; font-size: 11px;">
                            <i class="fa-solid fa-sitemap"></i> Distribute Work
                        </button>
                    </div>
                </div>
            `;
        }).join("");
    } catch (e) {
        container.innerHTML = `<div style="grid-column: 1 / -1; color: var(--danger); font-size: 12px;">Failed to scan platforms: ${e}</div>`;
    } finally {
        if (refreshBtn) refreshBtn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Scan Platforms`;
    }
}

async function distributeGig(jobId) {
    const banner = document.getElementById("freelanceDistributionBanner");
    banner.style.display = "block";
    banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 20px; color: #a855f7;"></i>
            <div>
                <h4 style="font-size: 14px; color: #f1f5f9;">Autonomous Work Decomposition & Multi-Department Execution in Progress...</h4>
                <p style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
                    Decomposing project into 100% turnkey milestones across Digital Products Lab, Technical Documentation Bureau, and Proposal Desk...
                </p>
            </div>
        </div>
    `;

    try {
        const res = await fetch("/api/freelance/distribute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ job_id: jobId })
        });
        const d = await res.json();

        if (d.status === "COMPLETED") {
            const milestonesHtml = (d.milestone_results || []).map(m => `
                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px; font-size: 12px;">
                    <div style="font-weight: 600; color: #60a5fa;"><i class="fa-solid fa-check"></i> Milestone ${m.milestone}: ${m.department}</div>
                    <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">${m.summary || 'Completed deliverable produced'}</div>
                </div>
            `).join("");

            banner.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <span class="badge-tag" style="background: rgba(16, 185, 129, 0.2); color: #34d399; margin-bottom: 6px;">
                            <i class="fa-solid fa-circle-check"></i> 100% Turnkey Execution Complete
                        </span>
                        <h4 style="font-size: 15px; color: #f1f5f9; margin-top: 4px;">${d.title} (${d.platform})</h4>
                        <p style="font-size: 12px; color: #a7f3d0; margin-top: 2px;">
                            Earned <strong style="font-size: 14px;">$${d.net_passive_income}</strong> Net Passive Income credited to Treasury!
                        </p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <a href="/view_deliverable/${encodeURIComponent(d.deliverable_html.split('deliverables/')[1] || '')}" target="_blank" class="btn-action" style="text-decoration: none; padding: 6px 12px; font-size: 12px;">
                            <i class="fa-solid fa-eye"></i> Preview HTML
                        </a>
                        <a href="/view_deliverable/${encodeURIComponent(d.deliverable_zip.split('deliverables/')[1] || '')}" class="btn-action purple" style="text-decoration: none; padding: 6px 12px; font-size: 12px;">
                            <i class="fa-solid fa-download"></i> Download Client ZIP
                        </a>
                    </div>
                </div>

                <div style="margin-top: 12px; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 8px;">
                    ${milestonesHtml}
                </div>
            `;
            fetchTelemetry();
        } else if (d.status === "REJECTED_UNLAWFUL") {
            banner.innerHTML = `
                <div style="color: #f87171;">
                    <i class="fa-solid fa-triangle-exclamation"></i> <strong>REJECTED BY LEGAL GUARDIAN:</strong> ${d.summary}
                </div>
            `;
        }
    } catch (e) {
        banner.innerHTML = `<div style="color: var(--danger); font-size: 12px;">Execution failed: ${e}</div>`;
    }
}

async function autoDistributeFreelanceGig() {
    const btn = document.getElementById("autoDistributeBtn");
    if (btn) btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Auto-Executing...`;
    await distributeGig(null);
    if (btn) btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Auto-Distribute Top Gig`;
}

// ==========================================
// GitHub Auto-Sync Engine Integration
// ==========================================
async function syncWithGithub() {
    const btn = document.getElementById("gitSyncBtn");
    const textSpan = document.getElementById("gitSyncText");
    if (textSpan) textSpan.textContent = "Syncing to GitHub...";
    if (btn) btn.disabled = true;

    try {
        const res = await fetch("/api/git/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();
        if (data.success) {
            alert(`✅ ${data.message}\nCommit: ${data.commit ? data.commit.hash : 'HEAD'}`);
        } else {
            alert(`⚠️ Git Sync notice: ${data.error || 'Check terminal or network'}`);
        }
        fetchTelemetry();
    } catch (e) {
        alert("Error syncing to GitHub: " + e);
    } finally {
        if (textSpan) textSpan.textContent = "Sync to GitHub";
        if (btn) btn.disabled = false;
    }
}

// Initial fetch & loop every 2.5 seconds
fetchTelemetry();
fetchFreelanceRadar();
setInterval(fetchTelemetry, 2500);

