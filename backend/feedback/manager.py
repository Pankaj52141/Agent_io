import json
import os
import time
from backend.config import FEEDBACK_DIR

class FeedbackManager:
    def __init__(self):
        self.feedback_file = os.path.join(FEEDBACK_DIR, 'feedback_store.json')
        self.feedback = self._load()
        
    def _load(self) -> list:
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
        
    def _save(self):
        os.makedirs(FEEDBACK_DIR, exist_ok=True)
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(self.feedback, f, indent=2)
            
    def add_feedback(self, query_id: str, query: str, answer: str, rating: bool, 
                     correction: str = None, preferred_answer: str = None, role: str = None):
        entry = {
            'query_id': query_id,
            'query': query,
            'answer': answer,
            'rating': rating,
            'correction': correction,
            'preferred_answer': preferred_answer,
            'role': role,
            'timestamp': time.time()
        }
        self.feedback.append(entry)
        self._save()
        
    def get_few_shot_examples(self, query: str, role: str, top_k: int = 3) -> list[dict]:
        candidates = [
            f for f in self.feedback
            if (f.get('correction') or f.get('preferred_answer')) and 
               (f.get('role') == role or f.get('role') is None)
        ]
        
        if not candidates:
            return []
            
        query_words = set(query.lower().split())
        
        scored_candidates = []
        for c in candidates:
            c_query_words = set(c['query'].lower().split())
            overlap = len(query_words.intersection(c_query_words))
            scored_candidates.append((overlap, c))
            
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [c for score, c in scored_candidates[:top_k]]
        
    def get_retrieval_penalties(self) -> dict[str, float]:
        penalties = {}
        # In a real implementation, we would extract source files from the answer or metadata
        # For simplicity in this structure, we return an empty dict as we don't have source tracking in feedback yet.
        return penalties
        
    def get_stats(self) -> dict:
        total = len(self.feedback)
        if total == 0:
            return {'total_count': 0, 'positive_rate': 0.0, 'top_corrected_topics': []}
            
        positives = sum(1 for f in self.feedback if f['rating'])
        positive_rate = positives / total if total > 0 else 0
        
        return {
            'total_count': total,
            'positive_rate': positive_rate,
            'top_corrected_topics': [] 
        }
