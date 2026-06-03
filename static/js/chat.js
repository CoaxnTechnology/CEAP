const state = {
    files: [],
    selectedFileIds: new Set(),

    sessions: [],
    currentSessionId: sessionStorage.getItem("current_chat_session") || "",
    history: [],
    sending: false,
    lastQuery: "",
    lastContextIds: [],
    oneDrive: {
        enabled: false,
        connected: false,
        user: "",
        email: "",
        loading: false,
        currentFolderId: "root",
        folderStack: [{ id: "root", name: "Root", path: "/" }],
        items: [],
        selectedItems: new Map(),
    },
};

const FEATURES = {
    hr: [
        { name: "Apply Leave", desc: "Submit a leave application", icon: "fa-calendar-days", prompt: "Apply for leave" },
        { name: "Leave Balance", desc: "Check remaining leave balance", icon: "fa-coins", prompt: "What is my leave balance?" },
        { name: "My Leaves", desc: "List all my leave requests", icon: "fa-list", prompt: "Show my leave requests" },
        { name: "Mark Attendance", desc: "Check-in or check-out", icon: "fa-clock", prompt: "Mark my attendance for today" },
        { name: "Attendance Records", desc: "View attendance for a date range", icon: "fa-clipboard-list", prompt: "Show my attendance records for this month" },
        { name: "Get Payslip", desc: "Retrieve payslip information", icon: "fa-file-invoice-dollar", prompt: "Get my payslip" },
        { name: "HR Policy Search", desc: "Search HR policy documents", icon: "fa-book", prompt: "Search HR policy for leave policy" },
        { name: "My Profile", desc: "View employee profile", icon: "fa-id-card", prompt: "Show my employee information" },
        { name: "Pending Approvals", desc: "View pending approval requests", icon: "fa-hourglass-half", prompt: "Show my pending approvals" },
        { name: "Approve/Reject", desc: "Approve or reject a request", icon: "fa-check-double", prompt: "Approve pending request" },
        { name: "Onboard Employee", desc: "Onboard a new employee", icon: "fa-user-plus", prompt: "Onboard a new employee named" },
        { name: "HR Report", desc: "Generate HR summary report", icon: "fa-chart-bar", prompt: "Generate an HR report" },
        { name: "Employee Documents", desc: "List employee-related docs", icon: "fa-file-contract", prompt: "List employee documents" },
    ],
    accounting: [
        { name: "Create Invoice", desc: "Create a new invoice", icon: "fa-file-invoice", prompt: "Create an invoice" },
        { name: "Extract Invoice Data", desc: "Extract data from invoice PDF", icon: "fa-file-export", prompt: "Extract invoice data from uploaded file" },
        { name: "List Invoices", desc: "List invoices by status", icon: "fa-list", prompt: "Show my invoices" },
        { name: "Mark Paid", desc: "Mark an invoice as paid", icon: "fa-check", prompt: "Mark invoice as paid" },
        { name: "Submit Expense", desc: "Submit an expense claim", icon: "fa-receipt", prompt: "Submit an expense claim" },
        { name: "List Expenses", desc: "View expense claims", icon: "fa-list", prompt: "List my expenses" },
        { name: "Financial Summary", desc: "Monthly financial overview", icon: "fa-chart-pie", prompt: "Show financial summary for this month" },
        { name: "Payment Reminder", desc: "Send reminder for overdue invoice", icon: "fa-bell", prompt: "Send payment reminder for overdue invoices" },
        { name: "Track Payments", desc: "Track payment status", icon: "fa-truck", prompt: "Track payment status" },
        { name: "Reconcile Statement", desc: "Reconcile vendor statement", icon: "fa-scale-balanced", prompt: "Reconcile vendor statement" },
        { name: "Accounting Entry", desc: "Create double-entry entry", icon: "fa-book", prompt: "Create an accounting entry" },
        { name: "Audit Storage", desc: "Store document for audit", icon: "fa-shield", prompt: "Store document in audit storage" },
    ],
    admin: [
        { name: "Schedule Meeting", desc: "Schedule a new meeting", icon: "fa-calendar-plus", prompt: "Schedule a meeting" },
        { name: "List Meetings", desc: "View upcoming meetings", icon: "fa-calendar", prompt: "Show my upcoming meetings" },
        { name: "Register Visitor", desc: "Pre-approve a visitor", icon: "fa-user", prompt: "Register a visitor" },
        { name: "List Assets", desc: "View assets by status", icon: "fa-boxes", prompt: "List assets" },
        { name: "Add Asset", desc: "Add new asset to inventory", icon: "fa-plus-circle", prompt: "Add a new asset" },
        { name: "Request Supply", desc: "Request office supplies", icon: "fa-cart-plus", prompt: "Request office supplies" },
        { name: "Check Inventory", desc: "Check supply inventory", icon: "fa-clipboard-check", prompt: "Check office supply inventory" },
        { name: "Create Ticket", desc: "Create support ticket", icon: "fa-ticket", prompt: "Create a support ticket" },
        { name: "List Tickets", desc: "View my tickets", icon: "fa-list", prompt: "Show my tickets" },
        { name: "Post Announcement", desc: "Post company announcement", icon: "fa-bullhorn", prompt: "Post an announcement" },
        { name: "View Announcements", desc: "Recent announcements", icon: "fa-newspaper", prompt: "Show recent announcements" },
        { name: "File Document", desc: "File a document for retrieval", icon: "fa-folder-plus", prompt: "File a document" },
        { name: "Admin Report", desc: "Generate admin summary report", icon: "fa-chart-line", prompt: "Generate an admin report" },
    ],
};

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

async function apiFetch(url, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = { ...(options.headers || {}) };
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
        headers["X-CSRFToken"] = csrfToken;
    }
    return fetch(url, { ...options, headers });
}

const dom = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
    cacheDom();
    bindEvents();
    restoreSelectedFiles();

    const skel = document.getElementById("skeletonLoader");
    if (skel) {
        skel.classList.add("show");
    }

    try {
        await loadChatSessions();
        await loadPersistedChat(state.currentSessionId);
        updateSessionHeader();
        renderAllFeatures();
        if (skel) {
            skel.classList.remove("show");
        }
        Promise.resolve().then(() => {
            loadFiles();
        });
    } catch (error) {
        console.error("init failed:", error);
        showToast("Failed to load some data. Try refreshing the page.", "error");
        if (skel) {
            skel.classList.remove("show");
        }
    }
}

