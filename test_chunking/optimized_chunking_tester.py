#!/usr/bin/env python3
"""
Optimized Legal Document Chunking Tester

Tests WHOLE article chunking for text-embedding-3-large (8192 tokens).
Works with text files, not PDFs. No article splitting.
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import re
import tiktoken

# Add parent directory to import existing modules
sys.path.append('..')
from debug_logger import DebugLogger

class WholeArticleProcessor:
    """Simplified processor that keeps articles whole for large embeddings"""
    
    def __init__(self):
        self.debug = DebugLogger("whole_article_processor")
        self.encoding = tiktoken.get_encoding("cl100k_base")
        # Use text-embedding-3-large's full capacity
        self.max_tokens = 8192  # Full embedding model capacity
        
    def extract_articles(self, content: str) -> List[Dict[str, Any]]:
        """Extract articles using the existing robust logic"""
        # Import the existing article extraction from parent
        try:
            from doc_processor import DocumentProcessor
            temp_processor = DocumentProcessor()
            return temp_processor._extract_articles(content)
        except Exception as e:
            self.debug.log("error", f"Failed to extract articles: {e}")
            return []
    
    def create_whole_article_chunks(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create one chunk per article - NO SPLITTING"""
        chunks = []
        
        for article in articles:
            content = article['content']
            tokens = self.encoding.encode(content)
            token_count = len(tokens)
            
            # Create single chunk for entire article
            chunk_id = f"article_{article['article']}_p{article['page']}_whole"
            
            chunk = {
                'id': chunk_id,
                'content': content,
                'metadata': {
                    'article': str(article['article']),
                    'page': article['page'],
                    'position': article['position'],
                    'tokens': token_count,
                    'is_whole_article': True,
                    'citation': f"Commercial Code (Cap. 13) Art. {article['article']}",
                    'fits_in_embedding': token_count <= self.max_tokens
                }
            }
            
            chunks.append(chunk)
            
            # Log if article exceeds embedding capacity
            if token_count > self.max_tokens:
                self.debug.log("warning", f"Article {article['article']}: {token_count} tokens > {self.max_tokens} limit")
        
        return chunks

