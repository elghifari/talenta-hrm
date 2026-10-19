import os

import dj_database_url

from .base import *  # noqa: F403

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-synthetic-data-only-not-for-deployment")
DEBUG = True
FRONTEND_DEV_ENABLED = True
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"  # noqa: F405
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", "postgresql://hrm_dev@127.0.0.1:55439/hrm_dev")
    )
}
