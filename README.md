#  Dr. Richard Feynman - Digital Twin System

An interactive, premium, RAG-backed digital twin of Nobel laureate physicist **Richard Feynman**. Built with LangChain, ChromaDB, and FastAPI, this system simulates Feynman's physics intuition, teaching style, and personality. It features a stunning, minimalist holographic quantum dashboard with dynamic subatomic particle fields and integrated dialogue persistence.


##  Key Features

*   **RAG-Backed Persona**: Grounded in authentic lectures using a **Hybrid Retriever** (Chroma Dense Semantic Vector + BM25 Sparse Keyword Matcher) fused via Reciprocal Rank Fusion (RRF) with `text-embedding-004` and `gemini-2.0-flash`.
*   **Hugging Face Mirror Ingestion**: Auto-pulls and caches clean lecture text directly from Hugging Face datasets, ensuring pristine formatting completely free of OCR corruption.
*   **Topic-Segregated Session Memory**: Utilizes SQLite dialogue persistence (`SQLChatMessageHistory`) to provide separate, long-term memory for each independent discussion topic.
*   **PDF Conversion Pipeline**: Local utility powered by `marker-pdf` to convert native lecture drafts (like `fy(1).pdf`) into clean markdown formats in seconds.
*   **Minimalist REST API**: Fully non-blocking FastAPI backend serving live chat operations, database deletions, session history lookups, and static assets.

---

##  Technology Stack

1.  **AI & Core Chains**: `langchain-core`, `langchain-classic` (legacy retrieval chains), `langchain-google-genai`
2.  **Vector Store**: `Chroma` (vector database on disk)
3.  **Keyword Indexing**: `BM25Retriever` (rank-bm25)
4.  **Ingestion & Datasets**: Hugging Face `datasets`
5.  **Web Backend**: `FastAPI`, `Uvicorn`, `Pydantic`, `SQLAlchemy` (SQLite memory)
6.  **PDF Conversion CLI**: `marker-pdf`, `PyMuPDF`
7.  **Frontend Layout**: Vanilla HTML5, CSS3 Custom Properties, canvas-driven particle engines.

---

##  Project Structure

```dir
Feyman_digital_twin/
├── .venv/                      # Python virtual environment containing dependencies
├── data/                       # Grounding reference data folders
│   ├── official_lectures/      # Converted markdown lectures folder
│   └── transcripts/            # Local transcript datasets
├── pdf_source/                 # Source drafts folder
│   └── fy(1).pdf               # Native Richard Feynman Lecture PDF
├── static/                     # Web client asset folder
│   ├── images/
│   │   └── feynman_avatar.png  # Dr. Richard Feynman visual avatar
│   ├── index.html              # Quantum Dashboard UI structure
│   ├── style.css               # Cosmic styling custom tokens & animations
│   └── script.js               # Canvas physics engines & client logic
├── app.py                      # Core LangChain RAG pipeline & console interface
├── config.py                   # System credentials manager & prompt parameters
├── ingestion.py                # Dataset downloader & recursive text splitter
├── memory.py                   # SQLite long-term persistence connection helpers
├── web_server.py               # FastAPI backend router & session manager
├── requirements.txt            # Package manifest
└── README.md                   # System documentation (This file!)
```

---

##  Quick Start Guide

### 1. Credentials Setup
Copy `.env.example` into a new file named `.env` in the root directory:
```bash
GOOGLE_API_KEY="your-gemini-api-key-here"
```

### 2. Launch the Web Application
Start the FastAPI server:
```bash
.venv\Scripts\python web_server.py
```
Open your browser and navigate to:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### 3. CLI Dialogue Loop
To converse directly in your terminal:
```bash
.venv\Scripts\python app.py
```

### 4. Running PDF-to-Markdown Conversion
To convert local lecture drafts (avoiding expensive CPU-bound deep-learning OCR loops on native text layers):
```bash
.venv\Scripts\marker_single .\pdf_source\fy(1).pdf --output_dir .\data\official_lectures\ --disable_ocr
```

---

##  Architectural Insights

### Hybrid Retrieval & Reciprocal Rank Fusion
To mimic Dr. Feynman's ability to provide both precise, mathematical explanations and high-level analogies, the retrieval pipeline is dual-pronged:
1.  **Dense Semantic Space (70% weighting)**: Leverages `text-embedding-004` to measure conceptually related paragraphs, even when different words are used.
2.  **Sparse Keyword Space (30% weighting)**: Uses `BM25` literal text indexing to guarantee that specific physics formulas, terms, or historical equations are matched precisely.

The results are blended using **Reciprocal Rank Fusion (RRF)** to feed the most grounding reference context directly into the Gemini prompt template.

### Quota-Friendly Startup Caching
The dense vector search is configured to cache database files locally in `feynman_twin_db`. On system startup, the pipeline checks if the database is already written, bypassing expensive API calls and avoiding free-tier `429 RESOURCE_EXHAUSTED` rate limits. If a database is missing, it automatically creates one in rate-limit protected batches.
