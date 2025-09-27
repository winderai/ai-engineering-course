import requests
from rag_pipeline import SimpleRAG

class EmailProcessor:
    def __init__(self):
        self.rag = SimpleRAG()
        self.rag.index_documents()

    def process_email(self, email_content: str) -> str:
        """Process email using RAG"""
        # Retrieve relevant context
        context_docs = self.rag.search(email_content, top_k=2)

        # Build context string
        context = "\n".join([
            f"Document: {doc['document']['content']}"
            for doc in context_docs
        ])

        # Create prompt with context
        prompt = f"""You are a brewery operations assistant. Use the following context to help answer the customer's email.

CONTEXT:
{context}

EMAIL:
{email_content}

Provide a helpful response that references specific information from the context when relevant. If you mention specific products or orders, cite the source."""

        # Get response from LLM
        response = requests.post('http://localhost:11434/api/generate',
            json={
                'model': 'qwen3:1.7b',
                'prompt': prompt,
                'stream': False
            })

        return response.json()['response']

if __name__ == "__main__":
    processor = EmailProcessor()

    # Test with sample emails
    test_emails = [
        "Hi, I need information about your IPA products and their alcohol content.",
        "What's the status of order ORD-2024-002?",
        "Do you have any lagers available in kegs?"
    ]

    for email in test_emails:
        print(f"\nEMAIL: {email}")
        print("RESPONSE:")
        response = processor.process_email(email)
        print(response)
        print("-" * 50)