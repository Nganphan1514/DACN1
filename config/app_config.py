import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


SECRET_KEY = os.getenv("SECRET_KEY", "dacn1-secret-key")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dacn1-jwt-secret-key")
DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

# Supabase PostgreSQL connection string
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Legacy MySQL XAMPP settings (chi dung cho script migrate du lieu)
MYSQL_HOST = os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost"))
MYSQL_PORT = int(os.getenv("MYSQL_PORT", os.getenv("DB_PORT", "3306")))
MYSQL_USER = os.getenv("MYSQL_USER", os.getenv("DB_USER", "root"))
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "he_thong_tai_xe"))

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dacn1-internal-alert-key")
