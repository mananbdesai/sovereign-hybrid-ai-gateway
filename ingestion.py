import os
import logging
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# Configure Enterprise-Grade Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration & Environment Setup ---
DATA_DIRECTORY = "/opt/ai-gateway/data"
QDRANT_URL = "http://192.168.0.122:6333"
COLLECTION_NAME = "mainframe_logic"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def main():
    logger.info("Starting Phase 3: Sovereign Data Ingestion Pipeline")

    # 1. Ensure Data Directory Exists
    if not os.path.exists(DATA_DIRECTORY):
        logger.error(f"Data directory not found: {DATA_DIRECTORY}. Creating it now...")
        os.makedirs(DATA_DIRECTORY, exist_ok=True)
        logger.info(f"Please populate {DATA_DIRECTORY} with .cbl and .txt files and rerun.")
        return

    # 2. Load Proprietary Legacy Files (.cbl and .txt)
    logger.info(f"Scanning {DATA_DIRECTORY} for COBOL and architecture files...")
    
    # We use glob patterns to specifically target our required extensions
    cbl_loader = DirectoryLoader(DATA_DIRECTORY, glob="**/*.cbl", loader_cls=TextLoader)
    txt_loader = DirectoryLoader(DATA_DIRECTORY, glob="**/*.txt", loader_cls=TextLoader)
    
    documents = cbl_loader.load() + txt_loader.load()
    
    if not documents:
        logger.warning("No documents found. Pipeline aborted.")
        return
        
    logger.info(f"Successfully loaded {len(documents)} document(s).")

    # 3. Chunk the Legacy Code Logically
    # COBOL logic requires careful chunking. 1000 characters with a 200 overlap 
    # ensures paragraph definitions and perform statements remain structurally intact.
    logger.info("Chunking documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Split documents into {len(chunks)} logical chunks.")

    # 4. Initialize CPU-Bound Embedding Model (Zero-Trust/No-GPU Constraint)
    logger.info(f"Initializing embedding model: {EMBEDDING_MODEL} (STRICT CPU MODE)")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        # CRUCIAL INSTRUCTION: Force local CPU execution to prevent PyTorch/CUDA crashes on the Edge server
        model_kwargs={'device': 'cpu'} 
    )

    # 5. Connect to Local Qdrant & Ensure Collection Exists
    logger.info(f"Connecting to Vector DB at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)
    
    if not client.collection_exists(COLLECTION_NAME):
        logger.info(f"Collection '{COLLECTION_NAME}' not found. Creating it...")
        # all-MiniLM-L6-v2 outputs 384-dimensional vectors
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    # 6. Upsert Vectors into Qdrant
    logger.info(f"Upserting vectors into collection: {COLLECTION_NAME}...")
    QdrantVectorStore.from_documents(
        chunks,
        embeddings,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
    )
    
    logger.info("✅ Phase 3 Complete: Sovereign Data successfully ingested and vectorized.")

if __name__ == "__main__":
    main()
