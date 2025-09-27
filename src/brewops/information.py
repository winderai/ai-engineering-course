import os
import time
import logging
import duckdb
import numpy as np
import httpx
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Data Models


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


# Request/Response Schemas


class ProductSearchRequest(BaseModel):
    query: str
    max_results: int = 5
    include_details: bool = True


class ProductSearchResponse(BaseModel):
    query: str
    results: List[ProductSearchResult]
    total_results: int
    search_type: str = "rag"


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


class HealthResponse(BaseModel):
    status: str
    rag_pipeline_ready: bool
    duckdb_connection_active: bool
    products_indexed: int
    orders_loaded: int
    uptime_seconds: float


# Core Services


class VectorStoreService:
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "granite-embedding:30m")

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Ollama API."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.ollama_base_url}/api/embed",
                    json={"model": self.embedding_model, "input": text},
                )
                response.raise_for_status()
                result = response.json()

                if "embeddings" in result and result["embeddings"]:
                    return result["embeddings"][0]
                else:
                    logger.error(f"No embeddings in response: {result}")
                    return []

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def add_documents(self, chunks: List[DocumentChunk]) -> None:
        """Add document chunks to the vector store."""
        self.chunks.extend(chunks)

        # Build embeddings matrix
        embeddings = [chunk.embedding for chunk in self.chunks if chunk.embedding]
        if embeddings:
            self.embeddings_matrix = np.array(embeddings)
            logger.info(f"Vector store now contains {len(self.chunks)} chunks")

    def similarity_search(
        self, query_embedding: List[float], k: int = 5, threshold: float = 0.7
    ) -> List[DocumentChunk]:
        """Find similar document chunks using cosine similarity."""
        if not query_embedding or self.embeddings_matrix is None:
            return []

        # Normalize query embedding
        query_vec = np.array(query_embedding).reshape(1, -1)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []
        query_vec = query_vec / query_norm

        # Calculate cosine similarities
        chunk_norms = np.linalg.norm(self.embeddings_matrix, axis=1)
        valid_indices = chunk_norms > 0

        if not np.any(valid_indices):
            return []

        similarities = np.zeros(len(self.chunks))
        similarities[valid_indices] = np.dot(
            self.embeddings_matrix[valid_indices]
            / chunk_norms[valid_indices].reshape(-1, 1),
            query_vec.T,
        ).flatten()

        # Filter by threshold and get top-k
        valid_results = similarities >= threshold
        if not np.any(valid_results):
            return []

        top_indices = np.argsort(similarities)[::-1]
        top_indices = top_indices[similarities[top_indices] >= threshold][:k]

        return [self.chunks[i] for i in top_indices]

    def clear_index(self) -> None:
        """Clear the vector store."""
        self.chunks = []
        self.embeddings_matrix = None


