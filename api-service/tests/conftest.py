import os

# Must be set before any src.* import triggers Config() instantiation
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASS", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("AMQP_USER", "guest")
os.environ.setdefault("AMQP_PASSWORD", "guest")
os.environ.setdefault("AMQP_HOST", "localhost")
os.environ.setdefault("AMQP_PORT", "5672")
