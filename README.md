## Long-context embeddings and chunking

- Chunking increased to 3000 tokens with 200 overlap in `doc_processor.py`.
- Embeddings use OpenAI `text-embedding-3-large` for up to 8192-token inputs in `vector_store.py`.
- Ensure `OPENAI_API_KEY` is set (see `env`).