function cacheDom() {
    dom.appShell = document.querySelector(".app-shell");
    dom.sessionsPanel = document.getElementById("sessionsPanel");
    dom.filesPanel = document.getElementById("filesPanel");
    dom.mobileBackdrop = document.getElementById("mobileBackdrop");

    dom.sessionsPanelToggleBtn = document.getElementById("sessionsPanelToggleBtn");
    dom.collapseSidebarBtn = document.getElementById("collapseSidebarBtn");
    dom.collapseSidebarContentBtn = document.getElementById("collapseSidebarContentBtn");
    dom.newChatRailBtn = document.getElementById("newChatRailBtn");
    dom.profileRailBtn = document.getElementById("profileRailBtn");
    dom.mobileMenuBtn = document.getElementById("mobileMenuBtn");
    dom.closeMobileSidebarBtn = document.getElementById("closeMobileSidebarBtn");
    dom.newChatBtn = document.getElementById("newChatBtn");
    dom.clearChatBtn = document.getElementById("clearChatBtn");
    dom.currentChatList = document.getElementById("currentChatList");
    dom.pastChatList = document.getElementById("pastChatList");
    dom.sessionTitle = document.getElementById("sessionTitle");
    dom.sessionUpdatedAt = document.getElementById("sessionUpdatedAt");

    dom.messages = document.getElementById("messages");
    dom.welcomePanel = document.getElementById("welcomePanel");
    dom.messageInput = document.getElementById("messageInput");
    dom.sendBtn = document.getElementById("sendBtn");
    dom.chatUploadBtn = document.getElementById("chatUploadBtn");
    dom.selectedFilesBar = document.getElementById("selectedFilesBar");
    dom.selectedFilesChips = document.getElementById("selectedFilesChips");
    dom.clearFilesSelectionBtn = document.getElementById("clearFilesSelectionBtn");

    dom.fileInput = document.getElementById("fileInput");
    dom.clipDropdown = document.getElementById("clipDropdown");
    dom.odPanelCloseBtn = document.getElementById("odPanelCloseBtn");

    dom.odStatusText = document.getElementById("odStatusText");
    dom.odUserText = document.getElementById("odUserText");
    dom.odConnectBtn = document.getElementById("odConnectBtn");
    dom.odDisconnectBtn = document.getElementById("odDisconnectBtn");
    dom.odBackBtn = document.getElementById("odBackBtn");
    dom.odRefreshBtn = document.getElementById("odRefreshBtn");
    dom.odPathLabel = document.getElementById("odPathLabel");
    dom.odImportBtn = document.getElementById("odImportBtn");
    dom.odSelectionCount = document.getElementById("odSelectionCount");
    dom.odFilesList = document.getElementById("odFilesList");

    dom.uploadProgressCard = document.getElementById("uploadProgressCard");
    dom.uploadProgressTitle = document.getElementById("uploadProgressTitle");
    dom.uploadProgressFill = document.getElementById("uploadProgressFill");
    dom.uploadProgressText = document.getElementById("uploadProgressText");

    dom.filesManageBtn = document.getElementById("filesManageBtn");
    dom.exportChatBtn = document.getElementById("exportChatBtn");
    dom.sessionsSearchInput = document.getElementById("sessionsSearchInput");
    dom.fmPanelCloseBtn = document.getElementById("fmPanelCloseBtn");
    dom.fmFileList = document.getElementById("fmFileList");

    dom.composerPanel = document.getElementById("composerPanel");
    dom.dropOverlay = document.getElementById("dropOverlay");

    dom.fsContent = document.getElementById("fsContent");
}

function bindEvents() {
    dom.sessionsPanelToggleBtn?.addEventListener("click", toggleSessionsPanel);
    dom.collapseSidebarBtn?.addEventListener("click", toggleSessionsPanel);
    dom.collapseSidebarContentBtn?.addEventListener("click", toggleSessionsPanel);
    dom.newChatRailBtn?.addEventListener("click", createNewChat);
    dom.mobileMenuBtn?.addEventListener("click", openMobilePanel);
    dom.closeMobileSidebarBtn?.addEventListener("click", closeMobilePanels);
    dom.mobileBackdrop?.addEventListener("click", closeMobilePanels);

    dom.newChatBtn?.addEventListener("click", createNewChat);
    dom.clearChatBtn?.addEventListener("click", clearCurrentChat);
    dom.currentChatList?.addEventListener("click", handleSessionListClick);
    dom.pastChatList?.addEventListener("click", handleSessionListClick);
    dom.sessionsSearchInput?.addEventListener("input", filterSessionLists);

    dom.messageInput?.addEventListener("input", () => {
        autoResizeInput();
        updateSendButtonState();
    });
    dom.messageInput?.addEventListener("keydown", handleComposerKeydown);
    dom.sendBtn?.addEventListener("click", sendMessage);
    dom.chatUploadBtn?.addEventListener("click", toggleClipDropdown);

    dom.clearFilesSelectionBtn?.addEventListener("click", clearFileSelection);
    dom.selectedFilesChips?.addEventListener("click", handleChipRemove);
    dom.filesSelectedClearBtn?.addEventListener("click", clearFileSelection);

    document.querySelectorAll(".prompt-chip").forEach((btn) => {
        btn.addEventListener("click", () => {
            const prompt = btn.dataset.prompt || "";
            dom.messageInput.value = prompt;
            autoResizeInput();
            updateSendButtonState();
            sendMessage();
        });
    });

    dom.fileInput?.addEventListener("change", async () => {
        const files = Array.from(dom.fileInput.files || []);
        if (!files.length) {
            return;
        }
        await handleFileUpload(files);
        dom.fileInput.value = "";
    });

    dom.clipDropdown?.addEventListener("click", handleClipDropdownClick);
    dom.odPanelCloseBtn?.addEventListener("click", closeOneDrivePanel);
    document.addEventListener("click", handleOutsideClick);

    dom.odDisconnectBtn?.addEventListener("click", disconnectOneDrive);
    dom.odBackBtn?.addEventListener("click", goBackOneDriveFolder);
    dom.odRefreshBtn?.addEventListener("click", () =>
        loadOneDriveFiles(state.oneDrive.currentFolderId)
    );
    dom.odImportBtn?.addEventListener("click", importSelectedOneDriveFiles);
    dom.odFilesList?.addEventListener("click", handleOneDriveListClick);
    dom.messages?.addEventListener("click", handleMessageActions);
    dom.exportChatBtn?.addEventListener("click", exportConversation);
    dom.filesManageBtn?.addEventListener("click", toggleFilesManagePanel);
    dom.fmPanelCloseBtn?.addEventListener("click", closeFilesManagePanel);
    dom.fmFileList?.addEventListener("click", handleFileManageActions);

    dom.fsContent?.addEventListener("click", handleFeaturesPanelClick);

    dom.sessionTitle?.addEventListener("dblclick", startRenameSession);

    dom.composerPanel?.addEventListener("dragover", handleDragOver);
    dom.composerPanel?.addEventListener("dragleave", handleDragLeave);
    dom.composerPanel?.addEventListener("drop", handleDrop);
}

function autoResizeInput() {
    if (!dom.messageInput) {
        return;
    }
    dom.messageInput.style.height = "auto";
    dom.messageInput.style.height = `${Math.min(dom.messageInput.scrollHeight, 200)}px`;
}

function updateSendButtonState() {
    const hasText = (dom.messageInput?.value || "").trim().length > 0;
    dom.sendBtn.disabled = !hasText || state.sending;
}

function handleComposerKeydown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function openMobilePanel() {
    if (window.innerWidth > 980) return;
    dom.sessionsPanel.classList.add("open");
    dom.mobileBackdrop.classList.add("show");
}

function closeMobilePanels() {
    dom.sessionsPanel.classList.remove("open");
    dom.mobileBackdrop.classList.remove("show");
}

function toggleSessionsPanel() {
    if (window.innerWidth <= 980) {
        if (dom.sessionsPanel.classList.contains("open")) {
            closeMobilePanels();
        } else {
            openMobilePanel();
        }
        return;
    }
    dom.appShell.classList.toggle("sessions-collapsed");
    updateCollapseBtnIcon();
}

function updateCollapseBtnIcon() {
    const collapsed = dom.appShell.classList.contains("sessions-collapsed");
    const icon = dom.collapseSidebarBtn?.querySelector("i");
    if (icon) {
        icon.className = collapsed ? "fas fa-chevron-right" : "fas fa-chevron-left";
    }
    const icon2 = dom.collapseSidebarContentBtn?.querySelector("i");
    if (icon2) {
        icon2.className = collapsed ? "fas fa-chevron-right" : "fas fa-chevron-left";
    }
}

