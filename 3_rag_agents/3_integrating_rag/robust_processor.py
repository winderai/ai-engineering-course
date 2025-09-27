import requests
from typing import Dict, Any, List
from rag_pipeline import SimpleRAG

class RobustEmailProcessor:
    def __init__(self):
        self.rag = SimpleRAG()
        try:
            self.rag.index_documents()
            self.rag_available = True
        except Exception as e:
            print(f"RAG initialization failed: {e}")
            self.rag_available = False

    def process_email_safe(self, email_content: str) -> Dict[str, Any]:
        """Process email with fallback strategies"""
        try:
            if self.rag_available:
                # Try RAG-enhanced processing
                context_docs = self.rag.search(email_content, top_k=2)

                # Check if we found relevant results
                if context_docs and context_docs[0]['score'] > 0.3:
                    return self._process_with_rag(email_content, context_docs)
                else:
                    return self._process_without_context(email_content)
            else:
                return self._process_without_context(email_content)

        except Exception as e:
            # Ultimate fallback
            return {
                'response': "I apologize, but I'm experiencing technical difficulties. Please contact our support team directly.",
                'error': str(e),
                'fallback_used': True
            }

    def _process_with_rag(self, email: str, context_docs: List) -> Dict:
        """RAG-enhanced processing"""
        context = "\n".join([
            f"Document: {doc['document']['content']}"
            for doc in context_docs
        ])

        prompt = f"""You are a brewery operations assistant. Use the following context to help answer the customer's email.

CONTEXT:
{context}

EMAIL:
{email}

Provide a helpful response that references specific information from the context when relevant."""

        response = requests.post('http://localhost:11434/api/generate',
            json={'model': 'qwen3:1.7b', 'prompt': prompt, 'stream': False})

        return {
            'response': response.json()['response'],
            'fallback_used': False
        }

    def _process_without_context(self, email: str) -> Dict:
        """Fallback processing without RAG"""
        prompt = f"""You are a brewery operations assistant. Respond helpfully to this email, but acknowledge that you don't have access to specific order or product information.

EMAIL: {email}"""

        response = requests.post('http://localhost:11434/api/generate',
            json={'model': 'qwen3:1.7b', 'prompt': prompt, 'stream': False})

        return {
            'response': response.json()['response'],
            'fallback_used': True
        }