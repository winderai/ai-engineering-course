# Information System Design Specification

## Overview

This specification defines a prototype-level FastAPI information system for the Brewery Operations Hub. The system provides RAG-powered product search and natural language querying of order data through a single `information.py` module.

## Data Models

### Core Entities

#### Product Information

```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ProductInfo(BaseModel):
    product_id: str
    name: str
    alcohol_percentage: float
    ibu: int
    style: str
    flavor_profile: str
    ingredients: List[str]
    recipe: str
    backstory: str
    ai_theme: str
    brewing_notes: str
    serving_temp_min: int
    serving_temp_max: int
    storage_instructions: str
    shelf_life_days: int
    available_sizes: List[str]
    food_pairings: List[str]
    awards: List[str]

class ProductSearchResult(BaseModel):
    product_id: str
    name: str
    relevance_score: float
    matched_content: str
```

#### Order Information

```python
class OrderItem(BaseModel):
    product: str
    quantity: int
    unit: str

class Order(BaseModel):
    id: str
    customer: str
    status: str
    items: List[OrderItem]
    ship_date: Optional[str] = None
    expected_ship: Optional[str] = None
    tracking: Optional[str] = None

class OrderQueryResult(BaseModel):
    total_results: int
    orders: List[Order]
    summary: str
```

#### RAG Pipeline Models

```python
class DocumentChunk(BaseModel):
    chunk_id: str
    product_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]

class RAGSearchQuery(BaseModel):
    query: str
    max_results: int = 5
    similarity_threshold: float = 0.7

class RAGSearchResponse(BaseModel):
    query: str
    results: List[ProductSearchResult]
    total_chunks_searched: int
    processing_time_ms: float
```

### Request/Response Schemas

#### Product Search Endpoints

```python
class ProductSearchRequest(BaseModel):
    query: str
    max_results: int = 5
    include_details: bool = True

class ProductSearchResponse(BaseModel):
    query: str
    results: List[ProductSearchResult]
    total_results: int
    search_type: str = "rag"
```

#### Order Query Endpoints

```python
class OrderQueryRequest(BaseModel):
    question: str
    include_items: bool = True
    date_filter: Optional[str] = None

class OrderQueryResponse(BaseModel):
    question: str
    answer: str
    matching_orders: List[Order]
    sql_query: str
    execution_time_ms: float
```

## API Endpoints

### Product Information Endpoints

#### POST /information/products/search

**Purpose**: Search products using natural language RAG pipeline
**Request Body**: `ProductSearchRequest`
**Response**: `ProductSearchResponse`

#### GET /information/products/{product_id}

**Purpose**: Retrieve specific product information
**Path Parameters**:

- `product_id`: Product identifier
**Response**: `ProductInfo`

#### GET /information/products/

**Purpose**: List all available products
**Query Parameters**:

- `limit` (optional, default=50): Number of products to return
- `offset` (optional, default=0): Pagination offset
**Response**: `List[ProductInfo]`

### Order Information Endpoints

#### POST /information/orders/query

**Purpose**: Query orders using natural language with LLM-powered SQL generation
**Request Body**: `OrderQueryRequest`
**Response**: `OrderQueryResponse`

#### GET /information/orders/{order_id}

**Purpose**: Retrieve specific order details
**Path Parameters**:

- `order_id`: Order identifier
**Response**: `Order`

### System Health Endpoints

#### GET /information/health

**Purpose**: System health check and component status
**Response**:

```python
class HealthResponse(BaseModel):
    status: str
    rag_pipeline_ready: bool
    duckdb_connection_active: bool
    products_indexed: int
    orders_loaded: int
    uptime_seconds: float
```

## Business Logic

### RAG Pipeline Implementation

#### Document Indexing Process

1. **Data Loading**:
   - Scan `data/products/` directory for `.txt` files
   - Parse comprehensive product information including recipes and backstories
   - Extract structured fields (name, alcohol%, IBU, AI theme, brewing notes, etc.)
   - Create enriched `ProductInfo` objects with full content for RAG indexing

2. **Text Chunking**:
   - Split comprehensive product content (descriptions, recipes, backstories) into 300-character overlapping chunks
   - Maintain 75-character overlap between chunks
   - Include AI themes, brewing notes, and backstories in chunking
   - Preserve product metadata and content type in each chunk

3. **Embedding Generation**:
   - Use Ollama `granite-embedding:30m` model
   - Generate embeddings for each text chunk
   - Store embeddings in in-memory vector store
   - Index chunks by product_id for retrieval
   - **Important**: Always add `"think": false` to all ollama `/api/generate` requests

4. **Vector Storage**:
   - Implement simple in-memory vector database using numpy arrays
   - Support cosine similarity search
   - Maintain chunk-to-product mapping

#### Search Algorithm

1. **Query Processing**:
   - Generate embedding for user query using same model
   - Normalize query embedding vector

2. **Similarity Search**:
   - Calculate cosine similarity with all stored embeddings
   - Filter results by similarity threshold
   - Rank by relevance score

3. **Result Aggregation**:
   - Group matching chunks by product_id
   - Calculate aggregate relevance scores
   - Return top-k products with matched content

### Order Query System

#### Database Setup

1. **DuckDB Initialization**:
   - Create in-memory DuckDB instance
   - Load `data/orders.csv` into orders table
   - Normalize JSON structure for SQL querying
   - Create indexes on frequently queried fields

