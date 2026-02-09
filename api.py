"""
Flask API for Maltese Law RAG Chat Interface.

Run: python api.py
Then open: http://localhost:5000
"""

import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from src.retrieval.graphrag_retriever import GraphRAGRetriever, build_rag_context
from src.generation.response_generator import LegalResponseGenerator
from src.chat_history import ChatHistoryManager
from user_tracking import tracker

# Setup logging with rotation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add file handler with rotation
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
file_handler = RotatingFileHandler(
    log_dir / 'api.log',
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

app = Flask(__name__, static_folder='static')

# Configure CORS with stricter settings for production
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:*", "http://127.0.0.1:*"],
        "methods": ["GET", "POST", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

# Rate limiting: 30 requests per minute per IP
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["30 per minute"],
    storage_uri="memory://"
)

# Security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:;"
    )
    return response

# Initialize components (lazy loading)
_retriever = None
_generator = None
_chat_history = None


def get_retriever():
    global _retriever
    if _retriever is None:
        logger.info("Initializing GraphRAG Retriever...")
        _retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")
        logger.info("Retriever ready!")
    return _retriever


def get_generator():
    global _generator
    if _generator is None:
        logger.info("Initializing Response Generator...")
        _generator = LegalResponseGenerator()
        logger.info("Generator ready!")
    return _generator


def get_chat_history():
    global _chat_history
    if _chat_history is None:
        logger.info("Initializing Chat History Manager...")
        _chat_history = ChatHistoryManager()
        logger.info("Chat History ready!")
    return _chat_history


