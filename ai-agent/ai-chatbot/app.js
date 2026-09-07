const API_URL = "http://127.0.0.1:8000/api/chat";
const API_KEY = "E-Sahakara-Agent-2026";


// ============================================================
// SESSION
// ============================================================

let sessionId =
    sessionStorage.getItem("eshakara_ai_session");

if (!sessionId) {
    sessionId =
        "session-" +
        Date.now() +
        "-" +
        Math.random().toString(36).substring(2);

    sessionStorage.setItem(
        "eshakara_ai_session",
        sessionId
    );
}


// ============================================================
// ELEMENTS
// ============================================================

const aiButton = document.getElementById("aiButton");
const aiWindow = document.getElementById("aiWindow");
const closeAI = document.getElementById("closeAI");
const messages = document.getElementById("messages");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendAI = document.getElementById("sendAI");


// ============================================================
// SAFETY CHECK
// ============================================================

if (
    !aiButton ||
    !aiWindow ||
    !closeAI ||
    !messages ||
    !form ||
    !input
) {
    console.error(
        "E-Sahakara AI: required chatbot elements are missing."
    );
}


// ============================================================
function toggleAIChat(e) {
    if (e && e.stopPropagation) {
        e.stopPropagation();
    }
    const win = document.getElementById("aiWindow") || aiWindow;
    if (!win) return;

    const isVisible = (win.style.display === "flex") ||
                      win.classList.contains("open") ||
                      win.classList.contains("active");

    if (isVisible) {
        win.style.setProperty("display", "none", "important");
        win.classList.remove("open", "active");
    } else {
        win.style.setProperty("display", "flex", "important");
        win.classList.add("open", "active");
        const inp = document.getElementById("input") || input;
        if (inp) {
            setTimeout(function () {
                inp.focus();
            }, 60);
        }
    }
}

function closeAIChat(e) {
    if (e && e.stopPropagation) {
        e.stopPropagation();
    }
    const win = document.getElementById("aiWindow") || aiWindow;
    if (!win) return;
    win.style.setProperty("display", "none", "important");
    win.classList.remove("open", "active");
}

window.toggleAIChat = toggleAIChat;
window.closeAIChat = closeAIChat;

if (aiButton) {
    aiButton.onclick = toggleAIChat;
}

if (closeAI) {
    closeAI.onclick = closeAIChat;
}


// ============================================================
// FORMAT BOT MESSAGE (AWS AI AGENT CARD PARSER)
// ============================================================

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatBotMessage(text) {
    if (!text) return "";

    const escaped = escapeHtml(text);

    // Replace amounts like Rs. 100,000.00 or ₹100,000 with badge
    let formatted = escaped.replace(/(Rs\.?\s*[\d,]+(?:\.\d{2})?|₹\s*[\d,]+(?:\.\d{2})?)/g, '<span class="cbs-amount-badge">$1</span>');

    // Parse Summary block if present (e.g., Summary: ...)
    const summaryRegex = /(?:───+\s*)?(?:Summary|Note):\s*([^\n]+(?:\n[^\n]+)*)/i;
    const summaryMatch = formatted.match(summaryRegex);

    let summaryHtml = "";
    if (summaryMatch) {
        summaryHtml = `<div class="cbs-summary-box"><strong>Summary:</strong> ${summaryMatch[1].trim()}</div>`;
        formatted = formatted.replace(summaryMatch[0], "").trim();
    }

    // Split paragraphs
    const paragraphs = formatted.split(/\n\s*\n/);
    const resultParts = [];

    for (const para of paragraphs) {
        const trimmed = para.trim();
        if (!trimmed) continue;

        // Check if paragraph contains numbered scheme items (e.g. 1. Sahakara Fixed Deposit...)
        if (/^\d+\.\s+[^\n]+/m.test(trimmed)) {
            const lines = trimmed.split(/\n/);
            let inCard = false;
            let cardHtml = "";

            for (const line of lines) {
                const itemMatch = line.match(/^(\d+\.\s*)([^\n]+)/);
                if (itemMatch) {
                    if (inCard) {
                        cardHtml += '</div>';
                        resultParts.push(cardHtml);
                    }
                    inCard = true;
                    const isMember = /member/i.test(itemMatch[2]);
                    const icon = isMember ? "⚠️" : "🏦";
                    const cardClass = isMember ? "cbs-scheme-card cbs-invalid-card" : "cbs-scheme-card";
                    cardHtml = `<div class="${cardClass}"><div class="cbs-scheme-title"><span>${icon}</span> <span>${itemMatch[2]}</span></div>`;
                } else if (inCard) {
                    cardHtml += `<div class="cbs-scheme-detail">${line.trim()}</div>`;
                } else {
                    resultParts.push(`<p>${line}</p>`);
                }
            }
            if (inCard) {
                cardHtml += '</div>';
                resultParts.push(cardHtml);
            }
        } else {
            // Normal paragraph with newline conversion
            resultParts.push(`<p>${trimmed.replace(/\n/g, '<br>')}</p>`);
        }
    }

    if (summaryHtml) {
        resultParts.push(summaryHtml);
    }

    return resultParts.join("");
}

