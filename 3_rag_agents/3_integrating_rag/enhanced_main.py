from fastapi import FastAPI, HTTPException
from email_processor import EmailProcessor

app = FastAPI()
processor = EmailProcessor()

@app.post("/emails/process")
async def process_email(email_content: str):
    """Process email with RAG enhancement"""
    try:
        response = processor.process_email(email_content)
        return {"response": response, "enhanced": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge/search")
async def search_knowledge(query: str):
    """Search the knowledge base directly"""
    results = processor.rag.search(query, top_k=5)
    return {"results": results}

@app.post("/knowledge/reindex")
async def reindex_knowledge():
    """Reindex the knowledge base"""
    processor.rag.index_documents()
    return {"status": "reindexed", "documents": len(processor.rag.documents)}