function toggleOneDrivePane() {
    const panel = document.getElementById("filesPanel");
    const isOpen = panel?.classList.contains("show");
    if (isOpen) {
        panel?.classList.remove("show");
    } else {
        panel?.classList.add("show");
        loadOneDriveStatus();
    }
}

function closeOneDrivePanel() {
    const panel = document.getElementById("filesPanel");
    panel?.classList.remove("show");
}

function toggleClipDropdown(event) {
    event.stopPropagation();
    const showing = dom.clipDropdown?.classList.contains("show");
    dom.clipDropdown?.classList.toggle("show", !showing);
}

function handleClipDropdownClick(event) {
    const item = event.target.closest(".clip-dropdown-item");
    if (!item) return;
    dom.clipDropdown?.classList.remove("show");
    const action = item.dataset.action;
    if (action === "upload") {
        dom.fileInput?.click();
    } else if (action === "onedrive") {
        toggleOneDrivePane();
    }
}

function handleOutsideClick(event) {
    const btn = document.getElementById("chatUploadBtn");
    const dd = document.getElementById("clipDropdown");
    if (btn && dd && !btn.contains(event.target) && !dd.contains(event.target)) {
        dd.classList.remove("show");
    }
    const fmPanel = document.getElementById("filesManagePanel");
    const fmBtn = document.getElementById("filesManageBtn");
    if (fmPanel && fmBtn && fmPanel.classList.contains("show") && !fmPanel.contains(event.target) && !fmBtn.contains(event.target)) {
        fmPanel.classList.remove("show");
    }


}

function toggleFilesManagePanel() {
    const panel = document.getElementById("filesManagePanel");
    if (!panel) return;
    const open = panel.classList.contains("show");
    if (open) {
        panel.classList.remove("show");
    } else {
        renderFilesManageList();
        panel.classList.add("show");
    }
}

function closeFilesManagePanel() {
    document.getElementById("filesManagePanel")?.classList.remove("show");
}

function renderAllFeatures() {
    if (!dom.fsContent) return;
    const sectors = [
        { key: "hr", label: "HR", icon: "fa-users" },
        { key: "accounting", label: "Accounting", icon: "fa-calculator" },
        { key: "admin", label: "Admin", icon: "fa-building" },
    ];
    dom.fsContent.innerHTML = sectors
        .map((s, idx) => {
            const features = FEATURES[s.key] || [];
            const open = idx === 0 ? " open" : "";
            return `
                <div class="fs-group${open}" data-sector="${s.key}">
                    <div class="fs-group-header" data-sector="${s.key}">
                        <div class="fs-group-icon ${s.key}">
                            <i class="fas ${s.icon}"></i>
                        </div>
                        <span class="fs-group-title">${s.label}</span>
                        <button class="fs-group-toggle" data-sector="${s.key}">
                            <i class="fas fa-chevron-right"></i>
                        </button>
                    </div>
                    <div class="fs-group-body">
                        ${features
                            .map(
                                (f) => `
                                <div class="fs-feature" data-prompt="${escapeHtml(f.prompt)}">
                                    <div class="fs-feature-icon ${s.key}">
                                        <i class="fas ${f.icon}"></i>
                                    </div>
                                    <div class="fs-feature-info">
                                        <div class="fs-feature-name">${escapeHtml(f.name)}</div>
                                        <div class="fs-feature-desc">${escapeHtml(f.desc)}</div>
                                    </div>
                                </div>
                            `
                            )
                            .join("")}
                    </div>
                </div>
            `;
        })
        .join("");
}

function handleFeaturesPanelClick(event) {
    const toggle = event.target.closest(".fs-group-header, .fs-group-toggle");
    if (toggle) {
        const sector = toggle.dataset.sector;
        const group = dom.fsContent?.querySelector(`.fs-group[data-sector="${sector}"]`);
        if (group) {
            group.classList.toggle("open");
        }
        return;
    }
    const feature = event.target.closest(".fs-feature");
    if (!feature) return;
    const prompt = feature.dataset.prompt;
    if (!prompt) return;
    if (dom.messageInput) {
        dom.messageInput.value = prompt;
        autoResizeInput();
        updateSendButtonState();
        sendMessage();
    }
}

function renderFilesManageList() {
    if (!dom.fmFileList) return;
    if (!state.files.length) {
        dom.fmFileList.innerHTML = `<div class="empty-state">No uploaded files yet.</div>`;
        return;
    }
    dom.fmFileList.innerHTML = state.files
        .map(
            (file) => `
                <div class="fm-file-item${state.selectedFileIds.has(file.id) ? " selected" : ""}" data-file-id="${file.id}">
                    <div class="fm-file-check">
                        <i class="fas fa-${state.selectedFileIds.has(file.id) ? "check-circle" : "circle"}"></i>
                    </div>
                    <div class="fm-file-icon"><i class="fas fa-file"></i></div>
                    <div class="fm-file-info">
                        <div class="fm-file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
                        <div class="fm-file-meta">${file.status === "ready" ? "Indexed" : "Error"} · ${formatFileSize(file.size)}</div>
                    </div>
                    <button class="fm-file-summarize" data-file-id="${file.id}" title="Summarize this file">
                        <i class="fas fa-file-lines"></i>
                    </button>
                    <button class="fm-file-delete" data-file-id="${file.id}" title="Delete file">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `
        )
        .join("");
}

function handleFileManageActions(event) {
    event.stopPropagation();
    const deleteBtn = event.target.closest(".fm-file-delete");
    if (deleteBtn) {
        const fileId = deleteBtn.dataset.fileId;
        if (fileId) deleteUploadedFile(fileId);
        return;
    }
    const summarizeBtn = event.target.closest(".fm-file-summarize");
    if (summarizeBtn) {
        const fileId = summarizeBtn.dataset.fileId;
        if (fileId) summarizeFile(fileId);
        return;
    }
    const row = event.target.closest(".fm-file-item");
    if (!row) return;
    const fileId = row.dataset.fileId;
    if (!fileId) return;
    if (state.selectedFileIds.has(fileId)) {
        state.selectedFileIds.delete(fileId);
    } else {
        state.selectedFileIds.add(fileId);
    }
    persistSelectedFiles();
    updateSelectedFilesBar();
    renderFilesManageList();
}

function formatFileSize(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
    }
    return `${size.toFixed(1)} ${units[i]}`;
}

async function deleteUploadedFile(fileId) {
    try {
        const res = await apiFetch("/api/remove", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_id: fileId }),
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || "Delete failed");
        }
        state.files = state.files.filter((f) => f.id !== fileId);
        state.selectedFileIds.delete(fileId);
        persistSelectedFiles();
        updateSelectedFilesBar();
        renderFilesManageList();
        showToast("File deleted", "success");
    } catch (error) {
        showToast(error.message || "Failed to delete file", "error");
    }
}

function summarizeFile(fileId) {
    state.selectedFileIds.clear();
    state.selectedFileIds.add(fileId);
    persistSelectedFiles();
    updateSelectedFilesBar();
    closeFilesManagePanel();
    if (dom.messageInput) {
        dom.messageInput.value = "Summarize this document in detail with key bullet points.";
        autoResizeInput();
        updateSendButtonState();
        dom.messageInput.focus();
    }
}

