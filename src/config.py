import os
from pathlib import Path


# ==================================================
# APPLICATION MODE
# ==================================================

APP_MODE = (
    os.getenv(
        "IBERIAN_APP_MODE",
        "local",
    )
    .strip()
    .lower()
)


if APP_MODE not in {
    "local",
    "public",
}:
    raise ValueError(
        "IBERIAN_APP_MODE must be "
        "'local' or 'public'."
    )


IS_PUBLIC = (
    APP_MODE == "public"
)


# ==================================================
# DATABASE PATHS
# ==================================================

LOCAL_DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


PUBLIC_DATABASE_PATH = (
    Path("deployment")
    / "iberian_energy_public.db"
)


default_database_path = (
    PUBLIC_DATABASE_PATH
    if IS_PUBLIC
    else LOCAL_DATABASE_PATH
)


DATABASE_PATH = Path(
    os.getenv(
        "IBERIAN_DB_PATH",
        str(default_database_path),
    )
)


# ==================================================
# WEB FILES
# ==================================================

LOCAL_WEB_PATH = (
    Path("src")
    / "web"
    / "index.html"
)


PUBLIC_WEB_PATH = (
    Path("src")
    / "web"
    / "public_index.html"
)


WEB_PATH = (
    PUBLIC_WEB_PATH
    if IS_PUBLIC
    else LOCAL_WEB_PATH
)