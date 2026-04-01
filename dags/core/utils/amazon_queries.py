INSERT_SCRAPING_RUN = """
INSERT INTO scraping_metadata
	(id, total_products_attempted, valid_products, invalid_products,
	 start_time, is_fallback_run, created_at, updated_at)
VALUES
	(%s, 0, 0, 0, %s, false, %s, %s)
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
ON CONFLICT (product_id, source) DO UPDATE
	SET price = EXCLUDED.price,
		discount = EXCLUDED.discount,
		rating = EXCLUDED.rating,
		review_count = EXCLUDED.review_count,
		image_url = EXCLUDED.image_url,
		run_id = EXCLUDED.run_id,
		scraped_at = EXCLUDED.scraped_at,
		updated_at = EXCLUDED.updated_at
"""

INSERT_ACTIVITY_LOG = """
INSERT INTO activity_logs
	(id, run_id, activity_type, product_data, product_url,
	 retry_count, human_review_flag, created_at, updated_at)
VALUES
	(gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s)
"""

FETCH_PRODUCT_URLS_TEMPLATE = """
SELECT url FROM {product_details_table} WHERE source = %s
"""

FETCH_ACTIVITY_URLS = """
SELECT product_url FROM activity_logs WHERE product_url IS NOT NULL
"""