async function createNewChat() {
    try {
        const res = await apiFetch("/api/chat/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || "Failed to create chat");
        }
        state.currentSessionId = data.session.session_id;
        sessionStorage.setItem("current_chat_session", state.currentSessionId);
        state.history = [];
        renderMessages([]);
        await loadChatSessions();
        updateSessionHeader();
        closeMobilePanels();
    } catch (error) {
        console.error("Failed to create chat:", error);
        showToast("Failed to create a new chat.", "error");
    }
}

async function loadChatSessions() {
    try {
        const res = await fetch("/api/chat/sessions");
        const data = await res.json();
        state.sessions = Array.isArray(data.sessions) ? data.sessions : [];

        if (!state.currentSessionId && state.sessions.length) {
            state.currentSessionId = state.sessions[0].session_id;
            sessionStorage.setItem("current_chat_session", state.currentSessionId);
        }
        renderSessionLists();
    } catch (error) {
        console.error("Failed to load sessions:", error);
    }
}

function renderSessionLists() {
    const current = state.sessions.find(
        (session) => session.session_id === state.currentSessionId
    );
    const past = state.sessions.filter(
        (session) => session.session_id !== state.currentSessionId
    );

    dom.currentChatList.innerHTML = current 
        ? renderSessionItem(current, true)
        : `<div class="empty-state">No active session</div>`;

    dom.pastChatList.innerHTML = past.length
        ? past.map((session) => renderSessionItem(session, false)).join("")
        : `<div class="empty-state">No past chats yet</div>`;
}

function renderSessionItem(session, active) {
    const title = escapeHtml(session.title || "New Chat");
    return `
        <article class="chat-item ${active ? "active" : ""}" data-session-id="${session.session_id}">
            <div class="chat-item-main">
                <div class="chat-item-title">${title}</div>
                <div class="chat-item-meta">Last updated ${formatRelativeTime(session.updated_at)}</div>
            </div>
            <button class="chat-item-delete" data-action="delete-session" title="Delete chat">
                <i class="fas fa-trash"></i>
            </button>
        </article>
    `;
}

function filterSessionLists() {
    const query = (dom.sessionsSearchInput?.value || "").toLowerCase();
    const currentItems = dom.currentChatList?.querySelectorAll(".chat-item") || [];
    const pastItems = dom.pastChatList?.querySelectorAll(".chat-item") || [];
    for (const item of currentItems) {
        const title = item.querySelector(".chat-item-title")?.textContent || "";
        item.style.display = title.toLowerCase().includes(query) ? "" : "none";
    }
    for (const item of pastItems) {
        const title = item.querySelector(".chat-item-title")?.textContent || "";
        item.style.display = title.toLowerCase().includes(query) ? "" : "none";
    }
}

function handleSessionListClick(event) {
    const deleteBtn = event.target.closest('[data-action="delete-session"]');
    const row = event.target.closest("[data-session-id]");
    if (!row) {
        return;
    }
    const sessionId = row.dataset.sessionId;
    if (!sessionId) {
        return;
    }

    if (deleteBtn) {
        event.stopPropagation();
        deleteChat(sessionId);
        return;
    }

    switchChat(sessionId);
}

async function switchChat(sessionId) {
    if (!sessionId || sessionId === state.currentSessionId) {
        return;
    }
    state.currentSessionId = sessionId;
    sessionStorage.setItem("current_chat_session", state.currentSessionId);

    await loadPersistedChat(sessionId);
    renderSessionLists();
    updateSessionHeader();
    closeMobilePanels();
}

async function deleteChat(sessionId) {
    if (!confirm("Delete this conversation?")) {
        return;
    }
    try {
        const res = await apiFetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
            method: "DELETE",
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || "Failed to delete session");
        }

        if (sessionId === state.currentSessionId) {
            state.currentSessionId = data.current_session_id || "";
            sessionStorage.setItem("current_chat_session", state.currentSessionId);
            await loadPersistedChat(state.currentSessionId);
        }
        await loadChatSessions();
        updateSessionHeader();
        showToast("Conversation deleted.", "success");
    } catch (error) {
        console.error("Failed to delete chat:", error);
        showToast("Failed to delete the conversation.", "error");
    }
}

async function clearCurrentChat() {
    if (!state.currentSessionId) {
        return;
    }
    if (!confirm("Clear this conversation?")) {
        return;
    }
    try {
        await apiFetch(
            `/api/chat/session?session_id=${encodeURIComponent(state.currentSessionId)}`,
            { method: "DELETE" }
        );
        state.history = [];
        renderMessages([]);
        await loadChatSessions();
        updateSessionHeader();
        showToast("Chat cleared.", "success");
    } catch (error) {
        console.error("Failed to clear chat:", error);
        showToast("Failed to clear the conversation.", "error");
    }
}

async function loadPersistedChat(sessionId) {
    try {
        const suffix = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
        const res = await fetch(`/api/chat/session${suffix}`);
        const data = await res.json();

        const messages = Array.isArray(data.messages) ? data.messages : [];
        state.history = messages.map((message) => ({
            role: message.role === "assistant" ? "assistant" : "user",
            content: message.content || "",
        }));
        renderMessages(messages);
    } catch (error) {
        console.error("Failed to load chat session:", error);
    }
}

function renderMessages(messages) {
    dom.messages.innerHTML = "";

    if (!messages.length) {
        dom.welcomePanel.style.display = "block";
        return;
    }

    dom.welcomePanel.style.display = "none";
    const fragment = document.createDocumentFragment();
    for (const message of messages) {
        const role = message.role === "assistant" ? "bot" : "user";
        const text = message.content || "";
        const sources = message.sources || [];

        const wrapper = document.createElement("div");
        wrapper.className = `message ${role}`;
        if (message.message_id) {
            wrapper.id = `msg-${message.message_id}`;
        }
        if (sources.length) {
            wrapper.dataset.sources = JSON.stringify(sources);
        }

        const body = role === "bot"
            ? DOMPurify.sanitize(marked.parse(text))
            : escapeHtml(text).replace(/\n/g, "<br>");

        wrapper.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-${role === "bot" ? "robot" : "user"}"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">${body}</div>
            </div>
        `;

        if (role === "bot") {
            const contentDiv = wrapper.querySelector(".message-content");

            const feedbackRow = document.createElement("div");
            feedbackRow.className = "message-actions";
            feedbackRow.innerHTML = `
                <button class="action-btn copy-btn" title="Copy message"><i class="fas fa-copy"></i></button>
                <button class="action-btn regenerate-btn" title="Regenerate"><i class="fas fa-rotate"></i></button>
                <button class="action-btn thumbs-up ${message.feedback === 1 ? "active" : ""}" data-message-id="${message.message_id || ""}" data-value="1"><i class="fas fa-thumbs-up"></i></button>
                <button class="action-btn thumbs-down ${message.feedback === -1 ? "active" : ""}" data-message-id="${message.message_id || ""}" data-value="-1"><i class="fas fa-thumbs-down"></i></button>
            `;
            contentDiv.appendChild(feedbackRow);
        }

        fragment.appendChild(wrapper);
    }
    dom.messages.appendChild(fragment);
    scrollMessagesToBottom();
}

function updateSessionHeader() {
    const current = state.sessions.find(
        (session) => session.session_id === state.currentSessionId
    );
    if (!current) {
        dom.sessionTitle.textContent = "New Chat";
        dom.sessionUpdatedAt.textContent = "Last updated just now";
        return;
    }
    dom.sessionTitle.textContent = current.title || "New Chat";
    dom.sessionUpdatedAt.textContent = `Last updated ${formatRelativeTime(current.updated_at)}`;
}

function startRenameSession() {
    const current = state.sessions.find(
        (session) => session.session_id === state.currentSessionId
    );
    if (!current) {
        return;
    }

    const wrapper = dom.sessionTitle.parentElement;
    const input = document.createElement("input");
    input.type = "text";
    input.className = "rename-input";
    input.value = current.title || "";
    input.maxLength = 80;

    dom.sessionTitle.style.display = "none";
    wrapper.insertBefore(input, dom.sessionTitle);
    input.focus();
    input.select();

    const commit = () => commitRenameSession(input, current.session_id);
    input.addEventListener("blur", commit);
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            input.blur();
        }
        if (event.key === "Escape") {
            input.value = current.title || "";
            input.blur();
        }
    });
}

async function commitRenameSession(input, sessionId) {
    const title = input.value.trim();
    input.remove();

    dom.sessionTitle.style.display = "";

    if (!title || !sessionId || title === dom.sessionTitle.textContent) {
        return;
    }

    try {
        const res = await apiFetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title }),
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || "Failed to rename");
        }
        dom.sessionTitle.textContent = title;
        await loadChatSessions();
        showToast("Session renamed.", "success");
    } catch (error) {
        console.error("Failed to rename session:", error);
        showToast("Failed to rename session.", "error");
    }
}

function exportConversation() {
    const history = state.history;
    if (!history.length) {
        showToast("No messages to export.", "info");
        return;
    }
    const title = dom.sessionTitle?.textContent || "Chat";
    const lines = [`# ${title}\n`];
    for (const msg of history) {
        const role = msg.role === "assistant" ? "**Assistant**" : "**You**";
        lines.push(`### ${role}\n${msg.content}\n`);
    }
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/[^a-zA-Z0-9 ]/g, "").trim() || "chat"}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Conversation exported.", "success");
}

