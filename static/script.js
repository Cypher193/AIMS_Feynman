// --- Constants and Chat State ---
let sessionId = "";
try {
    sessionId = localStorage.getItem("feynman_session_id");
} catch (e) {
    console.warn("localStorage is not accessible:", e);
}

if (!sessionId) {
    sessionId = "feynman_session_" + Math.random().toString(36).substring(2, 11);
    try {
        localStorage.setItem("feynman_session_id", sessionId);
    } catch (e) {
        console.warn("localStorage is not accessible:", e);
    }
}

const API_HEADERS = { "Content-Type": "application/json" };

// DOM Element References (Initialized on DOMContentLoaded)
let messagesContainer = null;
let chatForm = null;
let userInput = null;
let sessionLabel = null;
let newTopicBtn = null;
let topicsList = null;
let quickPromptBtns = [];
let openMemoryBtn = null;
let closeMemoryBtn = null;
let memoryModal = null;
let memoryCanvas = null;
let memoryCtx = null;
let isMemoryModalOpen = false;

// Physics Graph State
let graphNodes = [];
let graphLinks = [];
let selectedNode = null;
let hoveredNode = null;
let draggedNode = null;
let simulationId = null;

// --- Bongo Audio Stub (preserves safe chat triggers) ---
function playBongoSound(pitchType) {}

// --- Simple Markdown Compiler ---
function compileMarkdown(text) {
    if (!text) return "";
    
    // Escape HTML tags to prevent injections
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Code Blocks (```javascript ... ```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang || 'txt'}">${code.trim()}</code></pre>`;
    });

    // Inline Code (`code`)
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Strong/Bold (**text**)
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italics (*text*)
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Split paragraphs by double newlines
    const paragraphs = html.split(/\n\n+/);
    return paragraphs
        .map(p => {
            if (p.startsWith("<pre>")) return p; // Don't wrap code blocks in paragraphs
            return `<p>${p.replace(/\n/g, "<br>")}</p>`;
        })
        .join("");
}

// --- DOM Interactions & Dynamic Chat Rendering ---

function scrollToBottom() {
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Render dynamic chat bubbles
function appendMessage(sender, text, timestampStr = "Just now") {
    if (!messagesContainer) return;
    
    const isFeynman = sender === "feynman";
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${isFeynman ? 'feynman-message' : 'user-message'} slide-up`;
    
    const formattedContent = compileMarkdown(text);
    const avatarUrl = isFeynman ? "/static/images/feynman_avatar.png" : "https://api.dicebear.com/7.x/identicon/svg?seed=" + sessionId;

    msgDiv.innerHTML = `
        <div class="message-avatar">
            <img src="${avatarUrl}" alt="${sender} Avatar">
        </div>
        <div class="message-content glass">
            <div class="message-bubble-header">${isFeynman ? 'Dr. Richard Feynman' : 'You'}</div>
            <div class="message-text">${formattedContent}</div>
            <div class="message-time">${timestampStr}</div>
        </div>
    `;

    messagesContainer.appendChild(msgDiv);
    scrollToBottom();

    // Trigger MathJax rendering for the new message if loaded
    if (window.MathJax && typeof MathJax.typesetPromise === "function") {
        MathJax.typesetPromise([msgDiv]).catch((err) => console.warn("MathJax typeset error:", err));
    }
}

// Append Typing indicator
let typingIndicator = null;
function showTypingIndicator() {
    if (typingIndicator || !messagesContainer) return;
    
    typingIndicator = document.createElement("div");
    typingIndicator.className = "message feynman-message slide-up";
    typingIndicator.id = "typingIndicator";
    typingIndicator.innerHTML = `
        <div class="message-avatar">
            <img src="/static/images/feynman_avatar.png" alt="Feynman Avatar">
        </div>
        <div class="message-content glass">
            <div class="message-bubble-header">Dr. Richard Feynman</div>
            <div class="typing-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(typingIndicator);
    scrollToBottom();
}

function removeTypingIndicator() {
    if (typingIndicator) {
        typingIndicator.remove();
        typingIndicator = null;
    }
}

// Load Chat History from SQLite database
async function loadChatHistory() {
    if (!messagesContainer) return;
    try {
        const response = await fetch(`/api/history/${sessionId}`);
        if (!response.ok) throw new Error("Could not fetch history");
        
        const data = await response.json();
        
        // Reset container to greeting or list
        messagesContainer.innerHTML = "";
        
        // If we have messages, append them
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                const sender = msg.type === "human" ? "user" : "feynman";
                appendMessage(sender, msg.content, "Saved Dialogue");
            });
        } else {
            // Display default greeting
            messagesContainer.innerHTML = `
                <div class="message feynman-message slide-up">
                    <div class="message-avatar">
                        <img src="/static/images/feynman_avatar.png" alt="Feynman Avatar">
                    </div>
                    <div class="message-content glass">
                        <div class="message-bubble-header">Dr. Richard Feynman</div>
                        <p>Hello there! I'm Richard Feynman, and I find nature to be the most exciting, beautiful, and utterly bizarre thing in the universe.</p>
                        <p>You can ask me about physics, electrical engineering, AI architectures, my safe-cracking adventures, or why the color of the sunset is a beautiful trick of nature. Treat me as a peer—let's figure it out together!</p>
                        <div class="message-time">Just now</div>
                    </div>
                </div>
            `;
        }
    } catch (err) {
        console.warn("Failed to load chat history:", err);
    }
}

