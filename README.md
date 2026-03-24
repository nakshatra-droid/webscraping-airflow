# Webscraping Airflow

Apache Airflow orchestration for product embedding generation using Ollama. Processes pending products from PostgreSQL database and generates semantic embeddings.

## Architecture

### TaskFlow DAG Structure

```
├── fetch_pending_products
│   └── create_embedding_run
│       ├── generate_embeddings
│       │   └── store_embeddings
│       │       └── finalize_embedding_run
```

**Each task is independently trackable in Airflow UI** for clear visibility of pipeline progress.

### Components

**Models** (`models/`)
- `products.py` - Product catalog with embedding metadata fields
- `product_embeddings.py` - Vector storage with pgvector HNSW indexing
- `embedding_metadata.py` - Run metadata tracking (success/failure counts, timing)

**Embedding Pipeline** (`embeddings/embedding_task.py`)
- `EmbeddingPipeline` - Class-based ETL pipeline
- Text construction from all product attributes (brand, series, processor, RAM, storage, etc.)
- Ollama integration for local embedding generation
- Batch processing with granular error handling

**DAG** (`dags/embedding_dag.py`)
- 5 TaskFlow tasks for clear step-by-step execution
- Automatic run scheduling (`@daily` by default)
- XCom data flow between tasks
- Result aggregation and status reporting

**Utilities** (`utils/`)
- `ollama_utils.py` - OllamaEmbeddingClient for API calls
- `constants.py` - Status enums (RUNNING, COMPLETED, FAILED)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your PostgreSQL connection and Ollama settings:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/products_db
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=llama3.2
EMBEDDING_BATCH_SIZE=10
EMBEDD_BATCH_LIMIT=100
```

### 3. Ensure Ollama is Running

```bash
ollama serve
# In another terminal:
ollama pull llama3.2
```

### 4. Initialize Airflow

```bash
export AIRFLOW_HOME=$(pwd)
airflow db init
```

### 5. Create Airflow User

```bash
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

### 6. Start Airflow Scheduler & Webserver

```bash
# Terminal 1: Scheduler
airflow scheduler

# Terminal 2: Webserver
airflow webserver --port 8080
```

## Usage

### Automatic Scheduling

DAG runs daily at **00:00 UTC** (configurable via `EMBEDDING_DAG_INTERVAL` in `.env`)

### Manual Trigger

```bash
airflow dags trigger embedding_pipeline_dag
```

### Monitor Progress

1. Visit http://localhost:8080
2. Navigate to "DAGs" > "embedding_pipeline_dag"
3. Click on latest DAG run to view task execution
4. Each task shows detailed logs and execution time

## Task Details

### Task 1: `fetch_pending_products`
- Queries database for products with `embedding_status = 'PENDING'`
- Respects batch limit (default: 100 products)
- Returns count and product IDs for downstream tracking

### Task 2: `create_embedding_run`
- Creates EmbeddingMetadata record with `status = 'RUNNING'`
- Assigned unique `run_id` for this batch
- Used to track success/failure metrics

### Task 3: `generate_embeddings`
- Builds comprehensive product text from: model_number, brand, series, processor, RAM, storage, screen_size, graphic_processor, colour
- Calls Ollama API: `POST /api/embed` with structured text
- Returns embedding vectors (768-dim by default)
- Logs progress every 10% of batch

### Task 4: `store_embeddings`
- Inserts ProductEmbeddings records with vectors to PostgreSQL
- Creates pgvector HNSW indexes for fast semantic search
- Updates product `embedding_status = 'COMPLETED'` / 'FAILED'
- Sets `embedded_at` timestamp

### Task 5: `finalize_embedding_run`
- Updates EmbeddingMetadata with final statistics
- Records success/failure counts and end_time
- Sets `status = 'COMPLETED'` or 'FAILED'

## Database Schema

### products
```sql
├── id (UUID, PK)
├── model_number (TEXT, UNIQUE)
├── brand, series, processor, ram, storage, screen_size, graphic_processor, colour
├── embedding_status ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')
├── embedded_at (TIMESTAMP)
└── created_at, updated_at, deleted_at
```

### product_embeddings
```sql
├── id (UUID, PK)
├── product_id (FK → products.id)
├── embedding_metadata_id (FK → embedding_metadata.id)
├── embedding (Vector(768), HNSW indexed)
└── created_at, updated_at, deleted_at
```

### embedding_metadata
```sql
├── id (UUID, PK)
├── model_name ('llama3.2')
├── total_attempted, success_count, failed_count
├── status ('RUNNING', 'COMPLETED', 'FAILED')
├── start_time, end_time
└── created_at, updated_at, deleted_at
```

## Configuration

### Ollama Settings

- `OLLAMA_HOST` - Ollama API endpoint (default: `http://localhost:11434`)
- `OLLAMA_EMBEDDING_MODEL` - Model name (default: `llama3.2`)
- `OLLAMA_EMBEDDING_VECTOR_SIZE` - Output dimension (default: 768)

### Pipeline Settings

- `EMBEDDING_BATCH_SIZE` - Products per second (default: 10)
- `EMBEDD_BATCH_LIMIT` - Max products per run (default: 100)
- `EMBEDDING_DAG_INTERVAL` - Cron schedule (default: `@daily`)

### Database Connection

- `DATABASE_URL` - PostgreSQL async connection string (required)
  - Format: `postgresql+asyncpg://user:password@host:port/dbname`
  - Must support async driver (asyncpg)

## Troubleshooting

### "No Ollama server at localhost:11434"

Ensure Ollama is running:
```bash
ollama serve
```

### "DuplicateObjectError" in ProductEmbeddings

HNSW index name conflict. Drop old index:
```sql
DROP INDEX IF EXISTS product_embeddings_embedding_hnsw_idx;
```

### "Product not found" in DAG logs

Verify products exist in database with embedding_status = 'PENDING':
```sql
SELECT COUNT(*) FROM products WHERE embedding_status = 'PENDING';
```

### Slow embeddings generation

- Reduce `EMBEDDING_BATCH_SIZE` if Ollama is throttled
- Ensure Ollama model is fully loaded: `ollama pull llama3.2`
- Check Ollama server load: `ollama ps`

## Performance Notes

- **Ollama latency**: ~0.5-2s per product text (depends on model and hardware)
- **Vector storage**: 768-dimensional embedding ≈ 6.1 KB per product
- **HNSW indexing**: ~1-2s per 1000 products
- **Recommended batch size**: 10-50 products per DAG run for stability

## Next Steps

1. Monitor first DAG run to validate:
   - Database connectivity
   - Ollama embedding generation
   - Vector storage in pgvector
   
2. Tune `EMBEDDING_BATCH_SIZE` based on Ollama performance

3. Set up Airflow alerting for failed runs (admin email config)

4. Add semantic search endpoints to FastAPI backend using stored embeddings