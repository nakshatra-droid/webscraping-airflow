INSERT_SCRAPING_RUN = """
INSERT INTO scraping_metadata
    (id, total_products_attempted, valid_products, invalid_products,
     start_time, is_fallback_run, created_at, updated_at)
VALUES
    (%s, 0, 0, 0, %s, true, %s, %s)
"""

UPDATE_SCRAPING_RUN = """
UPDATE scraping_metadata
   SET total_products_attempted = %s,
       valid_products = %s,
       invalid_products = %s,
       end_time = %s,
       updated_at = %s
 WHERE id = %s
"""

UPSERT_PRODUCT = """
INSERT INTO products
    (id, model_number, brand, series, processor, ram, storage,
     screen_size, graphic_processor, colour,
     embedding_status, created_at, updated_at)
VALUES
    (gen_random_uuid(), %s, %s, %s, %s,
     %s, %s, %s, %s, %s,
     'PENDING', %s, %s)
ON CONFLICT (model_number) DO UPDATE
    SET brand = EXCLUDED.brand,
        series = EXCLUDED.series,
        processor = EXCLUDED.processor,
        ram = EXCLUDED.ram,
        storage = EXCLUDED.storage,
        screen_size = EXCLUDED.screen_size,
        graphic_processor = EXCLUDED.graphic_processor,
        colour = EXCLUDED.colour,
        updated_at = EXCLUDED.updated_at
RETURNING id
"""

UPSERT_PRODUCT_DETAILS_TEMPLATE = """
INSERT INTO {product_details_table}
    (id, product_id, source, run_id,
     price, discount, rating, review_count,
     url, image_url, scraped_at, updated_at)
VALUES
    (gen_random_uuid(), %s, %s, %s,
     %s, %s, %s, %s,
     %s, %s, %s, %s)
ON CONFLICT ON CONSTRAINT product_details_product_id_source_key
DO UPDATE
    SET price = EXCLUDED.price,
        discount = EXCLUDED.discount,
        rating = EXCLUDED.rating,
        review_count = EXCLUDED.review_count,
        image_url = EXCLUDED.image_url,
        run_id = EXCLUDED.run_id,
        scraped_at = EXCLUDED.scraped_at,
        updated_at = EXCLUDED.updated_at
"""

FETCH_FALLBACK_ACTIVITY_BATCH = """
SELECT id, product_url, COALESCE(retry_count, 0) AS retry_count
FROM activity_logs
WHERE deleted_at IS NULL
  AND human_review_flag IS NOT TRUE
  AND COALESCE(retry_count, 0) < 3
  AND product_url IS NOT NULL
  AND lower(product_url) LIKE %s
ORDER BY created_at ASC
LIMIT %s
"""

UPDATE_ACTIVITY_RETRY = """
UPDATE activity_logs
SET retry_count = LEAST(COALESCE(retry_count, 0) + 1, 3),
    human_review_flag = CASE
        WHEN COALESCE(retry_count, 0) + 1 >= 3 THEN true
        ELSE COALESCE(human_review_flag, false)
    END,
    updated_at = %s
WHERE id = %s
"""

DELETE_ACTIVITY_BY_ID = """
DELETE FROM activity_logs
WHERE id = %s
"""
