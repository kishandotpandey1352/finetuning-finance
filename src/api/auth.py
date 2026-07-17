import os

from fastapi import Header, HTTPException, status


DEFAULT_DEV_API_KEY = "dev-finance-api-key"


def get_api_key() -> str:
    return os.getenv("FINANCE_API_KEY", DEFAULT_DEV_API_KEY)


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    expected_api_key = get_api_key()

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )

    if x_api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )