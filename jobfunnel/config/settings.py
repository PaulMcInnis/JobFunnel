"""Settings YAML Schema w/ validator using Pydantic"""

import ipaddress
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from jobfunnel.resources import (
    LOG_LEVEL_NAMES,
    DelayAlgorithm,
    Locale,
    Provider,
    Remoteness,
)
from jobfunnel.resources.defaults import (
    DEFAULT_COMPANY_BLOCK_LIST,
    DEFAULT_DELAY_ALGORITHM,
    DEFAULT_DELAY_MAX_DURATION,
    DEFAULT_DELAY_MIN_DURATION,
    DEFAULT_LOG_LEVEL_NAME,
    DEFAULT_MAX_LISTING_DAYS,
    DEFAULT_MAX_SCROLL_ITERATIONS,
    DEFAULT_PROVIDER_NAMES,
    DEFAULT_RANDOM_CONVERGING_DELAY,
    DEFAULT_RANDOM_DELAY,
    DEFAULT_REMOTENESS,
    DEFAULT_RETURN_SIMILAR_RESULTS,
    DEFAULT_SEARCH_RADIUS,
)


class ProxySettings(BaseModel):
    """Proxy configuration settings"""

    protocol: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = Field(default=None, ge=0)

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["http", "https"]:
            raise ValueError("protocol must be 'http' or 'https'")
        return v

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                ipaddress.IPv4Address(v)
            except Exception:
                raise ValueError("Not a valid IPv4 address")
        return v


class DelaySettings(BaseModel):
    """Delay configuration settings"""

    algorithm: str = DEFAULT_DELAY_ALGORITHM.name
    max_duration: float = Field(default=DEFAULT_DELAY_MAX_DURATION, ge=0)
    min_duration: float = Field(default=DEFAULT_DELAY_MIN_DURATION, ge=0)
    random: bool = DEFAULT_RANDOM_DELAY
    converging: bool = DEFAULT_RANDOM_CONVERGING_DELAY

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        valid_algorithms = [d.name for d in DelayAlgorithm]
        if v not in valid_algorithms:
            raise ValueError(f"algorithm must be one of {valid_algorithms}")
        return v


class SearchSettings(BaseModel):
    """Search configuration settings"""

    providers: List[str] = DEFAULT_PROVIDER_NAMES
    locale: str
    province_or_state: str
    city: str
    radius: int = Field(default=DEFAULT_SEARCH_RADIUS, ge=0)
    similar_results: bool = DEFAULT_RETURN_SIMILAR_RESULTS
    keywords: List[str]
    max_listing_days: int = Field(default=DEFAULT_MAX_LISTING_DAYS, ge=0)
    company_block_list: List[str] = Field(default_factory=lambda: list(DEFAULT_COMPANY_BLOCK_LIST))
    remoteness: str = DEFAULT_REMOTENESS.name
    max_scroll_iterations: int = Field(default=DEFAULT_MAX_SCROLL_ITERATIONS, ge=1)

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, v: List[str]) -> List[str]:
        valid_providers = [p.name for p in Provider]
        for provider in v:
            if provider not in valid_providers:
                raise ValueError(f"provider '{provider}' must be one of {valid_providers}")
        return v

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str) -> str:
        valid_locales = [locale.name for locale in Locale]
        if v not in valid_locales:
            raise ValueError(f"locale must be one of {valid_locales}")
        return v

    @field_validator("remoteness")
    @classmethod
    def validate_remoteness(cls, v: str) -> str:
        valid_remoteness = [r.name for r in Remoteness]
        if v not in valid_remoteness:
            raise ValueError(f"remoteness must be one of {valid_remoteness}")
        return v


class JobFunnelSettings(BaseModel):
    """Complete JobFunnel settings schema"""

    master_csv_file: str
    block_list_file: str
    cache_folder: str
    duplicates_list_file: str
    log_file: str
    no_scrape: bool = False
    log_level: str = DEFAULT_LOG_LEVEL_NAME
    search: SearchSettings
    delay: DelaySettings = Field(default_factory=DelaySettings)
    proxy: Optional[ProxySettings] = None

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        if v not in LOG_LEVEL_NAMES:
            raise ValueError(f"log_level must be one of {LOG_LEVEL_NAMES}")
        return v


class JobFunnelSettingsValidator:
    """Validator class that provides cerberus-like interface using Pydantic"""

    def __init__(self, schema: Dict[str, Any]) -> None:
        """Initialize with schema (kept for compatibility, but we use Pydantic models)"""
        self._schema = schema
        self._errors: List[str] = []

    def normalized(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply defaults to config dictionary, replacing None values with defaults"""
        # Create a copy to avoid modifying the original
        result = dict(config)

        def set_default(d: Dict[str, Any], key: str, default: Any) -> None:
            """Set default value if key is missing or None"""
            if key not in d or d[key] is None:
                d[key] = default

        # Apply top-level defaults
        set_default(result, "no_scrape", False)
        set_default(result, "log_level", DEFAULT_LOG_LEVEL_NAME)

        # Apply search defaults
        if "search" in result and result["search"] is not None:
            search = result["search"]
            set_default(search, "providers", DEFAULT_PROVIDER_NAMES)
            set_default(search, "radius", DEFAULT_SEARCH_RADIUS)
            set_default(search, "similar_results", DEFAULT_RETURN_SIMILAR_RESULTS)
            set_default(search, "max_listing_days", DEFAULT_MAX_LISTING_DAYS)
            set_default(search, "company_block_list", list(DEFAULT_COMPANY_BLOCK_LIST))
            set_default(search, "remoteness", DEFAULT_REMOTENESS.name)
            set_default(search, "max_scroll_iterations", DEFAULT_MAX_SCROLL_ITERATIONS)

        # Apply delay defaults
        if "delay" not in result or result["delay"] is None:
            result["delay"] = {}
        delay = result["delay"]
        set_default(delay, "algorithm", DEFAULT_DELAY_ALGORITHM.name)
        set_default(delay, "max_duration", DEFAULT_DELAY_MAX_DURATION)
        set_default(delay, "min_duration", DEFAULT_DELAY_MIN_DURATION)
        set_default(delay, "random", DEFAULT_RANDOM_DELAY)
        set_default(delay, "converging", DEFAULT_RANDOM_CONVERGING_DELAY)

        return result

    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate config against the schema"""
        self._errors = []
        try:
            JobFunnelSettings(**config)
            return True
        except Exception as e:
            self._errors = [str(e)]
            return False

    @property
    def errors(self) -> List[str]:
        """Return validation errors"""
        return self._errors


# Legacy schema kept for reference but not used by Pydantic
SETTINGS_YAML_SCHEMA: Dict[str, Any] = {}

# Create validator instance for backwards compatibility
SettingsValidator = JobFunnelSettingsValidator(SETTINGS_YAML_SCHEMA)
