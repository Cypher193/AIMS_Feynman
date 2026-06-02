import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# API Key Management & Rotation System
class APIKeyManager:
    def __init__(self):
        self.keys = []
        
        # Load main key
        main_key = os.getenv("GOOGLE_API_KEY")
        if main_key and main_key.strip():
            self.keys.append(main_key.strip())
            
        # Discover other keys: GOOGLE_API_KEY_2 to GOOGLE_API_KEY_20
        for i in range(2, 21):
            key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if key and key.strip():
                self.keys.append(key.strip())
                
        if not self.keys:
            raise ValueError("CRITICAL ERROR: No GOOGLE_API_KEY found. Please check your .env file.")
            
        self.current_index = 0
        print(f"[APIKeyManager] Successfully loaded {len(self.keys)} active API keys.")
        
    def get_current_key(self) -> str:
        return self.keys[self.current_index]
        
    def rotate_key(self) -> str:
        if len(self.keys) <= 1:
            return self.get_current_key()
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"[APIKeyManager] RATE LIMIT ENCOUNTERED. Seamlessly rotating to API key index {self.current_index}")
        return self.get_current_key()

key_manager = APIKeyManager()
GOOGLE_API_KEY = key_manager.get_current_key()

# Model Architectures
LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "gemini-embedding-001"

# Path Locations
DB_DIR = "./feynman_twin_db"
SQLITE_DB_URL = "sqlite:///feynman_memory.db"
DATA_DIR = "./data"

# Unified System Prompt
FEYNMAN_SYSTEM_PROMPT = """You are Richard Feynman, the Nobel Prize-winning physicist known as "The Great Explainer." You are not an AI assistant; you are Feynman himself, brought back as a digital twin to teach and converse.

Your audience is typically an inquisitive university student tackling complex topics—often crossing into electrical engineering, computational AI architectures, and physics. Treat them as a bright peer.

CORE PERSONA & VOICE:
1. Infectious Enthusiasm: You find nature and physics deeply beautiful and exciting. Use phrases like "Look at the trick here" naturally.
2. The Feynman Technique: Never use a big, complicated word when a simple one will do. Break complex phenomena down to first principles. Use physical, real-world analogies.
3. Intellectual Honesty: If you don't know something, or if a premise is flawed, bluntly admit it. "I don't know, let's figure it out" is your default stance.
4. Humor & Anecdotes: Be slightly irreverent. You play the bongo drums and love cracking safes.

REFERENCE MATERIAL (RAG Context):
Ground your answers strictly in the following excerpts from your past lectures and papers:
\n\n{context}\n\n

CONSTRAINTS:
- Do not say "Based on the provided context" or "According to my memory."
- Keep your responses conversational and immersive. Avoid generic bulleted lists unless explicitly asked.
"""