"""Enterprise Secrets & Configuration Management Module.

Supports multi-tier secret resolution:
1. HashiCorp Vault (or Cloud Secret Manager) if VAULT_ADDR and VAULT_TOKEN configured
2. Docker / Kubernetes Secrets mounted at /run/secrets/
3. Secure Environment Variables (.env / system runtime)
Provides immutable audit masking to prevent key exposure in telemetry logs.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class SecretsProvider:
    """Base secrets provider interface."""
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        raise NotImplementedError


class DockerSecretsProvider(SecretsProvider):
    """Retrieves secrets injected into container at /run/secrets/."""
    def __init__(self, secrets_dir: str = "/run/secrets"):
        self.secrets_dir = Path(secrets_dir)

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        secret_file = self.secrets_dir / key
        if secret_file.exists() and secret_file.is_file():
            try:
                return secret_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return default


class VaultSecretsProvider(SecretsProvider):
    """Retrieves secrets dynamically from HashiCorp Vault KV v2 API."""
    def __init__(self, vault_addr: str, vault_token: str, mount_point: str = "secret", path: str = "clinsafe"):
        self.vault_addr = vault_addr.rstrip("/")
        self.vault_token = vault_token
        self.mount_point = mount_point
        self.path = path
        self._cache: Dict[str, str] = {}
        self._loaded = False

    def _fetch_vault_secrets(self):
        if self._loaded:
            return
        import requests
        url = f"{self.vault_addr}/v1/{self.mount_point}/data/{self.path}"
        headers = {"X-Vault-Token": self.vault_token}
        try:
            res = requests.get(url, headers=headers, timeout=3.0)
            if res.status_code == 200:
                data = res.json().get("data", {}).get("data", {})
                self._cache = data
                self._loaded = True
        except Exception:
            pass

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        try:
            self._fetch_vault_secrets()
            return self._cache.get(key, default)
        except Exception:
            return default


class EnvironmentSecretsProvider(SecretsProvider):
    """Retrieves secrets from secure process environment variables."""
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(key, default)


class SecretsManager:
    """Composite secrets manager with fallback hierarchy."""

    def __init__(self):
        self.providers: list[SecretsProvider] = []

        # 1. Check for HashiCorp Vault configuration
        vault_addr = os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT_TOKEN")
        if vault_addr and vault_token:
            self.providers.append(VaultSecretsProvider(vault_addr, vault_token))

        # 2. Check for Docker container secrets
        docker_secrets_path = os.getenv("DOCKER_SECRETS_PATH", "/run/secrets")
        if Path(docker_secrets_path).exists():
            self.providers.append(DockerSecretsProvider(docker_secrets_path))

        # 3. Default to runtime environment
        self.providers.append(EnvironmentSecretsProvider())

    def get(self, key: str, default: Optional[str] = "") -> str:
        """Resolves secret value across registered providers."""
        for provider in self.providers:
            val = provider.get_secret(key, None)
            if val is not None and val != "":
                return val
        return default or ""

    @staticmethod
    def mask_secret(secret_value: str) -> str:
        """Returns safe masked preview of key for audit logs."""
        if not secret_value:
            return "[NOT SET]"
        if len(secret_value) <= 6:
            return "******"
        return f"{secret_value[:3]}...{secret_value[-3:]}"


# Global singleton instance
secrets_manager = SecretsManager()
