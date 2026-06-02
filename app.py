# app.py
import os
import sys
from dotenv import load_dotenv

# Load credentials first before parsing analytical dependencies
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_core.runnables.history import RunnableWithMessageHistory

import config
import ingestion

def get_session_history(session_id: str):
    """Provides persistence mapping context matching the target session ID."""
    return SQLChatMessageHistory(
        session_id=session_id,
        connection=config.SQLITE_DB_URL
    )

def build_hybrid_retriever(chunks):
    """Combines semantic context mapping with literal keyword matching."""
    print("Initializing Dense Embedding Model (text-embedding-004)...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model=config.EMBEDDING_MODEL, 
        google_api_key=config.GOOGLE_API_KEY
    )
    
    # Dense Vector Space Configuration (70% weight preference)
    if os.path.exists(config.DB_DIR) and os.listdir(config.DB_DIR):
        print(f"Loading existing Chroma vector database from {config.DB_DIR}...")
        vectorstore = Chroma(
            persist_directory=config.DB_DIR,
            embedding_function=embeddings,
            collection_name="feynman_knowledge_base"
        )
    else:
        print("Vector database not found or empty. Creating a new Chroma vector database...")
        vectorstore = Chroma(
            persist_directory=config.DB_DIR,
            embedding_function=embeddings,
            collection_name="feynman_knowledge_base"
        )
        
        # Batch inserting with retry to avoid API rate limiting issues
        import time
        batch_size = 50
        total_chunks = len(chunks)
        print(f"Embedding {total_chunks} chunks in batches of {batch_size} with rate limit protection...")
        
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            success = False
            retries = 3
            wait_time = 12
            
            while not success and retries > 0:
                try:
                    vectorstore.add_documents(batch)
                    print(f"  Embedded chunks {i} to {min(i + batch_size, total_chunks)} of {total_chunks} successfully.")
                    success = True
                    time.sleep(1)
                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                        print(f"  [Rate Limit Hit] Sleeping for {wait_time}s before retry...")
                        time.sleep(wait_time)
                        retries -= 1
                        wait_time *= 1.5
                    else:
                        raise e
            if not success:
                raise RuntimeError("Failed to build vector database due to persistent rate limit exhaustion.")

    dense_retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

    # Sparse Keyword Configuration (30% weight preference)
    bm25_retriever = BM25Retriever.from_documents(chunks)
    bm25_retriever.k = 6

    # Reciprocal Rank Fusion Execution Pipeline
    return EnsembleRetriever(
        retrievers=[dense_retriever, bm25_retriever],
        weights=[0.7, 0.3]
    )

def init_digital_twin():
    """Compiles the operational modules into an integrated agent loop."""
    print("\n=== Initializing Feynman Digital Twin System ===")
    
    # 1. Processing Knowledge Layer
    raw_documents = ingestion.load_huggingface_data()
    chunks = ingestion.chunk_documents(raw_documents)
    hybrid_retriever = build_hybrid_retriever(chunks)
    
    # 2. Assembling Core LLM Inference Infrastructure
    llm = ChatGoogleGenerativeAI(
        model=config.LLM_MODEL, 
        temperature=0.7, 
        google_api_key=config.GOOGLE_API_KEY
    )
    
    # 3. Prompt Template Mapping (Injects grounding arrays and history placeholders)
    prompt = ChatPromptTemplate.from_messages([
        ("system", config.FEYNMAN_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    # 4. Assembling Chains
    qa_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(hybrid_retriever, qa_chain)
    
    # 5. Injection of Long-term Stateful Persistence Wrapper
    return RunnableWithMessageHistory(
        rag_chain,
        get_session_history=get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

# Compatibility alias for web server
init_agent = init_digital_twin

if __name__ == "__main__":
    if not config.GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY environment variable missing.")
        sys.exit(1)

    # Initialize agent configuration instance
    feynman_agent = init_digital_twin()
    print("\n--- Core Matrix Active. Say hi to Dr. Feynman! ---")
    print("(Type 'exit' or 'quit' to terminate the session)\n")
    
    # Set execution context credentials
    active_session_id = "dtu_student_session_1"
    runtime_config = {"configurable": {"session_id": active_session_id}}
    
    while True:
        try:
            user_msg = input("You: ")
            if user_msg.strip().lower() in ["exit", "quit"]:
                print("\nCatch you later! Don't stop questioning things.")
                break
                
            if not user_msg.strip():
                continue
                
            # Execute synchronous chain traversal loop 
            output = feynman_agent.invoke({"input": user_msg}, config=runtime_config)
            print(f"\nFeynman: {output['answer']}")
            
        except KeyboardInterrupt:
            print("\nSession safely closed.")
            break 