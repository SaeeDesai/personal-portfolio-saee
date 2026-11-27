import os
from urllib.parse import urlsplit

from argon2 import extract_parameters
from dotenv import load_dotenv

load_dotenv()


def validate_production_config():
    environment = os.getenv("APP_ENV", "production")

    if environment not in {"development", "production"}:
        raise RuntimeError("Invalid APP_ENV")

    if environment == "development":
        return

    required_variables = (
        "DATABASE_URL",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD_HASH",
        "DASHBOARD_ORIGIN",
    )

    for variable in required_variables:
        if not os.getenv(variable, "").strip():
            raise RuntimeError(
                f"Missing required configuration: {variable}"
            )

    origin = urlsplit(os.environ["DASHBOARD_ORIGIN"])

    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.username
        or origin.password
        or origin.path
        or origin.query
        or origin.fragment
    ):
        raise RuntimeError(
            "Production requires a valid HTTPS dashboard origin"
        )

    try:
        extract_parameters(os.environ["ADMIN_PASSWORD_HASH"])
    except Exception:
        raise RuntimeError(
            "Invalid administrator password hash"
        ) from None