2. **Schema Creation**:

   ```sql
   CREATE TABLE orders (
       id VARCHAR PRIMARY KEY,
       customer VARCHAR,
       status VARCHAR,
       ship_date DATE,
       expected_ship DATE,
       tracking VARCHAR
   );

   CREATE TABLE order_items (
       order_id VARCHAR,
       product VARCHAR,
       quantity INTEGER,
       unit VARCHAR,
       FOREIGN KEY (order_id) REFERENCES orders(id)
   );
   ```

#### Natural Language to SQL Translation

1. **LLM-Powered SQL Generation**:
   - Use Ollama `qwen3:1.7b` model for text-to-SQL conversion
   - Provide database schema context in system prompt
   - Include example queries for few-shot learning
   - Generate complete SQL queries from natural language
   - **Important**: Always add `"think": false` to all ollama `/api/generate` requests

2. **Query Generation Process**:
   - Send natural language question to LLM with schema context
   - LLM generates SQL query based on database structure
   - Validate generated SQL for safety and syntax
   - Execute against DuckDB instance
   - Handle LLM errors with fallback to simple pattern matching

3. **Safety and Validation**:
   - Whitelist allowed SQL operations (SELECT only)
   - Sanitize generated queries to prevent injection
   - Limit query complexity and execution time
   - Log all generated queries for monitoring

### Core Service Methods

#### ProductInformationService

```python
class ProductInformationService:
    def load_products(self) -> List[ProductInfo]
    def index_products(self, products: List[ProductInfo]) -> None
    def search_products_rag(self, query: str, max_results: int) -> List[ProductSearchResult]
    def get_product_by_id(self, product_id: str) -> Optional[ProductInfo]
    def reindex_products(self) -> bool
```

#### OrderQueryService

```python
class OrderQueryService:
    def initialize_database(self) -> None
    def load_orders_from_csv(self, csv_path: str) -> None
    def generate_sql_with_llm(self, question: str, schema_context: str) -> str
    def validate_sql_query(self, sql: str) -> bool
    def execute_order_query(self, sql: str) -> List[Order]
    def get_order_by_id(self, order_id: str) -> Optional[Order]
```

#### VectorStoreService

```python
class VectorStoreService:
    def add_documents(self, chunks: List[DocumentChunk]) -> None
    def similarity_search(self, query_embedding: List[float], k: int) -> List[DocumentChunk]
    def get_embedding(self, text: str) -> List[float]
    def clear_index(self) -> None
```

## Data Flow and Processing

### Product Search Flow

1. **Request Received**: FastAPI endpoint receives search query
2. **Query Embedding**: Generate embedding using Ollama API
3. **Vector Search**: Find similar document chunks in vector store
4. **Result Ranking**: Sort by relevance score, filter by threshold
5. **Product Aggregation**: Group chunks by product, calculate scores
6. **Response Formation**: Format as ProductSearchResponse

### Order Query Flow

1. **Request Received**: FastAPI endpoint receives natural language question
2. **Intent Analysis**: Parse question to identify query components
3. **SQL Generation**: Convert to valid DuckDB SQL query
4. **Query Execution**: Run SQL against orders database
5. **Result Processing**: Convert SQL results to Order objects
6. **Response Formation**: Format as OrderQueryResponse with summary

### System Initialization

1. **Startup Sequence**:
   - Initialize FastAPI application
   - Load environment variables and configuration
   - Set up Ollama client connection
   - Initialize DuckDB database
   - Load and index product information
   - Import orders data from CSV
   - Start health monitoring

2. **Error Handling Strategy**:
   - Graceful degradation if Ollama unavailable
   - Fallback to keyword search for RAG failures
   - Connection retry logic for external services
   - Detailed logging for debugging

3. **Performance Considerations**:
   - Lazy loading of embeddings
   - In-memory caching of frequent queries
   - Connection pooling for database access
   - Async processing where possible

## Configuration Requirements

### Environment Variables

- `OLLAMA_BASE_URL`: Ollama API endpoint (default: <http://localhost:11434>)
- `EMBEDDING_MODEL`: Embedding model name (default: granite-embedding:30m)
- `LLM_MODEL`: LLM model for text-to-SQL generation (default: qwen3:1.7b)
- `DATA_DIRECTORY`: Path to data files (default: ./data)
- `RAG_SIMILARITY_THRESHOLD`: Default similarity threshold (default: 0.7)
- `MAX_SEARCH_RESULTS`: Default max results (default: 5)

### File Structure Requirements

```
data/
├── products/
│   ├── neural-network-ipa.txt
│   ├── gradient-descent-lager.txt
│   ├── transformer-stout.txt
│   ├── machine-learning-wheat.txt
│   ├── deep-learning-porter.txt
│   ├── algorithm-ale.txt
│   ├── tensorflow-tripel.txt
│   ├── pytorch-pilsner.txt
│   ├── reinforcement-rye.txt
│   ├── clustering-kolsch.txt
│   ├── regression-red-ale.txt
│   ├── bayesian-brown.txt
│   ├── ensemble-ipa.txt
│   ├── hyperparameter-hefeweizen.txt
│   ├── autoencoder-amber.txt
│   └── generative-gose.txt
└── orders.csv
```

### Dependencies

- fastapi: Web framework
- pydantic: Data validation
- duckdb: SQL database engine
- numpy: Vector operations
- httpx: HTTP client for Ollama
- python-dotenv: Environment management
- uvicorn: ASGI server
