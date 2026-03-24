INSERT_METADATA = """
INSERT INTO embedding_metadata
(id, model_name, status, total_attempted, success_count, failed_count, start_time, created_at, updated_at)
VALUES (%s, 'sentence-transformers/multi-qa-mpnet-base-dot-v1', 'RUNNING', 0, 0, 0, NOW(), NOW(), NOW())
"""

FETCH_PENDING_PRODUCTS = """
SELECT
    id,
    brand,
    series,
    processor,
    ram,
    storage,
    graphic_processor,
    colour
FROM products
WHERE embedding_status = 'PENDING'
LIMIT %s
"""

INSERT_EMBEDDING = """
INSERT INTO product_embeddings
(id, product_id, embedding_metadata_id, embedding, created_at, updated_at)
VALUES (%s,%s,%s,%s,NOW(),NOW())
"""

UPDATE_PRODUCT_STATUS = """
UPDATE products
SET embedding_status='COMPLETED',
    embedded_at=NOW()
WHERE id = ANY(%s::uuid[])
"""

UPDATE_METADATA = """
UPDATE embedding_metadata
SET total_attempted=%s,
    success_count=%s,
    failed_count=%s,
    status='COMPLETED',
    end_time=NOW(),
    updated_at=NOW()
WHERE id=%s
"""
