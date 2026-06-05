# System Design & Architecture Documentation: Dr. Richard Feynman Digital Twin

This document outlines the technical approach, architectural layout, and critical design decisions made during the development of the RAG-backed digital twin of Nobel laureate physicist Dr. Richard Feynman.

---

## 1. Project Goal & Overview
The objective is to construct an immersive, interactive web application acting as a digital twin of Richard Feynman. It serves as an educational companion for university students tackling advanced concepts in physics, mathematics, electrical engineering, and computing. 

Rather than a generic assistant, the agent is designed to embody Feynman's signature voice, pedagogical style (the "Feynman Technique"), intellectual honesty, safe-cracking humor, and infectious curiosity.

---

## 2. Technical Stack
The application is designed to be lightweight, zero-dependency on the frontend, fast, and robust:
*   **Frontend UI:** Vanilla HTML5, CSS3, and JavaScript. 
    *   *Typography:* Google Fonts "Outfit" (geometric sans-serif) and "JetBrains Mono" (code blocks).
    *   *Icons:* FontAwesome v6.
    *   *Math Typesetting:* MathJax v3 CDN with dynamic typeset triggers.
*   **Backend Server:** FastAPI (Python 3.11/3.12) running under Uvicorn.
*   **AI & RAG Pipeline:** LangChain (combining retrieval chains with SQL database persistence) and Google Gemini API (`gemini-2.5-flash` LLM, `text-embedding-004` embedding model).
*   **Database & Persistence:** SQLite for local stateful dialogue memory and Chroma DB as the dense vector index.

---

## 3. Architecture & Data Flow

```mermaid
graph TD
    User([User Browser]) -->|User Prompt / Click| UI[Holographic UI HTML/JS/CSS]
    UI -->|API POST /api/chat| Server[FastAPI Web Server]
    Server -->|Retrieval Query| Hybrid[Hybrid Ensemble Retriever]
    Hybrid -->|70% Weight Dense| Chroma[Chroma DB Vectorstore]
    Hybrid -->|30% Weight Sparse| BM25[BM25 Retriever]
    Chroma -->|Dense Chunks| RRF[Reciprocal Rank Fusion]
    BM25 -->|Sparse Chunks| RRF
    RRF -->|Ranked Chunks| LLM[Gemini 2.5 LLM Chain]
    Server -->|Persist Turn| SQLite[(SQLite message_store)]
    LLM -->|Feynman Response| Server
    Server -->|JSON Answer| UI
    UI -->|Typeset| MathJax[MathJax Typesetting]
    UI -->|Render Graph| Physics[Canvas Force Graph Engine]
    Physics -->|Fetch Memory| Server
```

---

## 4. Key Design Decisions

### A. RAG Hybrid Retrieval Strategy
To deliver grounding in Feynman's actual publications, lectures, and transcripts, we implemented a hybrid RAG retrieval pipeline:
1.  **Dense Retrieval (70%):** Chroma vector store queries are processed using Google embeddings (`text-embedding-004`). This captures semantic meanings, synonyms, and conceptual relationships.
2.  **Sparse Retrieval (30%):** `BM25Retriever` performs keyword frequency matching. This ensures that exact mathematical equations, physics symbols, proper names, and literal terms are retrieved accurately.
3.  **Fusion:** The retrievers are fused using LangChain's `EnsembleRetriever` which balances semantic mapping and strict term matching. This mitigates hallucination and ensures responses are deeply grounded in real lecture transcripts.

### B. Local NLP Memory Extractor
Instead of invoking the LLM to summarize or classify user memories (which incurs token fees, latency, and rate limits), we implemented `MemoryExtractor` inside `memory_extractor.py`:
*   **Heuristics Matcher:** Matches text against pre-defined regexes covering core Feynman topics (e.g. QED, nanotech, safecracking).
*   **Named Entity Discoverer:** Dynamically extracts multi-word capitalized phrases (excluding common sentence starters) to harvest proper noun concepts like "Los Alamos" or "Dirac Equation".
*   **Linking:** Connects concepts discussed in the same conversational exchange to draw semantic threads.
*   **Milestones:** Traces the first time a concept is introduced to build an educational timeline of their study path.

### C. Custom Force-Directed Graph Engine
To provide a premium visualization of long-term memory:
*   Built a custom, zero-dependency physics loop inside `script.js` running on an HTML5 `<canvas>`.
*   **Coulomb's Repulsion:** $F_r = \frac{k_r}{d^2}$ pushes nodes apart.
*   **Hooke's Spring Tension:** $F_a = k_a \cdot (d - d_0)$ pulls linked concepts together.
*   **Damping & Friction:** Velocity multiplier of $0.8$ ensures physics simulations converge quickly to stable layouts.
*   **Memory Pulses:** Draws glowing particle nodes drifting continuously along connection lines, symbolizing active neural signals.
*   **Recall Connection:** Clicking a node queries the local extraction database, opening a "Recall Chamber" of past dialog bubbles matching the concept.

### D. MathJax LaTeX Typesetting
To present equations in high academic quality:
*   Integrated MathJax v3, allowing text formulas like `$E = mc^2$` or display systems like `$$\psi(x,t)$$` to be parsed.
*   Configured a post-append promise chain in `script.js`: `MathJax.typesetPromise([msgDiv])`. Whenever a new message bubble lands, it specifically compiles only that div, preserving rendering speed and avoiding full-page re-typesets.

