"""Optional AI configuration. Never required by the MVP startup."""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AISettings:
    enabled: bool = False
    api_key: str = field(default='', repr=False)
    model: str = ''
    base_url: str = 'https://apihub.agnes-ai.com/v1'
    timeout: int = 45
    user_limit: int = 20
    global_limit: int = 100
    concurrency: int = 2
    allowed_resources: frozenset[int] = frozenset()
    allow_all_resources: bool = False

    def allows_resource(self, resource_id):
        return self.allow_all_resources or resource_id in self.allowed_resources

    @classmethod
    def from_environment(cls):
        enabled = os.environ.get('AI_ASSISTANT_ENABLED', 'false').lower() == 'true'
        if not enabled:
            return cls()
        try:
            def number(name, default, upper):
                value = int(os.environ.get(name, default))
                if not 1 <= value <= upper:
                    raise ValueError()
                return value
            base = os.environ.get('AGNES_BASE_URL', cls.base_url).rstrip('/')
            if base != cls.base_url:
                raise ValueError()
            model = os.environ.get('AGNES_MODEL', '').strip()
            if len(model) > 100 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-._' for c in model):
                raise ValueError()
            environment = os.environ.get('APP_ENV', 'production').strip().lower()
            if environment not in ('development', 'production'):
                raise ValueError()
            raw_ids = os.environ.get('AI_ALLOWED_RESOURCE_IDS', '').strip()
            wildcard = raw_ids == '*'
            if wildcard and environment != 'development':
                raise ValueError()
            ids = frozenset() if wildcard else frozenset(int(v.strip()) for v in raw_ids.split(',') if v.strip())
            if any(v < 1 or v > 18446744073709551615 for v in ids):
                raise ValueError()
            return cls(True, os.environ.get('AGNES_API_KEY', ''), model, base,
                       number('AI_TOTAL_TIMEOUT_SECONDS', '45', 45),
                       number('AI_USER_DAILY_REQUEST_LIMIT', '100' if environment=='development' else '20', 100),
                       number('AI_GLOBAL_DAILY_REQUEST_LIMIT', '1000' if environment=='development' else '100', 1000),
                       number('AI_MAX_CONCURRENT_REQUESTS', '2', 2), ids, wildcard)
        except (ValueError, TypeError):
            raise RuntimeError('AI configuration unavailable') from None

    @property
    def ready(self):
        return self.enabled and bool(self.api_key.strip()) and bool(self.model)
