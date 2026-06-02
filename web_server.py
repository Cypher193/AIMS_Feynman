import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv

# Ensure dotenv loads properly
load_dotenv()

import app
import memory

# Initialize the FastAPI app
web_app = FastAPI(
    title="Dr. Richard Feynman - Digital Twin",
    description="An interactive, RAG-backed digital twin of Nobel laureate physicist Richard Feynman.",
    version="1.0.0"
)

# Initialize the LangChain RAG-backed Feynman agent
try:
    feynman_twin = app.init_agent()
    print("--- Feynman Agent Chain Online ---")
except Exception as e:
    print(f"Error initializing Feynman Agent: {e}")
    feynman_twin = None

# Request & Response Schemas
class ChatRequest(BaseModel):
    message: str
    session_id: str = "web_session_default"

class ChatResponse(BaseModel):
    answer: str

class MessageItem(BaseModel):
    type: str  # "human" or "ai"
    content: str

class HistoryResponse(BaseModel):
    messages: List[MessageItem]

@web_app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not feynman_twin:
        raise HTTPException(status_code=500, detail="Feynman Agent is offline. Check backend logs.")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    try:
        # Config for session history
        config_dict = {"configurable": {"session_id": request.session_id}}
        
        # Invoke the LangChain agent
        response = feynman_twin.invoke({"input": request.message}, config=config_dict)
        return ChatResponse(answer=response['answer'])
    except Exception as e:
        print(f"Error during chat invoke: {e}")
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

@web_app.get("/api/history/{session_id}", response_model=HistoryResponse)
async def get_history_endpoint(session_id: str):
    try:
        # Fetch SQL Chat history
        history = memory.get_long_term_memory(session_id)
        raw_messages = history.messages
        
        serializable_messages = []
        for msg in raw_messages:
            # Map LangChain message types to simple JSON representations
            msg_type = "human" if msg.type == "human" else "ai"
            serializable_messages.append(
                MessageItem(type=msg_type, content=msg.content)
            )
        
        return HistoryResponse(messages=serializable_messages)
    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

@web_app.get("/api/sessions")
async def list_sessions_endpoint():
    try:
        import sqlite3, json
        conn = sqlite3.connect("feynman_memory.db")
        cursor = conn.cursor()
        
        # Verify if the table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_store'")
        if not cursor.fetchone():
            conn.close()
            return {"sessions": []}
            
        cursor.execute("SELECT session_id FROM message_store GROUP BY session_id")
        sessions = [r[0] for r in cursor.fetchall()]
        
        session_list = []
        for sid in sessions:
            cursor.execute(
                "SELECT message FROM message_store WHERE session_id = ? ORDER BY id ASC",
                (sid,)
            )
            rows = cursor.fetchall()
            title = "New Topic"
            for r in rows:
                msg = json.loads(r[0])
                if msg.get("type") == "human":
                    content = msg.get("data", {}).get("content", "")
                    title = content[:32] + "..." if len(content) > 32 else content
                    break
            session_list.append({"session_id": sid, "title": title})
            
        conn.close()
        # Sort session list so newest or custom sessions are well-ordered
        return {"sessions": session_list}
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return {"sessions": []}

@web_app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    try:
        import sqlite3
        conn = sqlite3.connect("feynman_memory.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM message_store WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Session {session_id} deleted."}
    except Exception as e:
        print(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

# Mount static files folder
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    web_app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Catch-all to serve index.html at root
@web_app.get("/")
async def read_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Welcome to Feynman Digital Twin! HTML UI files are missing."}

if __name__ == "__main__":
    print("Starting Web Server...")
    uvicorn.run(web_app, host="127.0.0.1", port=8000)
