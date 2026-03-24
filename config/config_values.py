import os


class ConfigValues:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://Nakshatra:parle123@localhost:5432/scraping_airflow",
    )
    PRODUCT_DETAILS_TABLE = "product_details"

    POSTGRES_CONN_ID = os.getenv("POSTGRES_CONN_ID", "product_db")

    STEALTH_SCRIPT = """() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en'] });
    Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
    window.chrome = { runtime: {} };
    }"""
