import chromadb
from chromadb.config import Settings
import json
from typing import List, Dict, Optional
from debug_logger import DebugLogger
import os
from openai import OpenAI
from dotenv import load_dotenv

class VectorStore:
    """ChromaDB with optimized search"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.debug = DebugLogger("vector_store")
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize OpenAI API for long-context embeddings
        load_dotenv()
        if os.path.exists('env'):
            load_dotenv('env', override=True)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("OPENAI_API_KEY")
            except:
                pass
        if not api_key:
            self.debug.log("error", "OPENAI_API_KEY environment variable not set.")
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.openai_client = OpenAI(api_key=api_key)
        self.embedding_model = "text-embedding-3-large"  # 8192-token context, 3072-dim - Best for legal documents
        
        # Initialize collection
        self.collection = self._init_collection()
    
    def _init_collection(self):
        """Initialize or load collection with error recovery"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Try to get existing collection
                collection = self.client.get_collection("malta_code_v2")
                self.collection = collection
                
                # Test if collection is working
                doc_count = collection.count()
                self.debug.log("info", f"Loaded collection with {doc_count} documents")
                
                if doc_count == 0:
                    self.debug.log("info", "Collection is empty, loading documents...")
                    self._load_documents()
                
                return collection
                
            except Exception as e:
                self.debug.log("warning", f"Collection load attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    # Try to reset and recreate
                    try:
                        self.debug.log("info", "Attempting to reset database...")
                        self.client.reset()
                    except:
                        pass
                    
                    # Create new collection
                    collection = self.client.create_collection(
                        name="malta_code_v2",
                        metadata={"hnsw:space": "cosine"}
                    )
                    self.collection = collection
                    self.debug.log("info", f"Created new collection (attempt {attempt + 1})")
                    self._load_documents()
                    return collection
                else:
                    # Final attempt - create fresh
                    self.debug.log("error", "All attempts failed, creating fresh collection")
                    collection = self.client.create_collection(
                        name="malta_code_v2",
                        metadata={"hnsw:space": "cosine"}
                    )
                    self.collection = collection
                    self._load_documents()
                    return collection
    
    def _load_documents(self):
        """Load chunks into vector store with fallback to document processing"""
        try:
            # Try to load from processed chunks first
            if os.path.exists('processed_chunks.json'):
                with open('processed_chunks.json', 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                self.debug.log("info", f"Loaded {len(chunks)} chunks from processed_chunks.json")
            else:
                # Fallback: process documents directly
                self.debug.log("info", "processed_chunks.json not found, processing documents directly...")
                chunks = self._process_documents_directly()
            
            # Batch process for efficiency
            batch_size = 100
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                ids = [c['id'] for c in batch]
                documents = [c['content'] for c in batch]
                metadatas = [c['metadata'] for c in batch]
                
                # Generate embeddings
                embeddings = self._embed_texts(documents)
                
                # Add to collection
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
                
                self.debug.log("debug", f"Loaded batch {i//batch_size + 1}")
            
            self.debug.log("info", f"Loaded {len(chunks)} chunks total")
            
        except Exception as e:
            self.debug.log("error", f"Error loading documents: {e}")
            raise
    
    def _process_documents_directly(self):
        """Process documents directly when processed_chunks.json is not available"""
        try:
            from doc_processor import DocumentProcessor
            
            self.debug.log("info", "Initializing document processor...")
            processor = DocumentProcessor()
            
            # Process the main document
            if os.path.exists('malta_commercial_code_text.txt'):
                self.debug.log("info", "Processing malta_commercial_code_text.txt...")
                processor.process_document('malta_commercial_code_text.txt')
            
            # Process OCR documents if available
            ocr_dir = 'ocr/output'
            if os.path.exists(ocr_dir):
                self.debug.log("info", f"Processing OCR documents from {ocr_dir}...")
                for filename in os.listdir(ocr_dir):
                    if filename.endswith('.txt'):
                        filepath = os.path.join(ocr_dir, filename)
                        self.debug.log("info", f"Processing {filename}...")
                        processor.process_document(filepath)
            
            # Load the processed chunks
            if os.path.exists('processed_chunks.json'):
                with open('processed_chunks.json', 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                self.debug.log("info", f"Successfully processed {len(chunks)} chunks")
                return chunks
            else:
                self.debug.log("error", "Document processing failed - no chunks generated")
                return []
                
        except Exception as e:
            self.debug.log("error", f"Error processing documents directly: {e}")
            return []
    
    def search(self, query: str, n_results: int = 10, 
               filters: Optional[Dict] = None) -> List[Dict]:
        """Unified search with debugging"""
        self.debug.log("query", f"Search query: {query}")
        
        # Generate query embedding
        query_embedding = self._embed_texts([query])[0]
        
        # Build where clause
        where_clause = filters if filters else None
        
        # Search - retrieve many candidates, let AI filter what's relevant
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results * 2, 200),  # Retrieve broadly for AI-powered filtering
            where=where_clause,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Process results
        processed = self._process_results(results, query, n_results)
        
        self.debug.log("info", f"Returned {len(processed)} results")
        return processed
    
    def get_article(self, article_num: str, doc_code: Optional[str] = None) -> List[Dict]:
        """Get specific article, optionally constrained to a document code."""
        self.debug.log("query", f"Article lookup: {article_num} (doc={doc_code or 'any'})")
        
        # ChromaDB get() doesn't support multiple where conditions, so we need to use query() instead
        if doc_code and doc_code not in {"sl", "sl_*"}:
            # Use our own embedding method to ensure dimension consistency
            dummy_query = f"article {article_num} {doc_code}"
            query_embedding = self._embed_texts([dummy_query])[0]
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=100,  # Get enough to find the article
                where={"doc_code": doc_code},
                include=['documents', 'metadatas']
            )
            # Filter by article number in the results
            filtered_results = []
            for i, metadata in enumerate(results['metadatas'][0]):
                if metadata.get('article') == article_num:
                    filtered_results.append({
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': metadata,
                        'score': 1.0,
                        'citation': metadata['citation']
                    })
            return filtered_results
        else:
            # Simple article lookup without doc_code constraint
            results = self.collection.get(
                where={"article": article_num},
                include=['documents', 'metadatas']
            )
        
        if not results['ids']:
            return []
        
        # Format results
        formatted = []
        for i in range(len(results['ids'])):
            formatted.append({
                'id': results['ids'][i],
                'content': results['documents'][i],
                'metadata': results['metadatas'][i],
                'score': 1.0,
                'citation': results['metadatas'][i]['citation']
            })
        
        # Sort by chunk index
        formatted.sort(key=lambda x: x['metadata'].get('chunk_index', 0))
        
        return formatted
    
    def _process_results(self, results: Dict, query: str, 
                        n_results: int) -> List[Dict]:
        """Process and rank results"""
        if not results['ids'] or not results['ids'][0]:
            return []
        
        processed = []
        
        # Check for article lookup
        import re
        article_match = re.search(r'\b(?:article|art\.?)\s*(\d+[A-Z]?)\b', 
                                query.lower())
        
        if article_match:
            # Direct article lookup
            article_num = article_match.group(1).upper()
            article_results = self.get_article(article_num)
            if article_results:
                return article_results[:n_results]
        
        # Process semantic results
        for i in range(len(results['ids'][0])):
            doc_id = results['ids'][0][i]
            
            # Convert distance to similarity
            distance = results['distances'][0][i]
            score = 1 / (1 + distance)  # Convert to 0-1 score
            
            processed.append({
                'id': doc_id,
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'score': score,
                'citation': results['metadatas'][0][i]['citation']
            })
        
        # Sort by score
        processed.sort(key=lambda x: x['score'], reverse=True)
        
        # Deduplicate multi-chunk articles
        final_results = self._deduplicate_results(processed)
        
        return final_results[:n_results]

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts using OpenAI long-context embeddings.
        Splits into smaller batches to respect API payload limits.
        """
        embeddings: List[List[float]] = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=batch
            )
            # Ensure results are ordered corresponding to input
            batch_embeddings = [item.embedding for item in sorted(
                response.data, key=lambda x: x.index
            )]
            embeddings.extend(batch_embeddings)
        return embeddings
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Merge multi-chunk articles while preserving distinct documents.
        Use a compound key (doc_code, article) to avoid collapsing
        Companies Act Art. X with Commercial Code Art. X.
        """
        article_map: Dict[tuple, Dict] = {}

        for result in results:
            md = result.get('metadata', {})
            key = (md.get('doc_code'), md.get('article'))
            if key not in article_map:
                article_map[key] = result
            else:
                if result.get('score', 0) > article_map[key].get('score', 0):
                    article_map[key] = result

        return list(article_map.values())