// Load Dialogue Topics (Sessions) from Backend
async function loadSessions() {
    if (!topicsList) return;
    try {
        const response = await fetch("/api/sessions");
        if (!response.ok) throw new Error("Could not fetch sessions");
        
        const data = await response.json();
        topicsList.innerHTML = "";
        
        if (data.sessions && data.sessions.length > 0) {
            data.sessions.forEach(sess => {
                const isActive = sess.session_id === sessionId;
                const card = document.createElement("div");
                card.className = `topic-card ${isActive ? 'active-topic' : ''}`;
                card.setAttribute("data-id", sess.session_id);
                
                card.innerHTML = `
                    <div class="topic-card-content">
                        <i class="fa-solid fa-message"></i>
                        <span>${sess.title || 'New Topic'}</span>
                    </div>
                    <button class="delete-topic-btn" title="Delete Topic">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                `;
                
                // Clicking card switches session
                card.addEventListener("click", (e) => {
                    // Prevent triggering if clicked on the delete button
                    if (e.target.closest(".delete-topic-btn")) return;
                    switchSession(sess.session_id);
                });
                
                // Clicking delete removes session
                const delBtn = card.querySelector(".delete-topic-btn");
                if (delBtn) {
                    delBtn.addEventListener("click", (e) => {
                        e.stopPropagation();
                        deleteSession(sess.session_id);
                    });
                }
                
                topicsList.appendChild(card);
            });
        } else {
            topicsList.innerHTML = `
                <div style="font-size: 0.75rem; color: var(--text-muted); text-align: center; padding: 1rem 0;">
                    No previous dialogues
                </div>
            `;
        }
    } catch (err) {
        console.warn("Failed to load sessions:", err);
    }
}

// Switch Active Conversational Session
async function switchSession(targetSid) {
    sessionId = targetSid;
    try {
        localStorage.setItem("feynman_session_id", targetSid);
    } catch (e) {
        console.warn("localStorage is not accessible:", e);
    }
    if (sessionLabel) {
        sessionLabel.textContent = `Session: ${targetSid.substring(16, 22).toUpperCase()}`;
    }
    
    // Load history and re-render topics to highlight active
    await loadChatHistory();
    await loadSessions();
}

// Delete Session from Backend SQL db
async function deleteSession(targetSid) {
    if (!confirm("Are you sure you want to permanently delete this dialogue and clear its memory?")) return;
    
    try {
        const response = await fetch(`/api/sessions/${targetSid}`, {
            method: "DELETE"
        });
        
        if (!response.ok) throw new Error("Could not delete session");
        
        // If we deleted the currently active session, start a new fresh one
        if (targetSid === sessionId) {
            sessionId = "feynman_session_" + Math.random().toString(36).substring(2, 11);
            try {
                localStorage.setItem("feynman_session_id", sessionId);
            } catch (e) {
                console.warn("localStorage is not accessible:", e);
            }
            if (sessionLabel) {
                sessionLabel.textContent = `Session: ${sessionId.substring(16, 22).toUpperCase()}`;
            }
            await loadChatHistory();
        }
        
        await loadSessions();
    } catch (err) {
        console.error("Delete Error:", err);
        alert("Failed to delete dialogue: " + err.message);
    }
}

