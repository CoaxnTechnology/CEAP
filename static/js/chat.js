const state = {
    files: [],
    selectedFileIds: new Set(),
    filesMode: "docs",
    sessions: [],
    currentSessionId: sessionStorage.getItem("current_chat_session") || "",
    history: [],
    sending: false,
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

    applyDarkModePreference();

    try {
        await Promise.all([loadFiles(), loadChatSessions(), loadOneDriveStatus()]);
        await loadPersistedChat(state.currentSessionId);
        switchFilesMode("docs");
        updateSessionHeader();
    } catch (error) {
        console.error("init failed:", error);
        showToast("Failed to load some data. Try refreshing the page.", "error");
    } finally {
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
    dom.mobileMenuBtn = document.getElementById("mobileMenuBtn");
    dom.closeMobileSidebarBtn = document.getElementById("closeMobileSidebarBtn");
    dom.filesPanelToggleBtn = document.getElementById("filesPanelToggleBtn");

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
    dom.selectedFilesText = document.getElementById("selectedFilesText");
    dom.clearFilesSelectionBtn = document.getElementById("clearFilesSelectionBtn");

    dom.localPane = document.getElementById("localPane");
    dom.oneDrivePane = document.getElementById("oneDrivePane");
    dom.filesModeDocsBtn = document.getElementById("filesModeDocsBtn");
    dom.filesModeOneDriveBtn = document.getElementById("filesModeOneDriveBtn");

    dom.fileInput = document.getElementById("fileInput");
    dom.refreshFilesBtn = document.getElementById("refreshFilesBtn");
    dom.filesList = document.getElementById("filesList");
    dom.filesCount = document.getElementById("filesCount");
    dom.filesChunks = document.getElementById("filesChunks");
    dom.filesSelectedBar = document.getElementById("filesSelectedBar");
    dom.filesSelectedBarText = document.getElementById("filesSelectedBarText");
    dom.filesSelectedClearBtn = document.getElementById("filesSelectedClearBtn");

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

    dom.citationOverlay = document.getElementById("citationOverlay");
    dom.citationCloseBtn = document.getElementById("citationCloseBtn");
    dom.citationTitle = document.getElementById("citationTitle");
    dom.citationMeta = document.getElementById("citationMeta");
    dom.citationBody = document.getElementById("citationBody");

    dom.darkModeToggle = document.getElementById("darkModeToggle");
    dom.composerPanel = document.getElementById("composerPanel");
    dom.dropOverlay = document.getElementById("dropOverlay");
}

function bindEvents() {
    dom.sessionsPanelToggleBtn?.addEventListener("click", toggleSessionsPanel);
    dom.mobileMenuBtn?.addEventListener("click", () => openMobilePanel("sessions"));
    dom.closeMobileSidebarBtn?.addEventListener("click", closeMobilePanels);
    dom.filesPanelToggleBtn?.addEventListener("click", toggleFilesPanel);
    dom.mobileBackdrop?.addEventListener("click", closeMobilePanels);

    dom.newChatBtn?.addEventListener("click", createNewChat);
    dom.clearChatBtn?.addEventListener("click", clearCurrentChat);
    dom.currentChatList?.addEventListener("click", handleSessionListClick);
    dom.pastChatList?.addEventListener("click", handleSessionListClick);

    dom.messageInput?.addEventListener("input", () => {
        autoResizeInput();
        updateSendButtonState();
    });
    dom.messageInput?.addEventListener("keydown", handleComposerKeydown);
    dom.sendBtn?.addEventListener("click", sendMessage);
    dom.chatUploadBtn?.addEventListener("click", () => {
        switchFilesMode("docs");
        ensureFilesPanelVisible();
        dom.fileInput?.click();
    });

    dom.clearFilesSelectionBtn?.addEventListener("click", clearFileSelection);
    dom.filesSelectedClearBtn?.addEventListener("click", clearFileSelection);
    dom.filesModeDocsBtn?.addEventListener("click", () => switchFilesMode("docs"));
    dom.filesModeOneDriveBtn?.addEventListener("click", () => switchFilesMode("onedrive"));

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
    dom.refreshFilesBtn?.addEventListener("click", loadFiles);
    dom.filesList?.addEventListener("click", handleFilesListClick);

    dom.odDisconnectBtn?.addEventListener("click", disconnectOneDrive);
    dom.odBackBtn?.addEventListener("click", goBackOneDriveFolder);
    dom.odRefreshBtn?.addEventListener("click", () =>
        loadOneDriveFiles(state.oneDrive.currentFolderId)
    );
    dom.odImportBtn?.addEventListener("click", importSelectedOneDriveFiles);
    dom.odFilesList?.addEventListener("click", handleOneDriveListClick);

    dom.messages?.addEventListener("click", handleCitationChipClick);
    dom.citationCloseBtn?.addEventListener("click", closeCitationModal);
    dom.citationOverlay?.addEventListener("click", (event) => {
        if (event.target === dom.citationOverlay) {
            closeCitationModal();
        }
    });

    dom.darkModeToggle?.addEventListener("click", toggleDarkMode);

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

function openMobilePanel(target) {
    const isMobile = window.innerWidth <= 980;
    if (!isMobile) {
        return;
    }

    if (target === "sessions") {
        dom.sessionsPanel.classList.add("open");
        dom.filesPanel.classList.remove("open");
    } else if (target === "files") {
        dom.filesPanel.classList.add("open");
        dom.sessionsPanel.classList.remove("open");
    }
    dom.mobileBackdrop.classList.add("show");
}

function closeMobilePanels() {
    dom.sessionsPanel.classList.remove("open");
    dom.filesPanel.classList.remove("open");
    dom.mobileBackdrop.classList.remove("show");
}

function toggleFilesPanel() {
    if (window.innerWidth <= 980) {
        if (dom.filesPanel.classList.contains("open")) {
            closeMobilePanels();
        } else {
            openMobilePanel("files");
        }
        return;
    }
    dom.appShell.classList.toggle("files-collapsed");
}

function toggleSessionsPanel() {
    if (window.innerWidth <= 980) {
        if (dom.sessionsPanel.classList.contains("open")) {
            closeMobilePanels();
        } else {
            openMobilePanel("sessions");
        }
        return;
    }
    dom.appShell.classList.toggle("sessions-collapsed");
}

function ensureFilesPanelVisible() {
    if (window.innerWidth <= 980) {
        openMobilePanel("files");
        return;
    }
    dom.appShell.classList.remove("files-collapsed");
}

function switchFilesMode(mode) {
    const normalized = mode === "onedrive" ? "onedrive" : "docs";
    state.filesMode = normalized;
    const docsMode = normalized === "docs";

    dom.filesModeDocsBtn?.classList.toggle("active", docsMode);
    dom.filesModeOneDriveBtn?.classList.toggle("active", !docsMode);
    dom.localPane?.classList.toggle("active", docsMode);
    dom.oneDrivePane?.classList.toggle("active", !docsMode);
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
    messages.forEach((message) => {
        appendMessage(
            message.role === "assistant" ? "bot" : "user",
            message.content || "",
            message.sources || []
        );
    });
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
            appendCitations(botId, finalSources, result);
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

    if (sources.length) {
        wrapper.dataset.sources = JSON.stringify(sources);
        appendCitations(wrapper, sources);
    }

    dom.messages.appendChild(wrapper);
    scrollMessagesToBottom();
}

function appendCitations(wrapperOrId, sources, result) {
    const wrapper = typeof wrapperOrId === "string" ? document.getElementById(wrapperOrId) : wrapperOrId;
    if (!wrapper) {
        return;
    }

    let existing = wrapper.querySelector(".message-citations");
    if (existing) {
        existing.remove();
    }

    if (!sources.length) {
        return;
    }

    wrapper.dataset.sources = JSON.stringify(result?.sources || sources);

    const contentDiv = wrapper.querySelector(".message-content");
    if (!contentDiv) {
        return;
    }

    const citations = document.createElement("div");
    citations.className = "message-citations";
    citations.innerHTML = sources
        .map(
            (source, index) => `
                <button class="citation-chip" data-action="open-citation" data-source-index="${index}">
                    <i class="fas fa-file-alt"></i>
                    ${escapeHtml(source.name || "Source")}
                </button>
            `
        )
        .join("");
    contentDiv.appendChild(citations);
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

function handleCitationChipClick(event) {
    const chip = event.target.closest('[data-action="open-citation"]');
    if (!chip) {
        return;
    }
    const sourceIndex = Number(chip.dataset.sourceIndex || -1);
    if (sourceIndex < 0) {
        return;
    }

    const message = chip.closest(".message");
    const sources = safeJson(message?.dataset.sources, []);
    const source = sources[sourceIndex];
    if (!source) {
        return;
    }

    dom.citationTitle.textContent = source.name || "Source";
    dom.citationMeta.textContent = `Chunk ${Number(source.chunk_index || 0) + 1} · ${
        source.source || "local"
    }`;
    dom.citationBody.textContent = source.text || source.excerpt || "No excerpt available.";
    dom.citationOverlay.classList.add("show");
}

function closeCitationModal() {
    dom.citationOverlay.classList.remove("show");
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

        renderFilesList();
        updateFilesStats();
        updateSelectedFilesBar();
    } catch (error) {
        console.error("Failed to load files:", error);
    }
}

function renderFilesList() {
    if (!state.files.length) {
        dom.filesList.innerHTML = `<div class="empty-state">No documents uploaded yet</div>`;
        return;
    }

    dom.filesList.innerHTML = state.files
        .map((file) => {
            const selected = state.selectedFileIds.has(file.id);
            const clickable = file.status === "ready";
            const title = escapeHtml(file.name);

            return `
                <article class="file-row ${selected ? "selected" : ""}" data-file-id="${file.id}">
                    <div class="file-icon ${file.ext}">${file.ext.toUpperCase() || "FILE"}</div>
                    <div>
                        <div class="file-name" title="${title}">${title}</div>
                        <div class="file-meta">
                            ${file.chunks} chunks · ${formatBytes(file.size)}${
                                clickable ? "" : " · Not indexed"
                            }
                        </div>
                    </div>
                    <div class="file-actions">
                        <div class="file-status ${file.status}" title="${file.status}"></div>
                        <button class="file-remove-btn" data-action="remove-file" title="Remove file">
                            <i class="fas fa-xmark"></i>
                        </button>
                    </div>
                </article>
            `;
        })
        .join("");
}

function updateFilesStats() {
    const readyFiles = state.files.filter((file) => file.status === "ready");
    const totalChunks = readyFiles.reduce((sum, file) => sum + file.chunks, 0);
    dom.filesCount.textContent = `${readyFiles.length} document${readyFiles.length === 1 ? "" : "s"}`;
    dom.filesChunks.textContent = `${totalChunks} chunk${totalChunks === 1 ? "" : "s"}`;
}

function updateSelectedFilesBar() {
    const selectedCount = state.selectedFileIds.size;

    if (!state.selectedFileIds.size) {
        dom.selectedFilesBar.classList.remove("show");
        dom.selectedFilesText.textContent = "No files selected";
    } else {
        const selected = state.files.filter((file) => state.selectedFileIds.has(file.id));
        if (selected.length <= 2) {
            dom.selectedFilesText.textContent = selected.map((file) => file.name).join(", ");
        } else {
            dom.selectedFilesText.textContent = `${selected.length} files selected`;
        }
        dom.selectedFilesBar.classList.add("show");
    }

    if (!dom.filesSelectedBar || !dom.filesSelectedBarText) {
        return;
    }
    if (selectedCount) {
        dom.filesSelectedBar.classList.add("show");
        dom.filesSelectedBarText.textContent = `${selectedCount} selected`;
    } else {
        dom.filesSelectedBar.classList.remove("show");
        dom.filesSelectedBarText.textContent = "0 selected";
    }
}

function clearFileSelection() {
    state.selectedFileIds.clear();
    persistSelectedFiles();
    renderFilesList();
    updateSelectedFilesBar();
}

function handleFilesListClick(event) {
    const removeBtn = event.target.closest('[data-action="remove-file"]');
    const row = event.target.closest("[data-file-id]");
    if (!row) {
        return;
    }
    const fileId = row.dataset.fileId;
    if (!fileId) {
        return;
    }

    if (removeBtn) {
        event.stopPropagation();
        removeFile(fileId);
        return;
    }

    const file = state.files.find((entry) => entry.id === fileId);
    if (!file || file.status !== "ready") {
        return;
    }

    if (state.selectedFileIds.has(fileId)) {
        state.selectedFileIds.delete(fileId);
    } else {
        state.selectedFileIds.add(fileId);
    }
    persistSelectedFiles();
    renderFilesList();
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
    const allowedExts = new Set(["pdf", "docx", "doc", "xlsx", "xls", "csv", "txt"]);
    const valid = files.filter((file) => allowedExts.has(getExtension(file.name)));
    if (!valid.length) {
        return;
    }

    let processed = 0;
    const total = valid.length;
    const errors = [];

    setUploadProgress({
        visible: true,
        title: "Processing files...",
        text: `Starting ${total} file${total === 1 ? "" : "s"}...`,
        percent: 4,
    });

    await runWithConcurrency(valid, 2, async (file) => {
        try {
            setUploadProgress({
                visible: true,
                title: "Uploading and indexing...",
                text: file.name,
                percent: Math.max(8, Math.round((processed / total) * 100)),
            });
            await uploadSingleFile(file);
        } catch (error) {
            errors.push(`${file.name}: ${error.message}`);
        } finally {
            processed += 1;
            setUploadProgress({
                visible: true,
                title: "Processing files...",
                text: `${processed}/${total} completed`,
                percent: Math.round((processed / total) * 100),
            });
        }
    });

    await loadFiles();

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

function handleOneDriveListClick(event) {
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

function applyDarkModePreference() {
    const stored = localStorage.getItem("documind-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const useDark = stored ? stored === "dark" : prefersDark;

    document.documentElement.setAttribute("data-theme", useDark ? "dark" : "light");

    if (dom.darkModeToggle) {
        dom.darkModeToggle.innerHTML = useDark
            ? '<i class="fas fa-sun"></i>'
            : '<i class="fas fa-moon"></i>';
    }
}

function toggleDarkMode() {
    const current = document.documentElement.getAttribute("data-theme");
    const newTheme = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("documind-theme", newTheme);

    if (dom.darkModeToggle) {
        dom.darkModeToggle.innerHTML = newTheme === "dark"
            ? '<i class="fas fa-sun"></i>'
            : '<i class="fas fa-moon"></i>';
    }
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

    const allowedExts = new Set(["pdf", "docx", "doc", "xlsx", "xls", "csv", "txt"]);
    const valid = files.filter((file) => allowedExts.has(getExtension(file.name)));

    if (!valid.length) {
        showToast("Unsupported file type. Accepted: PDF, DOCX, XLSX, CSV, TXT", "error");
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