async function regenerateAnswer() {
    const question = state.lastQuery;
    if (!question || state.sending) return;

    state.sending = true;
    updateSendButtonState();

    const lastBotMsg = dom.messages?.querySelector(".message.bot:last-of-type");
    if (lastBotMsg) lastBotMsg.remove();

    for (let i = state.history.length - 1; i >= 0; i--) {
        if (state.history[i].role === "assistant") {
            state.history.splice(i, 1);
            break;
        }
    }

    const historyToSend = state.history.slice(-12);
    const ok = await sendMessageStreaming(question, state.lastContextIds, historyToSend);
    if (!ok) {
        await sendMessageNonStreaming(question, state.lastContextIds, historyToSend);
    }
}

async function sendMessage() {
    const message = (dom.messageInput.value || "").trim();
    if (!message || state.sending) {
        return;
    }

    state.sending = true;
    updateSendButtonState();

    dom.welcomePanel.style.display = "none";
    appendMessage("user", message);
    state.history.push({ role: "user", content: message });

    dom.messageInput.value = "";
    autoResizeInput();
    updateSendButtonState();

    const selectedReadyIds = Array.from(state.selectedFileIds).filter((id) => {
        const file = state.files.find((entry) => entry.id === id);
        return file && file.status === "ready";
    });
    const contextIds = selectedReadyIds.length
        ? selectedReadyIds
        : state.files.filter((file) => file.status === "ready").map((file) => file.id);
    state.lastQuery = message;
    state.lastContextIds = contextIds;
    const historyToSend = state.history.slice(0, -1).slice(-12);

    const ok = await sendMessageStreaming(message, contextIds, historyToSend);
    if (!ok) {
        await sendMessageNonStreaming(message, contextIds, historyToSend);
    }
}

async function sendMessageStreaming(question, contextIds, historyToSend) {
    const typingId = showTypingIndicator();

    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 120000);

        const res = await apiFetch("/api/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question,
                session_id: state.currentSessionId,
                file_ids: contextIds,
                history: historyToSend,
            }),
            signal: controller.signal,
        });
        clearTimeout(timer);

        if (!res.ok) {
            removeTypingIndicator(typingId);
            return false;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let botMessage = "";
        let result = null;
        const botId = `stream_${Date.now()}`;

        removeTypingIndicator(typingId);
        appendMessage("bot", "", [], botId);
        const botEl = document.getElementById(botId);
        const botBubble = botEl?.querySelector(".message-bubble");

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split("\n\n");
            buffer = parts.pop() || "";

            for (const part of parts) {
                const lines = part.split("\n");
                let eventType = "";
                let data = "";

                for (const line of lines) {
                    if (line.startsWith("event: ")) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith("data: ")) {
                        data = line.slice(6).trim();
                    }
                }

                if (!data) {
                    continue;
                }

                if (eventType === "token") {
                    botMessage += data;
                    if (botBubble) {
                        botBubble.innerHTML = DOMPurify.sanitize(marked.parse(botMessage || ""));
                    }
                } else if (eventType === "done") {
                    try {
                        result = JSON.parse(data);
                    } catch {
                        result = null;
                    }
                } else if (eventType === "error") {
                    try {
                        const errData = JSON.parse(data);
                        result = { error: errData.message || "Stream error" };
                    } catch {
                        result = { error: data };
                    }
                }
            }
        }

        if (result && result.response) {
            const finalSources = result.sources || [];
            if (botBubble) {
                botBubble.innerHTML = DOMPurify.sanitize(marked.parse(result.response || ""));
            }
            if (botEl && result.message_id) {
                const actions = botEl.querySelector(".message-actions");
                if (actions) {
                    const feedbackHtml = `
                        <button class="action-btn thumbs-up" data-message-id="${result.message_id}" data-value="1"><i class="fas fa-thumbs-up"></i></button>
                        <button class="action-btn thumbs-down" data-message-id="${result.message_id}" data-value="-1"><i class="fas fa-thumbs-down"></i></button>
                    `;
                    actions.insertAdjacentHTML("beforeend", feedbackHtml);
                }
            }
            state.history.push({ role: "assistant", content: result.response });

            if (result.session_id && result.session_id !== state.currentSessionId) {
                state.currentSessionId = result.session_id;
                sessionStorage.setItem("current_chat_session", state.currentSessionId);
            }

            await loadChatSessions();
            updateSessionHeader();
            return true;
        }

        if (result && result.error) {
            if (botBubble) {
                botBubble.textContent = result.error;
            }
            state.history.push({ role: "assistant", content: result.error });
            return true;
        }

        if (botMessage) {
            state.history.push({ role: "assistant", content: botMessage });
            return true;
        }

        return false;
    } catch (error) {
        removeTypingIndicator(typingId);
        if (error.name === "AbortError") {
            appendMessage("bot", "The request timed out. Please try again.", []);
            state.history.push({ role: "assistant", content: "The request timed out. Please try again." });
            return true;
        }
        return false;
    } finally {
        state.sending = false;
        updateSendButtonState();
    }
}

async function sendMessageNonStreaming(question, contextIds, historyToSend) {
    const typingId = showTypingIndicator();

    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 120000);

        const res = await apiFetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question,
                session_id: state.currentSessionId,
                file_ids: contextIds,
                history: historyToSend,
            }),
            signal: controller.signal,
        });
        clearTimeout(timer);

        const data = await res.json();
        removeTypingIndicator(typingId);

        const responseText =
            data.response || data.error || "Could not generate a response right now.";
        appendMessage("bot", responseText, data.sources || []);
        state.history.push({ role: "assistant", content: responseText });

        if (data.session_id && data.session_id !== state.currentSessionId) {
            state.currentSessionId = data.session_id;
            sessionStorage.setItem("current_chat_session", state.currentSessionId);
        }

        await loadChatSessions();
        updateSessionHeader();
    } catch (error) {
        removeTypingIndicator(typingId);
        const fallback =
            error.name === "AbortError"
                ? "The request timed out. Please try again."
                : "Could not reach the server. Please try again.";
        appendMessage("bot", fallback, []);
        state.history.push({ role: "assistant", content: fallback });
    } finally {
        state.sending = false;
        updateSendButtonState();
    }
}