def require_auth(f):
    """Decorator to require authentication for endpoints."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header or query param
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
        else:
            token = request.args.get('token') or request.json.get('token') if request.json else None

        if not token:
            return jsonify({"error": "Authentication required", "code": "NO_TOKEN"}), 401

        # Verify token
        user = tracker.verify_token(token)
        if not user:
            return jsonify({"error": "Invalid or expired token", "code": "INVALID_TOKEN"}), 401

        # Attach user to request
        request.user = user
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def index():
    """Serve the chat UI."""
    return send_from_directory('static', 'index.html')


@app.route('/register')
def register_page():
    """Serve the registration page."""
    return send_from_directory('static', 'register.html')


@app.route('/login')
def login_page():
    """Serve the login page."""
    return send_from_directory('static', 'login.html')


@app.route('/lib/<path:filename>')
@limiter.exempt
def serve_lib(filename):
    """Serve library files (vis-network, PDF.js, etc.)."""
    return send_from_directory('lib', filename)


@app.route('/static/<path:filename>')
@limiter.exempt
def serve_static(filename):
    """Serve static files including PDFs from 'All Malta law PDFs' folder."""
    pdf_dir = os.path.join(os.path.dirname(__file__), 'All Malta law PDFs')
    return send_from_directory(pdf_dir, filename)


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint with token-based authentication.

    Request body:
    {
        "message": "What are the penalties for tax evasion?",
        "token": "user_api_token",
        "settings": { ... }
    }

    Or use Authorization header: "Bearer <token>"
    """
    try:
        data = request.json
        query = data.get('message', '').strip()

        if not query:
            return jsonify({"error": "No message provided"}), 400

        # Get token from Authorization header or request body
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
        else:
            token = data.get('token')

        if not token:
            return jsonify({"error": "Authentication token required"}), 401

        # Verify token and get user
        user = tracker.verify_token(token)
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_id = user['id']
        username = user['username']

        settings = data.get('settings', {})

        # Get retriever and search
        retriever = get_retriever()

        # Legal RAG best practice: retrieve more chunks for comprehensive answers
        # Legal questions often span multiple provisions, exceptions, definitions, and penalties
        # Increased values to improve coverage (e.g., amber light rules in S.L. 65.11)
        search_results = retriever.search(
            query=query,
            limit=settings.get('limit', 15),  # Primary articles per law
            top_laws=settings.get('top_laws', 25),  # More laws = better coverage of S.L. regulations
            expand_graph=settings.get('expand_graph', True),  # Add cross-referenced articles
            auto_classify=settings.get('auto_classify', True),
            max_hops=1
        )

        # Build context for LLM - include more articles for complete legal answers
        context = build_rag_context(search_results, max_articles=10)  # Increased from 5

        # Debug: log what we found
        articles = search_results.get('articles', [])
        logger.info(f"Found {len(articles)} articles, {len(search_results.get('laws', []))} laws")
        if articles:
            logger.info(f"First article: {articles[0].get('law_code')} Art {articles[0].get('article_number')}")
        else:
            logger.warning("NO ARTICLES FOUND - context will be empty!")

        # Generate response
        generator = get_generator()
        response_data = generator.generate(query, articles)

        # Build response
        result = {
            "response": response_data.get("response", "I couldn't find relevant information."),
            "sources": response_data.get("sources", []),
            "citation_pages": response_data.get("citation_pages", {}),  # Map citations to PDF pages
            "classification": search_results.get("classification"),
            "categories_used": search_results.get("categories_used", []),
            "laws_searched": search_results.get("laws_searched", []),
            "laws": search_results.get("laws", []),  # Include law details for UI
            "articles_found": len(search_results.get("articles", [])),
            "schedules_found": len(search_results.get("schedules", [])),
            "related_articles": len(search_results.get("related_articles", [])),
            "query_expansion": search_results.get("query_expansion"),
            "debug": {
                "graph_paths": search_results.get("graph_path", [])[:5]
            }
        }

        # Log query to user tracking database
        if user_id:
            try:
                import sqlite3
                tracking_db = 'user_tracking.db'
                conn = sqlite3.connect(tracking_db)
                cursor = conn.cursor()

                # Extract token usage and cost
                usage_data = response_data.get('usage', {})
                input_tokens = usage_data.get('input_tokens', 0)
                output_tokens = usage_data.get('output_tokens', 0)
                total_tokens = usage_data.get('total_tokens', 0)
                cost_usd = usage_data.get('cost_usd', 0.0)

                # Insert usage log with token tracking
                cursor.execute('''
                    INSERT INTO usage_logs (user_id, query, response_length, sources_count,
                                          input_tokens, output_tokens, total_tokens, cost_usd)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, query, len(result['response']), len(result['sources']),
                      input_tokens, output_tokens, total_tokens, cost_usd))

                # Update user's total queries
                cursor.execute('''
                    UPDATE users SET total_queries = total_queries + 1, last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user_id,))

                conn.commit()
                conn.close()
                logger.info(f"Logged query for user '{username}' (id: {user_id}): {total_tokens} tokens, ${cost_usd:.4f}")
            except Exception as e:
                logger.error(f"Failed to log query: {e}", exc_info=True)

        # Send Telegram notification
        try:
            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
            telegram_chat = os.getenv("TELEGRAM_CHAT_ID")

            if telegram_token and telegram_chat:
                logger.info(f"Sending Telegram notification to chat_id: {telegram_chat}")
                msg = f"💬 New query from {username}:\n\n❓ {query[:200]}{'...' if len(query) > 200 else ''}\n\n📊 Response: {len(result['response'])} chars, {len(result['sources'])} sources"

                response = requests.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={"chat_id": telegram_chat, "text": msg},
                    timeout=5
                )

                if response.status_code == 200:
                    logger.info("Telegram notification sent successfully")
                else:
                    logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            else:
                logger.warning(f"Telegram not configured - token: {bool(telegram_token)}, chat: {bool(telegram_chat)}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}", exc_info=True)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def stats():
    """Get database statistics."""
    try:
        retriever = get_retriever()
        counts = retriever.count()
        return jsonify(counts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route('/api/pdf-lookup', methods=['GET'])
def pdf_lookup():
    """Get PDF filename lookup dictionary."""
    import re
    import os

    pdf_lookup = {}
    pdf_dir = os.path.join(os.path.dirname(__file__), "All Malta law PDFs")
    if os.path.isdir(pdf_dir):
        for fname in os.listdir(pdf_dir):
            if fname.endswith(".pdf"):
                # Extract law code from filename like "Companies Act (Cap. 386).pdf"
                m = re.search(r'\(((?:Cap\.|S\.L\.)\s*[\d.]+)\)', fname)
                if m:
                    law_code = m.group(1)
                    pdf_lookup[law_code] = fname
                    # Also add version without space after dot
                    no_space = law_code.replace('. ', '.')
                    if no_space != law_code:
                        pdf_lookup[no_space] = fname

    return jsonify(pdf_lookup)


@app.route('/graph')
def graph_view():
    """Serve the interactive graph visualization."""
    return send_from_directory('static', 'graph.html')


@app.route('/api/graph-data', methods=['GET'])
def graph_data():
    """
    Get graph data for visualization.
    Query params:
        - top_n: Number of top connected laws (default 100)
    """
    import json as json_lib
    import lancedb
    import pandas as pd

    try:
        top_n = int(request.args.get('top_n', 100))

        db = lancedb.connect('./lancedb_graphrag')
        laws_df = db.open_table('law_summaries').to_pandas()
        edges_df = db.open_table('edges').to_pandas()

        # Build law lookup
        law_info = {}
        for _, law in laws_df.iterrows():
            categories = json_lib.loads(law.get('categories', '[]'))
            info = {
                'id': law['law_code'],
                'label': law['law_code'],
                'name': law['law_name'][:80],
                'category': categories[0] if categories else 'other',
                'total_articles': int(law.get('total_articles', 0)),
            }
            law_info[law['law_code']] = info
            no_space = law['law_code'].replace('. ', '.')
            if no_space != law['law_code']:
                law_info[no_space] = info

        # Get external references only
        external_edges = edges_df[edges_df['edge_type'] == 'EXTERNAL_REF'].copy()

        def get_law_code(article_id):
            if article_id.startswith('art:'):
                parts = article_id.replace('art:', '').split('/')
                return parts[0]
            elif article_id.startswith('law:'):
                return article_id.replace('law:', '')
            return article_id

        external_edges['source_law'] = external_edges['source_id'].apply(get_law_code)
        external_edges['target_law_code'] = external_edges['target_id'].apply(get_law_code)

        # Aggregate
        law_edges = external_edges.groupby(['source_law', 'target_law_code']).size().reset_index(name='weight')
        law_edges = law_edges[law_edges['source_law'] != law_edges['target_law_code']]

        # Filter to Maltese laws only
        def is_maltese_law(code):
            return (code.startswith('Cap.') or code.startswith('Cap ') or
                    code.startswith('S.L.') or code.startswith('S.L ') or
                    code.startswith('L.N.') or code.startswith('L.N '))

        law_edges = law_edges[
            law_edges['source_law'].apply(is_maltese_law) &
            law_edges['target_law_code'].apply(is_maltese_law)
        ]

        # Get top N most connected
        all_refs = pd.concat([
            law_edges.groupby('source_law')['weight'].sum(),
            law_edges.groupby('target_law_code')['weight'].sum()
        ])
        total_refs = all_refs.groupby(all_refs.index).sum().sort_values(ascending=False)
        top_laws = set(total_refs.head(top_n).index)

        # Filter edges
        law_edges = law_edges[
            law_edges['source_law'].isin(top_laws) &
            law_edges['target_law_code'].isin(top_laws)
        ]

        # Build nodes and links
        laws_with_edges = set(law_edges['source_law']) | set(law_edges['target_law_code'])

        nodes = []
        for law_code in laws_with_edges:
            if law_code in law_info:
                info = law_info[law_code]
                nodes.append({
                    'id': law_code,
                    'label': info['label'],
                    'name': info['name'],
                    'category': info['category'],
                    'size': info['total_articles'],
                    'refs': int(total_refs.get(law_code, 0))
                })
            else:
                nodes.append({
                    'id': law_code,
                    'label': law_code,
                    'name': f'{law_code} (external)',
                    'category': 'external',
                    'size': 0,
                    'refs': int(total_refs.get(law_code, 0))
                })

        links = []
        for _, edge in law_edges.iterrows():
            links.append({
                'source': edge['source_law'],
                'target': edge['target_law_code'],
                'weight': int(edge['weight'])
            })

        return jsonify({
            'nodes': nodes,
            'links': links,
            'stats': {
                'total_nodes': len(nodes),
                'total_links': len(links)
            }
        })

    except Exception as e:
        logger.error(f"Graph data error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/verify')
def verify_view():
    """Serve the RAG verification dashboard."""
    return send_from_directory('static', 'verify.html')


@app.route('/factcheck')
def factcheck_view():
    """Serve the fact-check page for individual responses."""
    return send_from_directory('static', 'factcheck.html')


@app.route('/admin')
def admin_view():
    """Serve the admin dashboard for user tracking."""
    return send_from_directory('static', 'admin.html')


@app.route('/api/verification-data', methods=['GET'])
def verification_data():
    """
    Get test questions with retrieved articles for manual verification.
    This runs the RAG on each test question and returns the results.
    """
    import json as json_lib

    try:
        # Import test questions
        sys.path.insert(0, str(Path(__file__).parent / 'tests'))
        from comprehensive_rag_eval import TEST_QUESTIONS

        retriever = get_retriever()
        results = []

        # Limit to first 20 for faster loading (can be paginated later)
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))

        for q in TEST_QUESTIONS[offset:offset + limit]:
            # Run retrieval
            search_results = retriever.search(
                query=q.query,
                limit=10,
                top_laws=15,
                expand_graph=True,
                auto_classify=True
            )

            # Extract articles
            articles = []
            for art in search_results.get('articles', [])[:5]:
                articles.append({
                    'law_code': art.get('law_code', ''),
                    'article_number': art.get('article_number', ''),
                    'title': art.get('title', ''),
                    'text': art.get('text', '')[:2000]  # Limit text size
                })

            results.append({
                'id': q.id,
                'query': q.query,
                'category': q.category,
                'expected_laws': q.expected_laws,
                'expected_keywords': q.expected_keywords,
                'notes': q.notes,
                'retrieved_articles': articles,
                'laws_found': [a['law_code'] for a in articles]
            })

        return jsonify(results)

    except Exception as e:
        logger.error(f"Verification data error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/law-source/<path:law_code>', methods=['GET'])
def law_source(law_code):
    """
    Get the raw extraction JSON for a specific law.
    Used for manual verification of test answers.
    """
    import json as json_lib

    try:
        extractions_dir = Path('extractions')

        # Try different filename variations
        variations = [
            f"{law_code}.json",
            f"{law_code.replace(' ', '')}.json",
            f"{law_code.replace('.', '. ')}.json",
        ]

        for filename in variations:
            filepath = extractions_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json_lib.load(f)
                return jsonify(data)

        # Try to find partial match
        for json_file in extractions_dir.glob('*.json'):
            if law_code.replace(' ', '') in json_file.stem.replace(' ', ''):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json_lib.load(f)
                return jsonify(data)

        return jsonify({"error": f"Law {law_code} not found in extractions"}), 404

    except Exception as e:
        logger.error(f"Law source error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================================
# CHAT HISTORY ENDPOINTS
# ============================================================================

@app.route('/api/chats/save', methods=['POST'])
def save_chat():
    """
    Save or update a chat conversation.

    Request body:
    {
        "chat_id": "optional-existing-id",
        "title": "Optional title",
        "messages": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "...", "sources": [...]}
        ],
        "metadata": {"key": "value"}
    }
    """
    try:
        data = request.json
        messages = data.get('messages', [])

        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        chat_history = get_chat_history()

        chat_id = chat_history.save_chat(
            messages=messages,
            chat_id=data.get('chat_id'),
            title=data.get('title'),
            metadata=data.get('metadata')
        )

        return jsonify({
            "success": True,
            "chat_id": chat_id,
            "message": "Chat saved successfully"
        })

    except Exception as e:
        logger.error(f"Save chat error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/chats/list', methods=['GET'])
def list_chats():
    """
    List all saved chats.

    Query params:
        - limit: Max chats to return (default 50)
        - offset: Number to skip (default 0)
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        chat_history = get_chat_history()
        chats = chat_history.list_chats(limit=limit, offset=offset)

        return jsonify({
            "chats": chats,
            "count": len(chats)
        })

    except Exception as e:
        logger.error(f"List chats error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/chats/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    """Load a specific chat by ID."""
    try:
        chat_history = get_chat_history()
        chat = chat_history.load_chat(chat_id)

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        return jsonify(chat)

    except Exception as e:
        logger.error(f"Get chat error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/chats/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    """Delete a chat by ID."""
    try:
        chat_history = get_chat_history()
        deleted = chat_history.delete_chat(chat_id)

        if not deleted:
            return jsonify({"error": "Chat not found"}), 404

        return jsonify({
            "success": True,
            "message": "Chat deleted successfully"
        })

    except Exception as e:
        logger.error(f"Delete chat error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/chats/search', methods=['GET'])
def search_chats():
    """
    Search chats by title or content.

    Query params:
        - q: Search query
        - limit: Max results (default 20)
    """
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 20))

        if not query:
            return jsonify({"error": "No search query provided"}), 400

        chat_history = get_chat_history()
        results = chat_history.search_chats(query, limit=limit)

        return jsonify({
            "results": results,
            "count": len(results),
            "query": query
        })

    except Exception as e:
        logger.error(f"Search chats error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/chats/stats', methods=['GET'])
def chat_stats():
    """Get chat history statistics."""
    try:
        chat_history = get_chat_history()
        stats = chat_history.get_stats()
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Chat stats error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/chats/<chat_id>/export', methods=['GET'])
def export_chat(chat_id):
    """
    Export a chat as JSON.

    Query params:
        - format: 'json' (default) or 'txt'
    """
    try:
        chat_history = get_chat_history()
        chat = chat_history.load_chat(chat_id)

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        export_format = request.args.get('format', 'json').lower()

        if export_format == 'txt':
            # Export as readable text
            lines = [
                f"Chat: {chat['title']}",
                f"Created: {chat['created_at']}",
                f"Messages: {chat['message_count']}",
                "=" * 60,
                ""
            ]

            for msg in chat['messages']:
                role = msg['role'].upper()
                content = msg['content']
                lines.append(f"{role}:")
                lines.append(content)
                lines.append("")

            text_content = "\n".join(lines)

            return text_content, 200, {
                'Content-Type': 'text/plain',
                'Content-Disposition': f'attachment; filename="chat_{chat_id}.txt"'
            }

        else:
            # Export as JSON (default)
            return jsonify(chat), 200, {
                'Content-Disposition': f'attachment; filename="chat_{chat_id}.json"'
            }

    except Exception as e:
        logger.error(f"Export chat error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================================
# USER AUTHENTICATION & TRACKING ENDPOINTS
# ============================================================================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """
    Public user registration endpoint.

    Request body:
    {
        "email": "user@example.com",
        "username": "username",
        "password": "password"
    }
    """
    try:
        data = request.json
        email = data.get('email', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not email or not username or not password:
            return jsonify({"error": "Email, username and password required"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        result = tracker.create_user(username, password, email, notes="Self-registered user")

        if result.get('success'):
            return jsonify({
                "success": True,
                "user_id": result['user_id'],
                "username": result['username'],
                "email": email,
                "api_token": result['api_token'],
                "message": "Account created successfully"
            })
        else:
            return jsonify({"error": result.get('error')}), 400

    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/signin', methods=['POST'])
def signin():
    """
    Public user login endpoint.

    Request body:
    {
        "username": "username_or_email",
        "password": "password"
    }
    """
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        user = tracker.authenticate(username, password)

        if user:
            return jsonify({
                "success": True,
                "username": user['username'],
                "email": user.get('email', ''),
                "api_token": user['api_token'],
                "message": "Login successful"
            })
        else:
            return jsonify({"error": "Invalid username or password"}), 401

    except Exception as e:
        logger.error(f"Signin error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
    {
        "username": "client_name",
        "password": "secure_password",
        "email": "optional@email.com",
        "notes": "Free trial client - Company X"
    }
    """
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()
        notes = data.get('notes', '').strip()

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        result = tracker.create_user(username, password, email, notes)

        if result.get('success'):
            return jsonify({
                "success": True,
                "user_id": result['user_id'],
                "username": result['username'],
                "api_token": result['api_token'],
                "message": "User created successfully. Save your API token!"
            })
        else:
            return jsonify({"error": result.get('error')}), 400

    except Exception as e:
        logger.error(f"Register error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Authenticate user with username/password.

    Request body:
    {
        "username": "client_name",
        "password": "secure_password"
    }
    """
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        user = tracker.authenticate(username, password)

        if user:
            return jsonify({
                "success": True,
                "user": user,
                "message": "Login successful"
            })
        else:
            return jsonify({"error": "Invalid username or password"}), 401

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/verify', methods=['GET'])
@require_auth
def verify_auth():
    """Verify token is valid and return user info."""
    return jsonify({
        "success": True,
        "user": request.user
    })


# ============================================================================
# ADMIN ENDPOINTS (for monitoring client usage)
# ============================================================================

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    """
    Get all users with stats (for admin monitoring).

    In production, add admin authentication here.
    Query params:
        - admin_key: Simple admin password (set in .env)
    """
    # Simple admin auth - in production use proper admin roles
    admin_key = request.args.get('admin_key') or request.headers.get('X-Admin-Key')
    expected_key = os.getenv('ADMIN_KEY', 'change_this_in_production')

    if admin_key != expected_key:
        return jsonify({"error": "Admin authentication required"}), 401

    try:
        users = tracker.get_all_users()
        return jsonify({
            "users": users,
            "count": len(users)
        })

    except Exception as e:
        logger.error(f"Admin users error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/users/<int:user_id>/stats', methods=['GET'])
def admin_user_stats(user_id):
    """
    Get detailed usage stats for a specific user.

    Query params:
        - admin_key: Admin authentication
    """
    admin_key = request.args.get('admin_key') or request.headers.get('X-Admin-Key')
    expected_key = os.getenv('ADMIN_KEY', 'change_this_in_production')

    if admin_key != expected_key:
        return jsonify({"error": "Admin authentication required"}), 401

    try:
        stats = tracker.get_user_stats(user_id)
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Admin user stats error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/users/<int:user_id>/deactivate', methods=['POST'])
def admin_deactivate_user(user_id):
    """
    Deactivate a user account.

    Request body or query params:
        - admin_key: Admin authentication
    """
    admin_key = request.args.get('admin_key') or request.headers.get('X-Admin-Key')
    if request.json:
        admin_key = admin_key or request.json.get('admin_key')

    expected_key = os.getenv('ADMIN_KEY', 'change_this_in_production')

    if admin_key != expected_key:
        return jsonify({"error": "Admin authentication required"}), 401

    try:
        tracker.deactivate_user(user_id)
        return jsonify({
            "success": True,
            "message": f"User {user_id} deactivated"
        })

    except Exception as e:
        logger.error(f"Admin deactivate error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/admin/analytics')
def analytics_dashboard():
    """Serve the MVP analytics dashboard."""
    return send_from_directory('static', 'analytics.html')


@app.route('/api/admin/analytics', methods=['GET'])
def get_analytics():
    """
    Get CRM-style analytics for all clients.

    Returns:
        List of all users with their engagement stats
    """
    admin_key = request.args.get('admin_key') or request.headers.get('X-Admin-Key')
    expected_key = os.getenv('ADMIN_KEY', 'change_this_in_production')

    if admin_key != expected_key:
        return jsonify({"error": "Admin authentication required"}), 401

    try:
        import sqlite3
        from datetime import datetime

        db_path = 'user_tracking.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all users with their stats
        cursor.execute("""
            SELECT id, username, email, created_at, total_queries, last_login, is_active, notes
            FROM users
            ORDER BY last_login DESC NULLS LAST, created_at DESC
        """)
        users = cursor.fetchall()

        user_stats = []

        for user in users:
            user_id, username, email, created_at, total_queries, last_login, is_active, notes = user

            # Get last activity and cost stats from usage_logs
            cursor.execute("""
                SELECT timestamp FROM usage_logs
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id,))

            last_activity_row = cursor.fetchone()
            last_active = last_activity_row[0] if last_activity_row else last_login

            # Calculate total cost and token usage
            cursor.execute("""
                SELECT
                    COALESCE(SUM(input_tokens), 0) as total_input,
                    COALESCE(SUM(output_tokens), 0) as total_output,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(cost_usd), 0) as total_cost
                FROM usage_logs
                WHERE user_id = ?
            """, (user_id,))

            cost_row = cursor.fetchone()
            total_input_tokens = int(cost_row[0]) if cost_row else 0
            total_output_tokens = int(cost_row[1]) if cost_row else 0
            total_tokens = int(cost_row[2]) if cost_row else 0
            total_cost_usd = float(cost_row[3]) if cost_row else 0.0

            # Calculate average cost per query
            avg_cost_per_query = (total_cost_usd / total_queries) if total_queries > 0 else 0.0

            # Calculate engagement status
            if last_active:
                last_active_dt = datetime.fromisoformat(last_active)
                now = datetime.now()
                days_since = (now - last_active_dt).days
                hours_since = (now - last_active_dt).total_seconds() / 3600

                if hours_since < 24:
                    status = "hot"
                    status_emoji = "🔥"
                    status_text = "Active today"
                elif days_since < 7:
                    status = "warm"
                    status_emoji = "⚠️"
                    status_text = f"{days_since}d ago"
                else:
                    status = "cold"
                    status_emoji = "❄️"
                    status_text = f"{days_since}d ago"
            else:
                status = "cold"
                status_emoji = "❄️"
                status_text = "Never active"
                days_since = None
                hours_since = None

            user_stats.append({
                "id": user_id,
                "username": username,
                "email": email or "",
                "created_at": created_at,
                "total_queries": total_queries or 0,
                "last_active": last_active,
                "status": status,
                "status_emoji": status_emoji,
                "status_text": status_text,
                "days_since_activity": days_since,
                "is_active": bool(is_active),
                "notes": notes or "",
                "cost_stats": {
                    "total_input_tokens": total_input_tokens,
                    "total_output_tokens": total_output_tokens,
                    "total_tokens": total_tokens,
                    "total_cost_usd": round(total_cost_usd, 4),
                    "avg_cost_per_query": round(avg_cost_per_query, 4)
                }
            })

        conn.close()

        return jsonify({
            "users": user_stats,
            "total_users": len(user_stats),
            "active_users": len([u for u in user_stats if u['status'] in ['hot', 'warm']])
        })

    except Exception as e:
        logger.error(f"Analytics error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Create static folder if it doesn't exist
    Path('static').mkdir(exist_ok=True)

    # Get port from environment variable, default to 5000
    port = int(os.getenv('PORT', 5000))

    print("=" * 60)
    print("Maltese Law RAG Chat API with User Tracking")
    print("=" * 60)
    print(f"\nStarting server on port {port}...")
    print(f"Open http://localhost:{port} in your browser")
    print(f"Open http://localhost:{port}/verify for RAG verification")
    print("\nUser tracking enabled:")
    print("  - Telegram notifications configured")
    print("  - All queries logged to database")
    print("=" * 60)

    # Set debug=False for production
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', '0') == '1')