class OptimizedChunkingTester:
    def __init__(self):
        self.debug = DebugLogger("optimized_chunking_tester")
        self.test_dir = Path(".")  # Current directory
        self.text_dir = self.test_dir / "text_files"
        self.output_dir = self.test_dir / "test_outputs"
        
        # Ensure directories exist
        for dir_path in [self.text_dir, self.output_dir]:
            dir_path.mkdir(exist_ok=True)
        
        self.processor = WholeArticleProcessor()
        
    def run_optimized_tests(self):
        """Run optimized chunking tests with text files"""
        print("🎯 OPTIMIZED WHOLE-ARTICLE CHUNKING TESTER")
        print("=" * 60)
        print("✅ Configuration: text-embedding-3-large (8192 tokens)")
        print("✅ Strategy: 1 article = 1 chunk (no splitting)")
        print("✅ Input: Text files (no PDF processing)")
        
        # Check for text files
        text_files = list(self.text_dir.glob("*.txt"))
        if not text_files:
            print(f"\n❌ No text files found in {self.text_dir}/")
            print(f"📁 Please copy your Group 1 text files to:")
            print(f"   {self.text_dir.absolute()}")
            print(f"   Example: SUBSIDIARY LEGISLATION 386 02.txt")
            return
        
        print(f"\n📄 Found {len(text_files)} text files to test")
        
        all_results = []
        
        for text_file in text_files:
            print(f"\n🔍 Processing: {text_file.name}")
            result = self._test_whole_article_chunking(text_file)
            all_results.append(result)
        
        # Generate analysis
        self._generate_optimized_analysis(all_results)
        
        # Test embeddings
        self._test_embedding_compatibility(all_results)
        
        print(f"\n" + "=" * 60)
        print("✅ OPTIMIZED CHUNKING TESTS COMPLETE!")
        print(f"📊 Results: {self.output_dir.absolute()}")
        
    def _test_whole_article_chunking(self, text_file: Path) -> Dict[str, Any]:
        """Test whole-article chunking for a single document"""
        
        # Read text file
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"   📄 Content: {len(content):,} characters")
        
        # Extract articles
        articles = self.processor.extract_articles(content)
        print(f"   📋 Articles: {len(articles)}")
        
        # Create whole-article chunks
        chunks = self.processor.create_whole_article_chunks(articles)
        print(f"   🧩 Chunks: {len(chunks)} (1:1 ratio)")
        
        # Analyze token distribution
        token_counts = [c['metadata']['tokens'] for c in chunks]
        exceeds_limit = [c for c in chunks if c['metadata']['tokens'] > 8192]
        
        print(f"   📊 Token range: {min(token_counts) if token_counts else 0}-{max(token_counts) if token_counts else 0}")
        print(f"   ⚠️  Articles > 8192 tokens: {len(exceeds_limit)}")
        
        # Show samples
        print(f"   🔍 Sample chunks:")
        for i, chunk in enumerate(chunks[:3]):
            meta = chunk['metadata']
            print(f"      [{i+1}] Article {meta['article']}: {meta['tokens']} tokens")
            if meta['tokens'] > 8192:
                print(f"          ⚠️  EXCEEDS EMBEDDING LIMIT")
        
        analysis = {
            "document": text_file.stem,
            "articles_found": len(articles),
            "chunks_created": len(chunks),
            "one_to_one_ratio": len(articles) == len(chunks),
            "token_stats": {
                "min": min(token_counts) if token_counts else 0,
                "max": max(token_counts) if token_counts else 0,
                "avg": sum(token_counts) / len(token_counts) if token_counts else 0,
                "exceeds_8192": len(exceeds_limit)
            },
            "chunks": chunks,
            "articles_exceeding_limit": [
                {
                    "article": c['metadata']['article'],
                    "tokens": c['metadata']['tokens']
                } for c in exceeds_limit
            ]
        }
        
        # Save detailed results
        output_file = self.output_dir / f"{text_file.stem}_whole_article_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        return analysis
    
    def _generate_optimized_analysis(self, all_results: List[Dict[str, Any]]):
        """Generate optimized analysis report"""
        print(f"\n📋 Generating Optimized Analysis...")
        
        total_docs = len(all_results)
        total_articles = sum(r['articles_found'] for r in all_results)
        total_chunks = sum(r['chunks_created'] for r in all_results)
        total_exceeding = sum(r['token_stats']['exceeds_8192'] for r in all_results)
        
        # Perfect 1:1 ratio check
        perfect_ratio = all(r['one_to_one_ratio'] for r in all_results)
        
        report = {
            "optimization_summary": {
                "strategy": "whole_article_chunking",
                "embedding_model": "text-embedding-3-large",
                "max_tokens": 8192,
                "perfect_1_to_1_ratio": perfect_ratio
            },
            "totals": {
                "documents": total_docs,
                "articles": total_articles,
                "chunks": total_chunks,
                "articles_exceeding_limit": total_exceeding
            },
            "efficiency": {
                "avg_articles_per_doc": round(total_articles / total_docs, 1) if total_docs > 0 else 0,
                "chunk_article_ratio": f"{total_chunks}:{total_articles}",
                "percentage_exceeding_limit": round((total_exceeding / total_articles) * 100, 1) if total_articles > 0 else 0
            },
            "document_breakdown": [
                {
                    "document": r['document'],
                    "articles": r['articles_found'],
                    "chunks": r['chunks_created'],
                    "exceeding_limit": r['token_stats']['exceeds_8192'],
                    "max_tokens": r['token_stats']['max']
                } for r in all_results
            ]
        }
        
        # Save report
        with open(self.output_dir / "optimized_chunking_report.json", 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Perfect 1:1 ratio: {perfect_ratio}")
        print(f"   📊 {total_articles} articles → {total_chunks} chunks")
        print(f"   ⚠️  {total_exceeding} articles exceed 8192 tokens")
        
    def _test_embedding_compatibility(self, all_results: List[Dict[str, Any]]):
        """Test compatibility with text-embedding-3-large"""
        print(f"\n🧠 Testing text-embedding-3-large Compatibility...")
        
        # Get sample chunks
        all_chunks = []
        for result in all_results:
            all_chunks.extend(result['chunks'])
        
        if not all_chunks:
            print("   ❌ No chunks to test")
            return
        
        # Analyze compatibility
        compatible_chunks = [c for c in all_chunks if c['metadata']['tokens'] <= 8192]
        incompatible_chunks = [c for c in all_chunks if c['metadata']['tokens'] > 8192]
        
        compatibility_rate = (len(compatible_chunks) / len(all_chunks)) * 100
        
        print(f"   📊 Compatibility: {compatibility_rate:.1f}%")
        print(f"   ✅ Compatible chunks: {len(compatible_chunks)}")
        print(f"   ❌ Incompatible chunks: {len(incompatible_chunks)}")
        
        if incompatible_chunks:
            print(f"   ⚠️  Large articles requiring attention:")
            for chunk in incompatible_chunks[:5]:  # Show first 5
                meta = chunk['metadata']
                print(f"      - Article {meta['article']}: {meta['tokens']} tokens")
        
        # Save compatibility report
        compatibility_report = {
            "embedding_model": "text-embedding-3-large",
            "max_tokens": 8192,
            "total_chunks": len(all_chunks),
            "compatible_chunks": len(compatible_chunks),
            "incompatible_chunks": len(incompatible_chunks),
            "compatibility_rate": round(compatibility_rate, 1),
            "incompatible_articles": [
                {
                    "article": c['metadata']['article'],
                    "tokens": c['metadata']['tokens'],
                    "document": next(r['document'] for r in all_results if any(
                        chunk['metadata']['article'] == c['metadata']['article'] 
                        for chunk in r['chunks']
                    ))
                } for c in incompatible_chunks
            ]
        }
        
        with open(self.output_dir / "embedding_compatibility_report.json", 'w') as f:
            json.dump(compatibility_report, f, indent=2, ensure_ascii=False)

def main():
    """Run optimized chunking tests"""
    tester = OptimizedChunkingTester()
    tester.run_optimized_tests()

if __name__ == "__main__":
    main()