function appendMessage(role, text, sources = [], id = "") {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;
    if (id) {
        wrapper.id = id;
    }
    wrapper.dataset.sources = JSON.stringify(sources);

    const body =
        role === "bot"
            ? DOMPurify.sanitize(marked.parse(text || ""))
            : escapeHtml(text || "").replace(/\n/g, "<br>");

    wrapper.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-${role === "bot" ? "robot" : "user"}"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">${body}</div>
        </div>
    `;

    if (role === "bot") {
        const contentDiv = wrapper.querySelector(".message-content");
        const feedbackRow = document.createElement("div");
        feedbackRow.className = "message-actions";
        feedbackRow.innerHTML = `
            <button class="action-btn copy-btn" title="Copy message"><i class="fas fa-copy"></i></button>
            <button class="action-btn regenerate-btn" title="Regenerate"><i class="fas fa-rotate"></i></button>
        `;
        contentDiv.appendChild(feedbackRow);
    }

    dom.messages.appendChild(wrapper);
    scrollMessagesToBottom();
}

function showTypingIndicator() {
    const id = `typing_${Date.now()}`;
    const wrapper = document.createElement("div");
    wrapper.className = "message bot";
    wrapper.id = id;
    wrapper.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    dom.messages.appendChild(wrapper);
    scrollMessagesToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) {
        el.remove();
    }
}

function scrollMessagesToBottom() {
    dom.messages.scrollTop = dom.messages.scrollHeight;
    const stage = document.querySelector(".chat-stage");
    if (stage) {
        stage.scrollTop = stage.scrollHeight;
    }
}

async function loadFiles() {
    try {
        const res = await fetch("/api/files", { cache: "no-store" });
        const data = await res.json();
        const files = Object.entries(data.files || {}).map(([fileId, entry]) => ({
            id: fileId,
            name: entry.name || "Untitled",
            ext: getExtension(entry.name || ""),
            size: Number(entry.size || 0),
            chunks: Number(entry.chunks || 0),
            uploadedAt: Number(entry.uploaded_at || 0),
            indexed: Boolean(entry.indexed),
            status: entry.indexed ? "ready" : "error",
            source: entry.source || "local",
        }));

        state.files = files.sort((a, b) => b.uploadedAt - a.uploadedAt);
        state.selectedFileIds = new Set(
            Array.from(state.selectedFileIds).filter((id) => {
                const file = state.files.find((entry) => entry.id === id);
                return Boolean(file && file.status === "ready");
            })
        );
        persistSelectedFiles();

        updateSelectedFilesBar();
        renderFilesManageList();
    } catch (error) {
        console.error("Failed to load files:", error);
    }
}

function updateSelectedFilesBar() {
    if (!state.selectedFileIds.size) {
        dom.selectedFilesBar.classList.remove("show");
        return;
    }

    const selected = state.files.filter((file) => state.selectedFileIds.has(file.id));
    dom.selectedFilesChips.innerHTML = selected
        .map(
            (file) => `
                <span class="selected-file-chip">
                    <span class="chip-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
                    <button class="chip-remove" data-file-id="${file.id}" title="Remove">
                        <i class="fas fa-xmark"></i>
                    </button>
                </span>
            `
        )
        .join("");
    dom.selectedFilesBar.classList.add("show");
}

function handleChipRemove(event) {
    const btn = event.target.closest(".chip-remove");
    if (!btn) return;
    const fileId = btn.dataset.fileId;
    if (!fileId) return;
    state.selectedFileIds.delete(fileId);
    persistSelectedFiles();
    updateSelectedFilesBar();
}

function clearFileSelection() {
    state.selectedFileIds.clear();
    persistSelectedFiles();
    updateSelectedFilesBar();
}

async function removeFile(fileId) {
    try {
        const res = await apiFetch("/api/remove", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_id: fileId }),
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || "Failed to remove file");
        }
        state.selectedFileIds.delete(fileId);
        await loadFiles();
    } catch (error) {
        console.error("Failed to remove file:", error);
        showToast("Failed to remove the file.", "error");
    }
}

async function handleFileUpload(files) {
    const allowedExts = new Set(["pdf", "docx", "doc", "pptx", "xlsx", "xls", "csv", "txt"]);
    const valid = files.filter((file) => allowedExts.has(getExtension(file.name)));
    if (!valid.length) {
        return;
    }

    const existingNames = new Set(state.files.map((f) => f.name));
    const toUpload = [];
    const duplicates = [];
    for (const file of valid) {
        if (existingNames.has(file.name)) {
            duplicates.push(file.name);
        } else {
            toUpload.push(file);
        }
    }
    for (const name of duplicates) {
        showToast(`"${escapeHtml(name)}" is already uploaded`, "info");
    }
    if (!toUpload.length) {
        return;
    }

    const uploadedIds = [];
    let processed = 0;
    const total = toUpload.length;
    const errors = [];

    setUploadProgress({
        visible: true,
        title: "Processing files...",
        text: `Starting ${total} file${total === 1 ? "" : "s"}...`,
        percent: 4,
    });

    await runWithConcurrency(toUpload, 2, async (file) => {
        try {
            setUploadProgress({
                visible: true,
                title: "Uploading and indexing...",
                text: file.name,
                percent: Math.max(8, Math.round((processed / total) * 100)),
            });
            const result = await uploadSingleFile(file);
            if (result?.file_id) {
                uploadedIds.push(result.file_id);
            }
        } catch (error) {
            errors.push(`${file.name}: ${error.message}`);
        } finally {
            processed += 1;
            setUploadProgress({
                visible: true,
                text: `${processed}/${total} completed`,
                percent: Math.round((processed / total) * 100),
            });
        }
    });

    await loadFiles();

    for (const id of uploadedIds) {
        state.selectedFileIds.add(id);
    }
    persistSelectedFiles();
    updateSelectedFilesBar();

    if (errors.length) {
        setUploadProgress({
            visible: true,
            title: "Completed with errors",
            text: `${errors.length} failed, ${total - errors.length} uploaded`,
            percent: 100,
        });
    } else {
        setUploadProgress({
            visible: true,
            title: "Upload complete",
            text: `${total} file${total === 1 ? "" : "s"} indexed`,
            percent: 100,
        });
    }

    setTimeout(() => setUploadProgress({ visible: false }), 1500);
}

async function uploadSingleFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
        const res = await apiFetch("/api/upload", {
            method: "POST",
            body: formData,
            signal: controller.signal,
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || "Upload failed");
        }
        return data;
    } finally {
        clearTimeout(timeoutId);
    }
}

function setUploadProgress({ visible, title, text, percent }) {
    if (visible) {
        dom.uploadProgressCard.classList.add("show");
    } else {
        dom.uploadProgressCard.classList.remove("show");
    }
    if (typeof title === "string") {
        dom.uploadProgressTitle.textContent = title;
    }
    if (typeof text === "string") {
        dom.uploadProgressText.textContent = text;
    }
    if (typeof percent === "number") {
        dom.uploadProgressFill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    }
}

async function loadOneDriveStatus() {
    try {
        const res = await fetch("/api/onedrive/status");
        const data = await res.json();
        state.oneDrive.enabled = Boolean(data.enabled);
        state.oneDrive.connected = Boolean(data.connected);
        state.oneDrive.user = data.user || "";
        state.oneDrive.email = data.email || "";
        renderOneDriveStatus();

        if (state.oneDrive.connected) {
            await loadOneDriveFiles("root", true);
        } else {
            state.oneDrive.items = [];
            renderOneDriveFiles();
        }
    } catch (error) {
        console.error("Failed to load OneDrive status:", error);
        showToast("Failed to check OneDrive connection.", "error");
    }
}

function renderOneDriveStatus() {
    if (!state.oneDrive.enabled) {
        dom.odStatusText.textContent = "OneDrive integration is not configured";
        dom.odUserText.textContent = "Set Azure credentials in .env to enable cloud import.";
        dom.odConnectBtn.style.display = "none";
        dom.odDisconnectBtn.style.display = "none";
        dom.odBackBtn.disabled = true;
        dom.odRefreshBtn.disabled = true;
        dom.odImportBtn.disabled = true;
        return;
    }

    if (state.oneDrive.connected) {
        dom.odStatusText.textContent = "OneDrive connected";
        const identity = [state.oneDrive.user, state.oneDrive.email].filter(Boolean).join(" · ");
        dom.odUserText.textContent = identity || "Connected";
        dom.odConnectBtn.style.display = "none";
        dom.odDisconnectBtn.style.display = "inline-flex";
        dom.odRefreshBtn.disabled = false;
        dom.odImportBtn.disabled = false;
    } else {
        dom.odStatusText.textContent = "OneDrive not connected";
        dom.odUserText.textContent = "Connect to browse folders and import supported files.";
        dom.odConnectBtn.style.display = "inline-flex";
        dom.odDisconnectBtn.style.display = "none";
        dom.odBackBtn.disabled = true;
        dom.odRefreshBtn.disabled = true;
        dom.odImportBtn.disabled = true;
    }

    updateOneDrivePathLabel();
    updateOneDriveSelectionCounter();
}

async function disconnectOneDrive() {
    try {
        await apiFetch("/onedrive/disconnect", { method: "POST" });
        state.oneDrive.connected = false;
        state.oneDrive.user = "";
        state.oneDrive.email = "";
        state.oneDrive.items = [];
        state.oneDrive.selectedItems.clear();
        state.oneDrive.currentFolderId = "root";
        state.oneDrive.folderStack = [{ id: "root", name: "Root", path: "/" }];
        renderOneDriveStatus();
        renderOneDriveFiles();
    } catch (error) {
        console.error("Failed to disconnect OneDrive:", error);
        showToast("Failed to disconnect OneDrive.", "error");
    }
}

async function loadOneDriveFiles(folderId = "root", resetStack = false) {
    if (!state.oneDrive.connected) {
        return;
    }
    try {
        state.oneDrive.loading = true;
        renderOneDriveFiles();

        const res = await fetch(
            `/api/onedrive/files?folder=${encodeURIComponent(folderId)}`
        );
        const data = await res.json();
        if (!res.ok || data.success === false) {
            throw new Error(data.error || "Failed to load OneDrive files");
        }

        const items = Array.isArray(data.files) ? data.files : [];
        state.oneDrive.items = items.sort((a, b) => {
            const aFolder = Boolean(a.isFolder);
            const bFolder = Boolean(b.isFolder);
            if (aFolder !== bFolder) {
                return aFolder ? -1 : 1;
            }
            return (a.name || "").localeCompare(b.name || "");
        });
        state.oneDrive.currentFolderId = folderId || "root";

        if (resetStack) {
            state.oneDrive.folderStack = [{ id: "root", name: "Root", path: "/" }];
        }
        updateOneDrivePathLabel();
    } catch (error) {
        console.error("Failed to load OneDrive files:", error);
        showToast("Failed to load OneDrive folder.", "error");
    } finally {
        state.oneDrive.loading = false;
        renderOneDriveFiles();
    }
}

function renderOneDriveFiles() {
    if (!state.oneDrive.connected) {
        dom.odFilesList.innerHTML = `<div class="empty-state">Connect OneDrive to browse files.</div>`;
        return;
    }

    if (state.oneDrive.loading) {
        dom.odFilesList.innerHTML = `<div class="empty-state">Loading OneDrive files...</div>`;
        return;
    }

    if (!state.oneDrive.items.length) {
        dom.odFilesList.innerHTML = `<div class="empty-state">No supported files in this folder.</div>`;
        return;
    }

    dom.odFilesList.innerHTML = state.oneDrive.items
        .map((item) => {
            const isFolder = Boolean(item.isFolder);
            const selected = state.oneDrive.selectedItems.has(item.id);

            return `
                <article class="od-item ${isFolder ? "folder" : "file"}" data-item-id="${item.id}">
                    <div class="od-icon">
                        <i class="fas ${isFolder ? "fa-folder" : "fa-file-lines"}"></i>
                    </div>
                    <div>
                        <div class="od-name" title="${escapeHtml(item.name || "")}">${escapeHtml(item.name || "")}</div>
                        <div class="od-meta">${isFolder ? "Folder" : formatBytes(Number(item.size || 0))}</div>
                    </div>
                    <div class="od-actions">
                        ${
                            isFolder
                                ? '<i class="fas fa-angle-right" aria-hidden="true"></i>'
                                : `<input type="checkbox" data-action="od-select" data-item-id="${item.id}" ${
                                      selected ? "checked" : ""
                                  }>`
                        }
                    </div>
                </article>
            `;
        })
        .join("");
}

function handleMessageActions(event) {
    const copyBtn = event.target.closest(".copy-btn");
    if (copyBtn) {
        const messageEl = copyBtn.closest(".message");
        const bubble = messageEl?.querySelector(".message-bubble");
        const text = bubble?.textContent || messageEl?.querySelector(".message-content")?.textContent || "";
        const icon = copyBtn.querySelector("i");
        const origClass = icon?.className;
        if (icon) {
            icon.className = "fas fa-check";
        }
        setTimeout(() => {
            if (icon && origClass) icon.className = origClass;
        }, 1500);

        if (navigator.clipboard?.writeText) {
            navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
        } else {
            fallbackCopy(text);
        }
        return;
    }

    const regenBtn = event.target.closest(".regenerate-btn");
    if (regenBtn) {
        regenerateAnswer();
        return;
    }

    const thumb = event.target.closest(".thumbs-up, .thumbs-down");
    if (!thumb) return;

    const messageId = Number(thumb.dataset.messageId);
    const value = Number(thumb.dataset.value);
    if (!messageId) return;

    const wasActive = thumb.classList.contains("active");
    const newFeedback = wasActive ? null : value;

    const siblings = thumb.closest(".message-actions")?.querySelectorAll(".thumbs-up, .thumbs-down") || [];
    for (const btn of siblings) {
        btn.classList.remove("active");
    }

    if (!wasActive) {
        thumb.classList.add("active");
    }

    apiFetch("/api/chat/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: messageId, feedback: newFeedback }),
    }).catch(() => {});
}

function fallbackCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
        document.execCommand("copy");
    } catch (e) {
        // ignored
    }
    document.body.removeChild(ta);
}

function handleOneDriveListClick(event) {
    event.stopPropagation();
    const checkbox = event.target.closest('[data-action="od-select"]');
    if (checkbox) {
        const id = checkbox.dataset.itemId;
        const item = state.oneDrive.items.find((entry) => entry.id === id);
        if (!item || item.isFolder) {
            return;
        }
        if (checkbox.checked) {
            state.oneDrive.selectedItems.set(item.id, item);
        } else {
            state.oneDrive.selectedItems.delete(item.id);
        }
        updateOneDriveSelectionCounter();
        return;
    }

    const row = event.target.closest("[data-item-id]");
    if (!row) {
        return;
    }
    const itemId = row.dataset.itemId;
    const item = state.oneDrive.items.find((entry) => entry.id === itemId);
    if (!item) {
        return;
    }

    if (item.isFolder) {
        const path = `/${item.path || item.name || ""}`.replace(/\/+/g, "/");
        state.oneDrive.folderStack.push({
            id: item.id,
            name: item.name || "Folder",
            path,
        });
        loadOneDriveFiles(item.id);
        return;
    }

    if (state.oneDrive.selectedItems.has(item.id)) {
        state.oneDrive.selectedItems.delete(item.id);
    } else {
        state.oneDrive.selectedItems.set(item.id, item);
    }
    updateOneDriveSelectionCounter();
    renderOneDriveFiles();
}

function goBackOneDriveFolder() {
    if (state.oneDrive.folderStack.length <= 1) {
        closeOneDrivePanel();
        return;
    }
    state.oneDrive.folderStack.pop();
    const parent = state.oneDrive.folderStack[state.oneDrive.folderStack.length - 1];
    loadOneDriveFiles(parent?.id || "root");
}

function updateOneDrivePathLabel() {
    const current = state.oneDrive.folderStack[state.oneDrive.folderStack.length - 1];
    dom.odPathLabel.textContent = current?.path || "/";
    dom.odBackBtn.disabled = state.oneDrive.folderStack.length <= 1;
}

function updateOneDriveSelectionCounter() {
    const count = state.oneDrive.selectedItems.size;
    dom.odSelectionCount.textContent = `${count} selected`;
}

async function importSelectedOneDriveFiles() {
    if (!state.oneDrive.selectedItems.size) {
        return;
    }
    try {
        const items = Array.from(state.oneDrive.selectedItems.values()).map((item) => ({
            id: item.id,
            item_id: item.id,
            name: item.name,
            size: item.size,
            download_url: item.download_url,
        }));

        setUploadProgress({
            visible: true,
            title: "Importing from OneDrive...",
            text: `${items.length} file${items.length === 1 ? "" : "s"} selected`,
            percent: 35,
        });

        const res = await apiFetch("/api/onedrive/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ files: items }),
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || "Import failed");
        }

        const importedCount = Array.isArray(data.imported) ? data.imported.length : 0;
        const skippedCount = Array.isArray(data.skipped) ? data.skipped.length : 0;
        const errorCount = Array.isArray(data.errors) ? data.errors.length : 0;

        state.oneDrive.selectedItems.clear();
        updateOneDriveSelectionCounter();
        await loadFiles();

        const imported = data.imported || [];
        for (const item of imported) {
            if (item.file_id) {
                state.selectedFileIds.add(item.file_id);
            }
        }
        console.log("OneDrive import - selectedFileIds:", [...state.selectedFileIds], "files:", state.files.length);
        persistSelectedFiles();
        updateSelectedFilesBar();
        closeOneDrivePanel();

        setUploadProgress({
            visible: true,
            title: "Import complete",
            text: `Imported ${importedCount} · Skipped ${skippedCount} · Errors ${errorCount}`,
            percent: 100,
        });
        setTimeout(() => setUploadProgress({ visible: false }), 1800);
    } catch (error) {
        setUploadProgress({
            visible: true,
            title: "Import failed",
            text: error.message || "Unable to import OneDrive files.",
            percent: 100,
        });
        setTimeout(() => setUploadProgress({ visible: false }), 2200);
        console.error("OneDrive import failed:", error);
    }
}

function restoreSelectedFiles() {
    const parsed = safeJson(sessionStorage.getItem("selected_file_ids"), []);
    if (!Array.isArray(parsed)) {
        return;
    }
    state.selectedFileIds = new Set(parsed.filter((value) => typeof value === "string"));
}

function persistSelectedFiles() {
    sessionStorage.setItem(
        "selected_file_ids",
        JSON.stringify(Array.from(state.selectedFileIds))
    );
}

function getExtension(name) {
    const dot = name.lastIndexOf(".");
    if (dot < 0) {
        return "file";
    }
    return name.slice(dot + 1).toLowerCase();
}

function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) {
        return "0 B";
    }
    const units = ["B", "KB", "MB", "GB"];
    const power = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / 1024 ** power;
    return `${value.toFixed(value >= 10 || power === 0 ? 0 : 1)} ${units[power]}`;
}

function formatRelativeTime(timestampSeconds) {
    const timestampMs = Number(timestampSeconds || 0) * 1000;
    if (!timestampMs) {
        return "just now";
    }
    const diffMs = Date.now() - timestampMs;
    const diffSec = Math.round(diffMs / 1000);
    const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

    const units = [
        { limit: 60, unit: "second", value: diffSec },
        { limit: 3600, unit: "minute", value: Math.round(diffSec / 60) },
        { limit: 86400, unit: "hour", value: Math.round(diffSec / 3600) },
        { limit: 604800, unit: "day", value: Math.round(diffSec / 86400) },
        { limit: 2629800, unit: "week", value: Math.round(diffSec / 604800) },
        { limit: 31557600, unit: "month", value: Math.round(diffSec / 2629800) },
        { limit: Infinity, unit: "year", value: Math.round(diffSec / 31557600) },
    ];

    const chosen = units.find((entry) => Math.abs(diffSec) < entry.limit) || units[0];
    return rtf.format(chosen.value, chosen.unit);
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function safeJson(value, fallback) {
    if (!value) {
        return fallback;
    }
    try {
        return JSON.parse(value);
    } catch {
        return fallback;
    }
}

function showToast(message, type = "info", duration = 3500) {
    const container = document.getElementById("toastContainer");
    if (!container) {
        return;
    }

    const icons = { success: "fa-check-circle", error: "fa-circle-exclamation", info: "fa-info-circle" };
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<i class="fas ${icons[type] || icons.info} toast-icon"></i>${escapeHtml(message)}`;
    container.appendChild(el);

    setTimeout(() => {
        el.style.animation = "toastOut 0.25s ease forwards";
        setTimeout(() => el.remove(), 300);
    }, duration);
}

let dragCounter = 0;

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    dom.dropOverlay?.classList.add("show");
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    dom.dropOverlay?.classList.remove("show");
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    dom.dropOverlay?.classList.remove("show");

    const files = Array.from(event.dataTransfer?.files || []);
    if (!files.length) {
        return;
    }

    const allowedExts = new Set(["pdf", "docx", "doc", "pptx", "xlsx", "xls", "csv", "txt"]);
    const valid = files.filter((file) => allowedExts.has(getExtension(file.name)));

    if (!valid.length) {
        showToast("Unsupported file type. Accepted: PDF, DOCX, PPTX, XLSX, CSV, TXT", "error");
        return;
    }

    if (valid.length < files.length) {
        showToast(`${files.length - valid.length} file(s) skipped (unsupported format)`, "info");
    }

    handleFileUpload(valid);
}

async function runWithConcurrency(items, concurrency, worker) {
    if (!items.length) {
        return;
    }

    let index = 0;
    const runners = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
        while (index < items.length) {
            const item = items[index];
            index += 1;
            await worker(item);
        }
    });
    await Promise.all(runners);
}
