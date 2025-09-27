import requests
from typing import Dict, Any
from email_processor import EmailProcessor

class CitationProcessor(EmailProcessor):
    def process_email_with_citations(self, email_content: str) -> Dict[str, Any]:
        """Process email with source citations"""
        context_docs = self.rag.search(email_content, top_k=3)

        # Create numbered context with sources
        context_with_sources = ""
        sources = {}

        for i, doc in enumerate(context_docs, 1):
            source_id = f"[{i}]"
            content = doc['document']['content']
            source_file = doc['document']['source']

            context_with_sources += f"{source_id} {content}\n"
            sources[source_id] = {
                'file': source_file,
                'type': doc['document']['type'],
                'relevance_score': doc['score']
            }

        prompt = f"""You are a brewery operations assistant. Answer using the numbered sources below.

SOURCES:
{context_with_sources}

EMAIL: {email_content}

Provide a response and cite sources using [1], [2], etc. when you reference specific information."""

        response = requests.post('http://localhost:11434/api/generate',
            json={
                'model': 'qwen3:1.7b',
                'prompt': prompt,
                'stream': False
            })

        return {
            'response': response.json()['response'],
            'sources': sources,
            'context_docs': context_docs
        }

if __name__ == "__main__":
    processor = CitationProcessor()
    result = processor.process_email_with_citations(
        "What's the alcohol content of your IPA?"
    )
    print("RESPONSE:", result['response'])
    print("\nSOURCES:")
    for source_id, info in result['sources'].items():
        print(f"{source_id} {info['file']} (score: {info['relevance_score']:.3f})")