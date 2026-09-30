import os

import dj_database_url

from .base import *  # noqa: F403

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-synthetic-data-only-not-for-deployment")
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", "postgresql://hrm_dev@127.0.0.1:55439/hrm_dev")
    )
}