// Send Chat Message
async function sendChatMessage(message) {
    if (!message || !message.trim()) return;

    // Check if this is the first message in the session
    const isFirstMessage = messagesContainer ? messagesContainer.querySelectorAll(".message").length <= 1 : true;

    // Append user bubble
    appendMessage("user", message);
    if (userInput) {
        userInput.value = "";
        userInput.style.height = "auto"; // Reset height
    }

    // Show Feynman thinking indicator
    showTypingIndicator();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: API_HEADERS,
            body: JSON.stringify({ message: message, session_id: sessionId })
        });

        removeTypingIndicator();

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Server Error");
        }

        const data = await response.json();
        playBongoSound('high');
        appendMessage("feynman", data.answer);
        
        // If it was the first message, refresh topics list so the new session immediately displays in the sidebar
        if (isFirstMessage) {
            loadSessions();
        }
    } catch (err) {
        removeTypingIndicator();
        appendMessage("feynman", `*Ouch! Seems my digital quantum gears got a little stuck here. Let's try that again. Error details: ${err.message}*`);
        console.error("Chat Error:", err);
    }
}

// --- HTML5 Canvas Physics-Inspired Particle/Wave Background ---
function initQuantumCanvas() {
    const canvas = document.getElementById("quantumCanvas");
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener("resize", () => {
        width = (canvas.width = window.innerWidth);
        height = (canvas.height = window.innerHeight);
    });

    // Capture mouse movements
    const mouse = { x: width / 2, y: height / 2, active: false };
    window.addEventListener("mousemove", (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
        mouse.active = true;
    });

    // Particles tracking Quantum Chalk Dust (Scholarly organic drift)
    const particles = [];
    const particleCount = 35;

    class QuantumParticle {
        constructor() {
            this.reset();
        }

        reset() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.size = Math.random() * 1.2 + 0.4;
            this.speedX = Math.random() * 0.15 - 0.075;
            this.speedY = Math.random() * 0.15 - 0.075;
            this.opacity = Math.random() * 0.25 + 0.05;
            this.amplitude = Math.random() * 5 + 2;
            this.frequency = Math.random() * 0.01 + 0.002;
            this.phase = Math.random() * Math.PI * 2;
            this.baseY = this.y;
        }

        update() {
            this.x += this.speedX;
            
            // Faint drifting wave motion
            this.phase += this.frequency;
            this.y = this.baseY + Math.sin(this.phase) * this.amplitude;

            // Attract lightly to mouse (Observation effect!)
            if (mouse.active) {
                const dx = mouse.x - this.x;
                const dy = mouse.y - this.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 150) {
                    this.x += dx * 0.002;
                    this.y += dy * 0.002;
                    this.baseY += dy * 0.002;
                }
            }

            // Boundary wrapping
            if (this.x < 0) this.x = width;
            if (this.x > width) this.x = 0;
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(142, 202, 230, ${this.opacity})`;
            ctx.fill();
        }
    }

    // Instantiate particles
    for (let i = 0; i < particleCount; i++) {
        particles.push(new QuantumParticle());
    }

    // Canvas animation loop
    function animateCanvas() {
        ctx.clearRect(0, 0, width, height);
        
        // Draw chalk dust particles
        particles.forEach((p) => {
            p.update();
            p.draw();
        });

        requestAnimationFrame(animateCanvas);
    }
    animateCanvas();
}

// --- App Initialization Function ---
function initApp() {
    // Resolve all DOM references
    messagesContainer = document.getElementById("messagesContainer");
    chatForm = document.getElementById("chatForm");
    userInput = document.getElementById("userInput");
    sessionLabel = document.getElementById("sessionLabel");
    newTopicBtn = document.getElementById("newTopicBtn");
    topicsList = document.getElementById("topicsList");
    quickPromptBtns = document.querySelectorAll(".prompt-btn");
    openMemoryBtn = document.getElementById("openMemoryBtn");
    closeMemoryBtn = document.getElementById("closeMemoryBtn");
    memoryModal = document.getElementById("memoryModal");
    memoryCanvas = document.getElementById("memoryCanvas");
    
    if (memoryCanvas) {
        memoryCtx = memoryCanvas.getContext("2d");
    }

    if (sessionLabel) {
        sessionLabel.textContent = `Session: ${sessionId.substring(16, 22).toUpperCase()}`;
    }

    // Textarea auto-expanding effect
    if (userInput) {
        userInput.addEventListener("input", function() {
            this.style.height = "auto";
            this.style.height = (this.scrollHeight) + "px";
        });

        // Textarea Submit key handler (Enter sends, Shift+Enter newlines)
        userInput.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const msg = userInput.value.trim();
                sendChatMessage(msg);
            }
        });
    }

    // Chat form submission
    if (chatForm) {
        chatForm.addEventListener("submit", function(e) {
            e.preventDefault();
            if (userInput) {
                const msg = userInput.value.trim();
                sendChatMessage(msg);
            }
        });
    }

    // Sidebar Quick Prompt buttons
    if (quickPromptBtns) {
        quickPromptBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                const promptText = btn.getAttribute("data-prompt");
                sendChatMessage(promptText);
            });
        });
    }

    // Sidebar "+ New Topic" button
    if (newTopicBtn) {
        newTopicBtn.addEventListener("click", () => {
            // Generate new isolated session id
            sessionId = "feynman_session_" + Math.random().toString(36).substring(2, 11);
            try {
                localStorage.setItem("feynman_session_id", sessionId);
            } catch (e) {
                console.warn("localStorage is not accessible:", e);
            }
            if (sessionLabel) {
                sessionLabel.textContent = `Session: ${sessionId.substring(16, 22).toUpperCase()}`;
            }
            
            // Clear screen and load fresh greeting
            loadChatHistory();
            loadSessions();
        });
    }

    // Memory Matrix Button triggers
    if (openMemoryBtn) {
        openMemoryBtn.addEventListener("click", openMemoryMatrix);
    }
    if (closeMemoryBtn) {
        closeMemoryBtn.addEventListener("click", closeMemoryMatrix);
    }
    if (memoryModal) {
        memoryModal.addEventListener("click", (e) => {
            if (e.target === memoryModal) closeMemoryMatrix();
        });
    }

    window.addEventListener("resize", () => {
        if (isMemoryModalOpen) resizeMemoryCanvas();
    });

    // Start background canvas
    initQuantumCanvas();

    // Load initial messages and sessions
    loadChatHistory();
    loadSessions();
}

// --- Quantum Memory Matrix Logic & Physics Engine ---

async function openMemoryMatrix() {
    if (!memoryModal) return;
    memoryModal.style.display = "flex";
    isMemoryModalOpen = true;
    
    // Clear details
    const detailContainer = document.getElementById("conceptDetailContainer");
    if (detailContainer) {
        detailContainer.innerHTML = `<div class="placeholder-text">Click a concept node in the network to inspect memory snippets and recall the dialogue.</div>`;
    }
    
    try {
        const response = await fetch(`/api/memory-matrix/${sessionId}`);
        if (!response.ok) throw new Error("Could not fetch memory matrix");
        const data = await response.json();
        
        renderMilestones(data.milestones || []);
        setupGraphPhysics(data.nodes || [], data.links || []);
    } catch (e) {
        console.error("Error loading memory matrix:", e);
    }
}

function closeMemoryMatrix() {
    if (!memoryModal) return;
    memoryModal.style.display = "none";
    isMemoryModalOpen = false;
    
    if (simulationId) {
        cancelAnimationFrame(simulationId);
        simulationId = null;
    }
}

function renderMilestones(milestones) {
    const timeline = document.getElementById("milestonesTimeline");
    if (!timeline) return;
    timeline.innerHTML = "";
    
    if (milestones.length === 0) {
        timeline.innerHTML = `<div class="placeholder-text">Start discussing topics to map milestones.</div>`;
        return;
    }
    
    milestones.forEach(m => {
        const item = document.createElement("div");
        item.className = "milestone-item";
        item.innerHTML = `
            <div class="milestone-dot"></div>
            <div class="milestone-time">${m.timestamp}</div>
            <div class="milestone-title">${m.concept}</div>
            <div class="milestone-desc">${m.text}</div>
        `;
        timeline.appendChild(item);
    });
}

function setupGraphPhysics(nodes, links) {
    if (!memoryCanvas) return;
    
    if (simulationId) cancelAnimationFrame(simulationId);
    
    resizeMemoryCanvas();
    
    const width = memoryCanvas.width;
    const height = memoryCanvas.height;
    
    graphNodes = nodes.map((n, i) => {
        const angle = (i / nodes.length) * Math.PI * 2;
        const radius = Math.min(width, height) * 0.22;
        return {
            ...n,
            x: width / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 20,
            y: height / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 20,
            vx: 0,
            vy: 0,
            radius: Math.max(12, Math.min(32, 12 + (n.weight * 3)))
        };
    });
    
    graphLinks = links.map(l => {
        const sourceNode = graphNodes.find(n => n.id === l.source);
        const targetNode = graphNodes.find(n => n.id === l.target);
        return {
            ...l,
            sourceNode,
            targetNode,
            pulses: [0.0, 0.33, 0.66]
        };
    }).filter(l => l.sourceNode && l.targetNode);
    
    memoryCanvas.onmousedown = onCanvasMouseDown;
    memoryCanvas.onmousemove = onCanvasMouseMove;
    window.onmouseup = onCanvasMouseUp;
    
    selectedNode = null;
    hoveredNode = null;
    draggedNode = null;
    simulationId = requestAnimationFrame(updateGraphPhysics);
}

function resizeMemoryCanvas() {
    if (!memoryCanvas) return;
    const rect = memoryCanvas.parentNode.getBoundingClientRect();
    memoryCanvas.width = rect.width || 600;
    memoryCanvas.height = rect.height || 500;
}

function updateGraphPhysics() {
    if (!isMemoryModalOpen || !memoryCtx) return;
    
    const width = memoryCanvas.width;
    const height = memoryCanvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    
    // Repulsion
    const kRepulsion = 1600;
    for (let i = 0; i < graphNodes.length; i++) {
        const n1 = graphNodes[i];
        for (let j = i + 1; j < graphNodes.length; j++) {
            const n2 = graphNodes[j];
            const dx = n2.x - n1.x;
            const dy = n2.y - n1.y;
            const distSq = dx * dx + dy * dy + 0.1;
            const dist = Math.sqrt(distSq);
            
            const minAllowedDist = n1.radius + n2.radius + 35;
            let force = kRepulsion / distSq;
            if (dist < minAllowedDist) {
                force = (kRepulsion * 2.5) / distSq;
            }
            
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (n1 !== draggedNode) { n1.vx -= fx; n1.vy -= fy; }
            if (n2 !== draggedNode) { n2.vx += fx; n2.vy += fy; }
        }
    }
    
    // Attraction
    const kAttraction = 0.04;
    const restLength = 100;
    graphLinks.forEach(l => {
        const n1 = l.sourceNode;
        const n2 = l.targetNode;
        const dx = n2.x - n1.x;
        const dy = n2.y - n1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
        const displacement = dist - restLength;
        const force = kAttraction * displacement;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        
        if (n1 !== draggedNode) { n1.vx += fx; n1.vy += fy; }
        if (n2 !== draggedNode) { n2.vx -= fx; n2.vy -= fy; }
    });
    
    // Gravity and Friction
    const kGravity = 0.015;
    graphNodes.forEach(n => {
        if (n === draggedNode) return;
        
        n.vx += (centerX - n.x) * kGravity;
        n.vy += (centerY - n.y) * kGravity;
        
        n.vx *= 0.8;
        n.vy *= 0.8;
        
        n.x += n.vx;
        n.y += n.vy;
        
        const pad = n.radius + 10;
        if (n.x < pad) n.x = pad;
        if (n.x > width - pad) n.x = width - pad;
        if (n.y < pad) n.y = pad;
        if (n.y > height - pad) n.y = height - pad;
    });
    
    drawGraph(width, height);
    
    simulationId = requestAnimationFrame(updateGraphPhysics);
}

function drawGraph(width, height) {
    memoryCtx.clearRect(0, 0, width, height);
    
    // Links & pulses
    graphLinks.forEach(l => {
        const isSelectedLink = selectedNode && (l.sourceNode === selectedNode || l.targetNode === selectedNode);
        
        memoryCtx.beginPath();
        memoryCtx.moveTo(l.sourceNode.x, l.sourceNode.y);
        memoryCtx.lineTo(l.targetNode.x, l.targetNode.y);
        
        if (isSelectedLink) {
            memoryCtx.strokeStyle = "rgba(255, 183, 3, 0.45)";
            memoryCtx.lineWidth = 2.0;
        } else {
            memoryCtx.strokeStyle = "rgba(33, 158, 188, 0.18)";
            memoryCtx.lineWidth = 1.25;
        }
        memoryCtx.stroke();
        
        l.pulses.forEach((p, idx) => {
            l.pulses[idx] = (p + 0.005) % 1.0;
            const px = l.sourceNode.x + (l.targetNode.x - l.sourceNode.x) * l.pulses[idx];
            const py = l.sourceNode.y + (l.targetNode.y - l.sourceNode.y) * l.pulses[idx];
            
            memoryCtx.beginPath();
            memoryCtx.arc(px, py, 2.5, 0, Math.PI * 2);
            memoryCtx.fillStyle = isSelectedLink ? "rgba(255, 183, 3, 0.85)" : "rgba(142, 202, 230, 0.65)";
            memoryCtx.fill();
        });
    });
    
    // Nodes
    graphNodes.forEach(n => {
        const isSelected = selectedNode === n;
        const isHovered = hoveredNode === n;
        
        if (isSelected || isHovered) {
            const glowSize = n.radius * 1.5;
            const grad = memoryCtx.createRadialGradient(n.x, n.y, n.radius * 0.7, n.x, n.y, glowSize);
            const colorGlow = isSelected ? "rgba(255, 183, 3, 0.2)" : "rgba(33, 158, 188, 0.15)";
            grad.addColorStop(0, colorGlow);
            grad.addColorStop(1, "rgba(2, 48, 71, 0)");
            
            memoryCtx.beginPath();
            memoryCtx.arc(n.x, n.y, glowSize, 0, Math.PI * 2);
            memoryCtx.fillStyle = grad;
            memoryCtx.fill();
        }
        
        memoryCtx.beginPath();
        memoryCtx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        
        let nodeColor = "rgba(33, 158, 188, 0.7)";
        let nodeBorderColor = "#219ebc";
        
        if (n.category === "dynamic") {
            nodeColor = "rgba(142, 202, 230, 0.75)";
            nodeBorderColor = "#8ecae6";
        } else if (n.category === "persona") {
            nodeColor = "rgba(255, 183, 3, 0.8)";
            nodeBorderColor = "#ffb703";
        }
        
        if (isSelected) {
            nodeBorderColor = "#ffb703";
        }
        
        memoryCtx.fillStyle = nodeColor;
        memoryCtx.fill();
        
        memoryCtx.strokeStyle = nodeBorderColor;
        memoryCtx.lineWidth = isSelected ? 3.0 : 1.5;
        memoryCtx.stroke();
        
        memoryCtx.font = `bold ${n.radius * 0.45 + 5}px Outfit, sans-serif`;
        memoryCtx.textAlign = "center";
        memoryCtx.textBaseline = "middle";
        
        memoryCtx.fillStyle = "rgba(2, 48, 71, 0.9)";
        memoryCtx.fillText(n.label, n.x + 1, n.y + 1);
        
        memoryCtx.fillStyle = isSelected ? "#ffb703" : "#ffffff";
        memoryCtx.fillText(n.label, n.x, n.y);
    });
}

function onCanvasMouseDown(e) {
    const rect = memoryCanvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    let clickedNode = null;
    for (let i = graphNodes.length - 1; i >= 0; i--) {
        const n = graphNodes[i];
        const dx = n.x - mouseX;
        const dy = n.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= n.radius) {
            clickedNode = n;
            break;
        }
    }
    
    if (clickedNode) {
        draggedNode = clickedNode;
        selectedNode = clickedNode;
        selectConceptNode(clickedNode);
    } else {
        selectedNode = null;
    }
}

function onCanvasMouseMove(e) {
    const rect = memoryCanvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    if (draggedNode) {
        draggedNode.x = mouseX;
        draggedNode.y = mouseY;
        draggedNode.vx = 0;
        draggedNode.vy = 0;
        return;
    }
    
    let foundHover = null;
    for (let i = graphNodes.length - 1; i >= 0; i--) {
        const n = graphNodes[i];
        const dx = n.x - mouseX;
        const dy = n.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= n.radius) {
            foundHover = n;
            break;
        }
    }
    
    hoveredNode = foundHover;
    memoryCanvas.style.cursor = foundHover ? "pointer" : "grab";
}

function onCanvasMouseUp(e) {
    draggedNode = null;
}

function selectConceptNode(node) {
    const detailContainer = document.getElementById("conceptDetailContainer");
    if (!detailContainer) return;
    
    detailContainer.innerHTML = "";
    
    const snippets = node.snippets || [];
    if (snippets.length === 0) {
        detailContainer.innerHTML = `<div class="placeholder-text">This concept is active in your dialogue matrix, but no direct quotes are stored yet. Prompt Feynman on it!</div>`;
        return;
    }
    
    snippets.forEach(s => {
        const bubble = document.createElement("div");
        bubble.className = `recall-bubble ${s.sender === 'human' ? 'human' : 'feynman'}`;
        bubble.innerHTML = `
            <div class="recall-sender">${s.sender === 'human' ? 'You Asked' : 'Dr. Feynman Recalled'}</div>
            <div class="recall-text">${compileMarkdown(s.text)}</div>
        `;
        detailContainer.appendChild(bubble);
    });
}

// --- Page Initialization Handler ---
if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}