### E. Incognito Browser Protection
Accessing `localStorage` throws a fatal `SecurityError` in incognito tabs or iframe contexts on modern browsers:
*   **The Fix:** Wrapped all `localStorage.getItem` and `localStorage.setItem` inside `try-catch` blocks. If blocked, the application automatically handles sessions in-memory, preventing script failure and keeping forms responsive.
*   **ReadyState Check:** Uses `document.readyState` check to instantly initialize script hooks in cases where the document completed loading before script execution.

---

## 5. Temporal Persona Alignment (Pre-1988 Boundary)
To ensure the digital twin behaves authentically as Richard Feynman when he was alive, the architecture implements strict temporal boundaries. Feynman passed away on February 15, 1988. Allowing the agent to cite papers, discuss historical events, or reference technologies from after his death would break the realism of the persona. We prevent this using three primary methods:
1.  **Chronological RAG Filter:** The raw vector databases (Chroma and BM25 index) are strictly populated using texts, lecture files, transcripts, and notes written or recorded by Feynman during his lifetime. The document index contains zero references to post-1988 research, avoiding the presence of anachronistic citations in the RAG contexts.
2.  **System Prompt Guardrails:** The system prompt instructs the LLM that it is not an AI, but Dr. Feynman himself. The LLM is explicitly forbidden from citing post-1988 papers or referring to discoveries that occurred after his lifetime. If asked to write citations, it selects papers from his lifetime (e.g. his 1961 path-integral works or his 1985 nanotech outlines).
3.  **Anachronism Mitigation Strategy:** When users prompt Feynman with modern concepts (such as modern transformer models or deep learning architectures), the agent is instructed to respond with his characteristic intellectual curiosity. He approaches them as hypothetical future predictions or abstract first-principles computational architectures, keeping character while admitting the concepts are "from after his time."

---

## 6. Hallucination Prevention & Mitigation
Hallucination mitigation is critical in educational contexts. We employ four layers of safety checks to ensure the digital twin remains grounded in authentic source materials:
1.  **Strict Grounding Constraints:** The prompt template strictly binds the model's responses to the retrieved hybrid RAG context segments using a rigid prompt clause. The model is penalized for bringing in external knowledge bases when answering factual physics questions.
2.  **Intellectual Honesty Injection:** Feynman's own philosophy of scientific honesty is built into the system prompt. The model is instructed: *"If you don't know something, or if a premise is flawed, bluntly admit it. 'I don't know, let's figure it out' is your default stance."* This redirects potential hallucinations into honest admissions.
3.  **Retrieved Context Denseness:** By merging vector embeddings and keyword indexes (BM25), the retrieval accuracy rises, offering a richer context segment. This reduces the need for the model to fill in details from its own parametric memory.
4.  **Temperature Controls:** The temperature parameter is locked at 0.7. This allows enough flexibility for storytelling, jokes, and anecdotes (crucial to Feynman's persona) while keeping his scientific explanations grounded and deterministic.

---

## 7. Step-by-Step Prompt Data Flow Example

To illustrate the operations of the digital twin, here is the detailed sequence showing how a prompt (e.g., **"What is a photon?"**) propagates through the stack:

1.  **User Input Event:** 
    *   The user types "What is a photon?" and hits Enter.
    *   JavaScript intercepts the form `submit` event, blocks browser refresh, appends the user chat bubble to `#messagesContainer`, resets the textarea heights, and appends the typing indicator animation to the screen.
2.  **API POST Dispatch:**
    *   An asynchronous HTTP POST fetch request `/api/chat` is dispatched with payload:
        ```json
        {
            "message": "What is a photon?",
            "session_id": "feynman_session_hm2iqierz"
        }
        ```
3.  **FastAPI Backend Interception:**
    *   FastAPI intercepts the request at `/api/chat` and calls the `feynman_twin.invoke(...)` wrapper with the matching session ID.
4.  **Dual Retrieval Pathways:**
    *   *Dense Retrieval:* Prompt is embedded (`text-embedding-004`) and Chroma DB returns the top 6 semantically related vector text blocks.
    *   *Sparse Retrieval:* BM25 Retrievier tokenizes the prompt and fetches the top 6 document chunks matching exact keyword frequencies.
5.  **Ensemble Fusion & LLM Inference:**
    *   `EnsembleRetriever` runs Reciprocal Rank Fusion (weights: 70% dense, 30% sparse) to compile grounded context.
    *   SQLite queries the dialogue memory history for `feynman_session_hm2iqierz`.
    *   The compiled prompt payload (System Prompt + Chat History + RAG Context + User Prompt) is sent to `gemini-2.5-flash` for synthesis.
6.  **Persistence Layer Write:**
    *   The new user prompt and LLM answer are saved as a stateful exchange in SQLite `message_store`.
7.  **Client Response & MD Compilation:**
    *   FastAPI returns the response. JavaScript hides the typing indicator, parses markdown elements, and appends Feynman's response bubble.
8.  **MathJax Typeset Trigger:**
    *   JavaScript triggers `MathJax.typesetPromise([msgDiv])` to compile inline LaTeX (`$E = hf$`) or block LaTeX into formatted formulas.

---

## 8. Directory Mapping & Repository Policies

*   **`static/`**: Clean separation of frontend scripts. Contains `index.html` (structure), `script.js` (UI logic, canvas engines, animations), and `style.css` (styling variables).
*   **`feynman_memory.db`**: Local SQLite database storing conversational session history.
*   **`feynman_twin_db/`**: Local cache directories hosting vector embeddings database.
*   **`.gitignore`**: Strictly ignores local binaries, DB caches, logs, credentials (`.env`), and python environments (`.venv/`) to maintain repository hygiene.
