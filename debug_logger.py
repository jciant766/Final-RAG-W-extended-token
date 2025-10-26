import json
import os
import re
from datetime import datetime
from typing import Any, List, Dict

class DebugLogger:
    """Centralized debug logging system"""
    
    def __init__(self, module_name: str):
        self.module = module_name
        self.log_dir = "debug_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Log files
        self.log_file = os.path.join(self.log_dir, f"{module_name}.log")
        self.query_log = os.path.join(self.log_dir, "queries.log")
        
    def log(self, level: str, message: str, data: Any = None):
        """Log message with timestamp"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'module': self.module,
            'level': level,
            'message': message
        }
        
        if data:
            entry['data'] = data
        
        # Write to module log
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        # Also log queries
        if level == 'query':
            with open(self.query_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    @staticmethod
    def get_recent_logs(module: str = None, n: int = 50) -> List[Dict]:
        """Get recent log entries"""
        log_dir = "debug_logs"
        logs = []
        
        if module:
            log_files = [os.path.join(log_dir, f"{module}.log")]
        else:
            log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) 
                        if f.endswith('.log')]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-n:]  # Last n lines
                    for line in lines:
                        try:
                            logs.append(json.loads(line.strip()))
                        except:
                            pass
        
        # Sort by timestamp
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        return logs[:n]
    
    @staticmethod
    def analyze_queries() -> Dict:
        """Analyze search patterns"""
        query_log = os.path.join("debug_logs", "queries.log")
        
        if not os.path.exists(query_log):
            return {}
        
        queries = []
        with open(query_log, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    queries.append(entry['message'])
                except:
                    pass
        
        # Analysis
        analysis = {
            'total_queries': len(queries),
            'unique_queries': len(set(queries)),
            'common_queries': {},
            'query_types': {
                'article_lookup': 0,
                'keyword_search': 0,
                'question': 0
            }
        }
        
        # Count query types
        for q in queries:
            if re.search(r'\barticle\s*\d+', q.lower()):
                analysis['query_types']['article_lookup'] += 1
            elif '?' in q:
                analysis['query_types']['question'] += 1
            else:
                analysis['query_types']['keyword_search'] += 1
        
        # Common queries
        from collections import Counter
        query_counts = Counter(queries)
        analysis['common_queries'] = dict(query_counts.most_common(10))
        
        return analysis