class ProductInformationService:
    def __init__(self, data_directory: str = "./data"):
        self.data_directory = Path(data_directory)
        self.products: Dict[str, ProductInfo] = {}
        self.vector_store = VectorStoreService()

    def load_products(self) -> List[ProductInfo]:
        """Load products from data directory."""
        products = []
        products_dir = self.data_directory / "products"

        if not products_dir.exists():
            logger.warning(f"Products directory not found: {products_dir}")
            return products

        for txt_file in products_dir.glob("*.txt"):
            try:
                product = self._parse_product_file(txt_file)
                if product:
                    products.append(product)
                    self.products[product.product_id] = product

            except Exception as e:
                logger.error(f"Error loading product from {txt_file}: {e}")

        logger.info(f"Loaded {len(products)} products")
        return products

    def _parse_product_file(self, file_path: Path) -> Optional[ProductInfo]:
        """Parse a product text file into ProductInfo object."""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract product_id from filename
            product_id = file_path.stem

            # Simple parsing - in a real implementation, this would be more sophisticated
            lines = content.strip().split("\n")

            # Default values
            data = {
                "product_id": product_id,
                "name": product_id.replace("-", " ").title(),
                "alcohol_percentage": 5.0,
                "ibu": 30,
                "style": "Unknown",
                "flavor_profile": content[:200] + "..."
                if len(content) > 200
                else content,
                "ingredients": ["Water", "Malt", "Hops", "Yeast"],
                "recipe": content,
                "backstory": content,
                "ai_theme": "AI-inspired brewing",
                "brewing_notes": "Traditional brewing methods",
                "serving_temp_min": 38,
                "serving_temp_max": 45,
                "storage_instructions": "Store in cool, dry place",
                "shelf_life_days": 365,
                "available_sizes": ["12oz", "16oz"],
                "food_pairings": ["Various foods"],
                "awards": [],
            }

            # Try to extract structured data from content
            for line in lines:
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower().replace(" ", "_")
                    value = value.strip()

                    if key == "name":
                        data["name"] = value
                    elif key == "style":
                        data["style"] = value
                    elif key == "alcohol_percentage" or key == "abv":
                        try:
                            data["alcohol_percentage"] = float(value.rstrip("%"))
                        except ValueError:
                            pass
                    elif key == "ibu":
                        try:
                            data["ibu"] = int(value)
                        except ValueError:
                            pass

            return ProductInfo(**data)

        except Exception as e:
            logger.error(f"Error parsing product file {file_path}: {e}")
            return None

    def index_products(self, products: List[ProductInfo]) -> None:
        """Index products for RAG search."""
        chunks = []

        for product in products:
            # Create chunks from product content
            content_parts = [
                f"Name: {product.name}",
                f"Style: {product.style}",
                f"Flavor Profile: {product.flavor_profile}",
                f"Ingredients: {', '.join(product.ingredients)}",
                f"Recipe: {product.recipe}",
                f"Backstory: {product.backstory}",
                f"AI Theme: {product.ai_theme}",
                f"Brewing Notes: {product.brewing_notes}",
                f"Food Pairings: {', '.join(product.food_pairings)}",
            ]

            full_content = " ".join(content_parts)

            # Split into chunks (300 characters with 75 character overlap)
            chunk_size = 300
            overlap = 75

            for i in range(0, len(full_content), chunk_size - overlap):
                chunk_text = full_content[i : i + chunk_size]
                if not chunk_text.strip():
                    continue

                # Generate embedding for chunk
                embedding = self.vector_store.get_embedding(chunk_text)
                if not embedding:
                    continue

                chunk = DocumentChunk(
                    chunk_id=f"{product.product_id}_{i}",
                    product_id=product.product_id,
                    content=chunk_text,
                    embedding=embedding,
                    metadata={
                        "product_name": product.name,
                        "style": product.style,
                        "chunk_start": i,
                    },
                )
                chunks.append(chunk)

        self.vector_store.add_documents(chunks)
        logger.info(f"Indexed {len(chunks)} chunks for {len(products)} products")

    def search_products_rag(
        self, query: str, max_results: int = 5
    ) -> List[ProductSearchResult]:
        """Search products using RAG pipeline."""
        time.time()

        # Generate query embedding
        query_embedding = self.vector_store.get_embedding(query)
        if not query_embedding:
            return []

        # Search similar chunks
        similar_chunks = self.vector_store.similarity_search(
            query_embedding,
            k=max_results * 3,  # Get more chunks to aggregate by product
        )

        # Aggregate by product
        product_scores: Dict[str, List[float]] = {}
        product_content: Dict[str, List[str]] = {}

        for chunk in similar_chunks:
            if chunk.product_id not in product_scores:
                product_scores[chunk.product_id] = []
                product_content[chunk.product_id] = []

            # Calculate relevance score (cosine similarity)
            query_vec = np.array(query_embedding)
            chunk_vec = np.array(chunk.embedding)

            # Normalize vectors
            query_norm = np.linalg.norm(query_vec)
            chunk_norm = np.linalg.norm(chunk_vec)

            if query_norm > 0 and chunk_norm > 0:
                similarity = np.dot(query_vec, chunk_vec) / (query_norm * chunk_norm)
                product_scores[chunk.product_id].append(similarity)
                product_content[chunk.product_id].append(chunk.content[:100] + "...")

        # Create results
        results = []
        for product_id, scores in product_scores.items():
            if product_id in self.products:
                avg_score = np.mean(scores)
                result = ProductSearchResult(
                    product_id=product_id,
                    name=self.products[product_id].name,
                    relevance_score=float(avg_score),
                    matched_content=" | ".join(product_content[product_id][:2]),
                )
                results.append(result)

        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:max_results]

    def get_product_by_id(self, product_id: str) -> Optional[ProductInfo]:
        """Get specific product by ID."""
        return self.products.get(product_id)

    def reindex_products(self) -> bool:
        """Reload and reindex all products."""
        try:
            self.vector_store.clear_index()
            self.products = {}
            products = self.load_products()
            if products:
                self.index_products(products)
            return True
        except Exception as e:
            logger.error(f"Error reindexing products: {e}")
            return False


