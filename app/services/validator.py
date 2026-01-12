import httpx
from app.config import settings


class JobValidator:
    @staticmethod
    async def validate_target(url: str) -> None:
        """
        Validate target URL is reachable.
        
        Note: We allow 4xx errors (403, 401, etc) because the target might block
        validation requests but still be scrapeable with proper headers/sessions.
        Only reject on connection errors or 5xx server errors.
        """
        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "scraper-platform/1.0"})
                # Only reject on 5xx server errors
                # Allow 4xx (including 403, 401) since target might block validator
                if resp.status_code >= 500:
                    raise ValueError(f"Target server error: HTTP {resp.status_code}")
        except httpx.RequestError as e:
            raise ValueError(f"Target unreachable: {str(e)}")

    @staticmethod
    def validate_fields(fields: list[str]) -> None:
        if not fields:
            raise ValueError("At least one field is required")
        if len(set(fields)) != len(fields):
            raise ValueError("Duplicate field names detected")
        for f in fields:
            if not f or not f.strip():
                raise ValueError("Empty field name detected")
