from typing import List, Dict

class ContextManager:
    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4

    def compress_context(self, documents: List[Dict], query: str) -> str:
        """Compress context to fit token limits"""
        context_parts = []
        current_tokens = 0

        # Reserve tokens for query and response
        available_tokens = self.max_tokens - self.estimate_tokens(query) - 500

        for doc in documents:
            content = doc['document']['content']
            doc_tokens = self.estimate_tokens(content)

            if current_tokens + doc_tokens <= available_tokens:
                context_parts.append(content)
                current_tokens += doc_tokens
            else:
                # Truncate if needed
                remaining_tokens = available_tokens - current_tokens
                if remaining_tokens > 100:
                    truncated = content[:remaining_tokens * 4]
                    context_parts.append(truncated + "...")
                break

        return "\n".join(context_parts)