class OrderQueryService:
    def __init__(self, data_directory: str = "./data"):
        self.data_directory = Path(data_directory)
        self.db_connection: Optional[duckdb.DuckDBPyConnection] = None
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.llm_model = os.getenv("LLM_MODEL", "qwen3:1.7b")

    def initialize_database(self) -> None:
        """Initialize DuckDB database."""
        try:
            self.db_connection = duckdb.connect(":memory:")

            # Create tables
            self.db_connection.execute("""
                CREATE TABLE orders (
                    id VARCHAR PRIMARY KEY,
                    customer VARCHAR,
                    status VARCHAR,
                    ship_date DATE,
                    expected_ship DATE,
                    tracking VARCHAR
                );
            """)

            self.db_connection.execute("""
                CREATE TABLE order_items (
                    order_id VARCHAR,
                    product VARCHAR,
                    quantity INTEGER,
                    unit VARCHAR,
                    FOREIGN KEY (order_id) REFERENCES orders(id)
                );
            """)

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def load_orders_from_csv(self, csv_path: Optional[str] = None) -> None:
        """Load orders from CSV file."""
        if not csv_path:
            csv_path = str(self.data_directory / "orders.csv")

        try:
            if not Path(csv_path).exists():
                logger.warning(f"Orders CSV file not found: {csv_path}")
                return

            # Load CSV into DuckDB
            if self.db_connection is not None:
                self.db_connection.execute(f"""
                    CREATE TEMP TABLE temp_orders AS
                    SELECT * FROM read_csv_auto('{csv_path}')
                """)

            # Process and insert data (this would need to be customized based on CSV structure)
            # For now, create some sample data
            self._create_sample_orders()

            logger.info("Orders loaded successfully")

        except Exception as e:
            logger.error(f"Error loading orders: {e}")

    def _create_sample_orders(self) -> None:
        """Create sample orders for demo purposes."""
        sample_orders = [
            ("ORD-001", "Alice Smith", "shipped", "2024-01-15", "2024-01-20", "TRK123"),
            ("ORD-002", "Bob Johnson", "pending", None, "2024-02-01", None),
            (
                "ORD-003",
                "Carol Davis",
                "delivered",
                "2024-01-10",
                "2024-01-15",
                "TRK456",
            ),
        ]

        if self.db_connection is not None:
            for order_data in sample_orders:
                self.db_connection.execute(
                    """
                    INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)
                """,
                    order_data,
                )

            sample_items = [
                ("ORD-001", "Neural Network IPA", 2, "bottles"),
                ("ORD-001", "Gradient Descent Lager", 1, "bottle"),
                ("ORD-002", "Transformer Stout", 3, "bottles"),
                ("ORD-003", "Machine Learning Wheat", 1, "bottle"),
            ]

            for item_data in sample_items:
                self.db_connection.execute(
                    """
                    INSERT INTO order_items VALUES (?, ?, ?, ?)
                """,
                    item_data,
                )

    def generate_sql_with_llm(self, question: str, schema_context: str) -> str:
        """Generate SQL query from natural language using LLM."""
        try:
            prompt = f"""You are a SQL expert. Convert this natural language question to a SQL query.

Database Schema:
{schema_context}

Question: {question}

Generate only a SELECT query. Do not include explanations.
Return only valid DuckDB SQL syntax.

SQL Query:"""

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.llm_model,
                        "prompt": prompt,
                        "stream": False,
                        "think": False,
                    },
                )
                response.raise_for_status()
                result = response.json()

                sql_query = result.get("response", "").strip()

                # Clean up the response
                if sql_query.startswith("```sql"):
                    sql_query = sql_query[6:]
                if sql_query.endswith("```"):
                    sql_query = sql_query[:-3]

                sql_query = sql_query.strip()

                return sql_query

        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return ""

    def validate_sql_query(self, sql: str) -> bool:
        """Validate SQL query for safety."""
        sql_lower = sql.lower().strip()

        # Only allow SELECT queries
        if not sql_lower.startswith("select"):
            return False

        # Block dangerous keywords
        dangerous_keywords = [
            "drop",
            "delete",
            "update",
            "insert",
            "create",
            "alter",
            "truncate",
        ]
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                return False

        return True

    def execute_order_query(self, sql: str) -> List[Order]:
        """Execute SQL query and return Order objects."""
        try:
            if not self.validate_sql_query(sql):
                logger.error("Invalid SQL query")
                return []

            if self.db_connection is None:
                logger.error("Database connection not initialized")
                return []

            result = self.db_connection.execute(sql).fetchall()
            columns = (
                [desc[0] for desc in self.db_connection.description]
                if self.db_connection.description
                else []
            )

            orders = []
            for row in result:
                row_dict = dict(zip(columns, row))

                # Convert to Order object (this is simplified)
                order = Order(
                    id=str(row_dict.get("id", "")),
                    customer=str(row_dict.get("customer", "")),
                    status=str(row_dict.get("status", "")),
                    items=[],  # Would need to fetch items separately
                    ship_date=str(row_dict.get("ship_date", ""))
                    if row_dict.get("ship_date")
                    else None,
                    expected_ship=str(row_dict.get("expected_ship", ""))
                    if row_dict.get("expected_ship")
                    else None,
                    tracking=str(row_dict.get("tracking", ""))
                    if row_dict.get("tracking")
                    else None,
                )
                orders.append(order)

            return orders

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """Get specific order by ID."""
        try:
            orders = self.execute_order_query(
                f"SELECT * FROM orders WHERE id = '{order_id}'"
            )
            return orders[0] if orders else None
        except Exception:
            return None

    def get_schema_context(self) -> str:
        """Get database schema for LLM context."""
        return """
Tables:
- orders: id (VARCHAR), customer (VARCHAR), status (VARCHAR), ship_date (DATE), expected_ship (DATE), tracking (VARCHAR)
- order_items: order_id (VARCHAR), product (VARCHAR), quantity (INTEGER), unit (VARCHAR)
        """