// ============================================================
// ADD MESSAGE
// ============================================================

function getCurrentTimeStr() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function addMessage(text, sender = "bot") {
    if (!messages) return;

    const group = document.createElement("div");
    group.className = sender === "user" ? "msg-group user-group" : "msg-group bot-group";

    // Avatar
    const avatar = document.createElement("div");
    avatar.className = sender === "user" ? "msg-avatar user-avatar" : "msg-avatar bot-avatar";
    if (sender === "user") {
        avatar.textContent = "👤";
    } else {
        avatar.innerHTML = '<img src="assets/logo.png" alt="" width="28" height="28">';
    }
    group.appendChild(avatar);

    // Message card
    const msg = document.createElement("div");
    msg.className = sender === "user" ? "msg user" : "msg bot";

    // Metadata
    const meta = document.createElement("div");
    meta.className = "msg-meta";
    if (sender === "bot") {
        meta.innerHTML = `<span class="agent-name">E-Sahakara Agent</span> <span class="agent-tag">AI Core</span> <span style="font-size:10px; color:#94a3b8; margin-left:auto;">${getCurrentTimeStr()}</span>`;
    } else {
        meta.innerHTML = `<span class="agent-name" style="color:rgba(255,255,255,0.7)">You</span> <span style="font-size:10px; color:rgba(255,255,255,0.5); margin-left:auto;">${getCurrentTimeStr()}</span>`;
    }
    msg.appendChild(meta);

    // Content
    const content = document.createElement("div");
    content.className = "msg-content";

    if (sender === "bot") {
        content.innerHTML = formatBotMessage(text);
    } else {
        const p = document.createElement("p");
        p.textContent = text;
        content.appendChild(p);
    }
    msg.appendChild(content);

    // Bot message action bar (Copy button + feedback)
    if (sender === "bot") {
        const actions = document.createElement("div");
        actions.className = "msg-actions";

        const copyBtn = document.createElement("button");
        copyBtn.type = "button";
        copyBtn.className = "btn-msg-action";
        copyBtn.title = "Copy response";
        copyBtn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span>Copy</span>
        `;
        copyBtn.onclick = function () {
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.innerHTML = `<span>✓ Copied</span>`;
                copyBtn.style.color = "#16a34a";
                setTimeout(() => {
                    copyBtn.innerHTML = `
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                        <span>Copy</span>
                    `;
                    copyBtn.style.color = "";
                }, 2000);
            }).catch(() => {});
        };

        actions.appendChild(copyBtn);
        msg.appendChild(actions);
    }

    group.appendChild(msg);
    messages.appendChild(group);

    messages.scrollTop = messages.scrollHeight;
}

// ============================================================
// TYPING INDICATOR (AWS AI THINKING DOTS)
// ============================================================

function showTyping() {
    if (!messages) return;

    const group = document.createElement("div");
    group.id = "aiTyping";
    group.className = "msg-group bot-group";

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar bot-avatar";
    avatar.innerHTML = '<img src="assets/logo.png" alt="" width="28" height="28">';
    group.appendChild(avatar);

    const msg = document.createElement("div");
    msg.className = "msg bot";

    const wrap = document.createElement("div");
    wrap.className = "typing-wrap";
    wrap.innerHTML = `
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <span class="typing-label">Querying CBS core database...</span>
    `;

    msg.appendChild(wrap);
    group.appendChild(msg);
    messages.appendChild(group);

    messages.scrollTop = messages.scrollHeight;
}

function removeTyping() {
    const typing = document.getElementById("aiTyping");
    if (typing) {
        typing.remove();
    }
}

// ============================================================
// SEND MESSAGE
// ============================================================

async function sendMessage(overrideText = null) {
    const raw = overrideText !== null ? overrideText : input.value;
    const message = (raw || "").trim();

    if (!message) {
        return;
    }

    addMessage(message, "user");

    input.value = "";
    input.style.height = "auto";
    input.disabled = true;

    if (sendAI) {
        sendAI.disabled = true;
    }

    showTyping();

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Agent-Key": API_KEY,
                "X-Session-ID": sessionId
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });

        removeTyping();

        if (!response.ok) {
            let errorText = `Server error (${response.status})`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorText = errorData.detail;
                }
            } catch (_) {}

            addMessage(errorText, "bot");
            return;
        }

        const data = await response.json();

        if (data.session_id) {
            sessionId = data.session_id;
            sessionStorage.setItem("eshakara_ai_session", sessionId);
        }

        addMessage(
            data.answer || "I could not generate a response from the CBS database.",
            "bot"
        );

    } catch (error) {
        console.error("E-Sahakara AI error:", error);
        removeTyping();
        addMessage(
            "Could not connect to the local AI backend service on 127.0.0.1:8000. Please verify the backend is running.",
            "bot"
        );
    } finally {
        input.disabled = false;
        if (sendAI) {
            sendAI.disabled = false;
        }
        input.focus();
    }
}

// ============================================================
// QUICK PROMPT CHIPS (AWS AI AGENT)
// ============================================================

function initPromptChips() {
    const chips = document.querySelectorAll(".prompt-chip");
    chips.forEach((chip) => {
        chip.addEventListener("click", function () {
            const promptText = this.getAttribute("data-prompt") || this.textContent.trim();
            if (promptText) {
                sendMessage(promptText);
            }
        });
    });
}

// ============================================================
// CLEAR CHAT BUTTON
// ============================================================

const clearBtn = document.getElementById("clearChat");
if (clearBtn) {
    clearBtn.addEventListener("click", function () {
        if (!messages) return;
        messages.innerHTML = `
            <div class="msg-group bot-group">
                <div class="msg-avatar bot-avatar"><img src="assets/logo.png" alt="" width="28" height="28"></div>
                <div class="msg bot">
                    <div class="msg-meta">
                        <span class="agent-name">E-Sahakara Agent</span>
                        <span class="agent-tag">Assistant</span>
                    </div>
                    <div class="msg-content">
                        <p>Chat cleared. Ready for your CBS inquiries about schemes, accounts, and transactions.</p>
                    </div>
                </div>
            </div>
        `;
    });
}

// ============================================================
// FORM SUBMIT & AUTO-EXPAND INPUT
// ============================================================

if (form) {
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        sendMessage();
    });
}

if (input) {
    input.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    // Auto-expand textarea up to 110px
    input.addEventListener("input", function () {
        this.style.height = "auto";
        this.style.height = Math.min(this.scrollHeight, 110) + "px";
    });
}

// Initialize chips on load
initPromptChips();

console.log("E-Sahakara AWS AI Agent frontend loaded successfully.");