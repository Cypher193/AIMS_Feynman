# ingestion.py
from datasets import load_dataset
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_huggingface_data():
    """
    Pulls the clean, pre-processed Feynman Lectures dataset directly 
    from Hugging Face, completely avoiding OCR corruption and firewalls.
    """
    print("Pulling Feynman text data from Hugging Face mirror...")
    
    # Automatically pulls and caches the data locally
    dataset = load_dataset("enesxgrahovac/the-feynman-lectures-on-physics", split="train")
    
    # Select first 30 lectures to stay within free-tier embedding rate limits
    dataset = dataset.select(range(min(30, len(dataset))))
    
    documents = []
    for idx, entry in enumerate(dataset):
        # Extract and compile all string components from the row columns
        content_pieces = []
        for col_name, val in entry.items():
            if isinstance(val, str) and val.strip():
                content_pieces.append(f"{col_name.capitalize()}: {val}")
                
        full_content = "\n".join(content_pieces)
        
        # Fallback to general conversion if formatted string compilation is empty
        if not full_content.strip():
            full_content = "\n".join([str(v) for v in entry.values() if str(v).strip()])

        # Build Document object with proper tracking metadata
        doc = Document(
            page_content=full_content,
            metadata={
                "source": "huggingface:enesxgrahovac/the-feynman-lectures-on-physics",
                "author": "Richard Feynman",
                "type": "official_lecture",
                "excerpt_id": f"hf_row_{idx}"
            }
        )
        documents.append(doc)
        
    print(f"Successfully loaded {len(documents)} clean reference excerpts.")
    return documents

def chunk_documents(documents):
    """
    Applies hierarchical splitting logic to avoid chopping off equations 
    or isolating the punchlines of structural physical analogies.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split raw corpus into {len(chunks)} structural RAG chunks.")
    return chunks