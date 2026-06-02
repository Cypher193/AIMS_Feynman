from typing import List, Any
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
import config

# Rate-limit aware Embeddings wrapper
class SafeGoogleGenerativeAIEmbeddings(Embeddings):
    def __init__(self, model: str, key_manager: Any, **kwargs: Any):
        self.model = model
        self.key_manager = key_manager
        self.kwargs = kwargs
        self._init_embeddings()
        
    def _init_embeddings(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model,
            api_key=self.key_manager.get_current_key(),
            **self.kwargs
        )
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        attempts = 0
        max_attempts = len(self.key_manager.keys)
        while attempts < max_attempts:
            try:
                return self.embeddings.embed_documents(texts)
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "limit" in err_str or "resource_exhausted" in err_str:
                    self.key_manager.rotate_key()
                    self._init_embeddings()
                    attempts += 1
                else:
                    raise e
        raise Exception("All API keys rate limited for embeddings.")
        
    def embed_query(self, text: str) -> List[float]:
        attempts = 0
        max_attempts = len(self.key_manager.keys)
        while attempts < max_attempts:
            try:
                return self.embeddings.embed_query(text)
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "limit" in err_str or "resource_exhausted" in err_str:
                    self.key_manager.rotate_key()
                    self._init_embeddings()
                    attempts += 1
                else:
                    raise e
        raise Exception("All API keys rate limited for query embedding.")

def build_hybrid_retriever(chunks):
    embeddings = SafeGoogleGenerativeAIEmbeddings(model=config.EMBEDDING_MODEL, key_manager=config.key_manager)
    
    # Dense Retriever
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=config.DB_DIR,
        collection_name="feynman_knowledge_base"
    )
    dense_retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

    # Sparse Retriever
    bm25_retriever = BM25Retriever.from_documents(chunks)
    bm25_retriever.k = 6

    # Hybrid Ensemble
    return EnsembleRetriever(
        retrievers=[dense_retriever, bm25_retriever],
        weights=[0.7, 0.3]
    )