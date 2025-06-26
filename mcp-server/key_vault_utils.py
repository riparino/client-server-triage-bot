"""
Utility functions for working with Azure Key Vault.
"""

import os
import logging
import functools
from typing import Any, Optional, Dict

try:
    from azure.identity import ManagedIdentityCredential, DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    from azure.core.exceptions import ResourceNotFoundError
except ImportError:
    logging.warning("Azure Key Vault packages not installed. Key Vault functionality will not be available.")
    ManagedIdentityCredential = None
    DefaultAzureCredential = None
    SecretClient = None
    ResourceNotFoundError = Exception

# Configuration
KEY_VAULT_NAME = os.environ.get("KEY_VAULT_NAME")
USE_KEY_VAULT = os.environ.get("USE_KEY_VAULT", "true").lower() == "true"

# Cache for Key Vault secrets
_secret_cache: Dict[str, str] = {}

@functools.lru_cache(maxsize=1)
def get_key_vault_client() -> Optional[Any]:
    """
    Get a Key Vault client using Managed Identity.
    Uses caching to avoid creating a new client for every request.
    """
    if not USE_KEY_VAULT or not KEY_VAULT_NAME or not SecretClient:
        return None
    
    try:
        # Use Managed Identity to access Key Vault
        credential = ManagedIdentityCredential()
        key_vault_url = f"https://{KEY_VAULT_NAME}.vault.azure.net"
        return SecretClient(vault_url=key_vault_url, credential=credential)
    except Exception as e:
        logging.error(f"Failed to create Key Vault client: {str(e)}")
        try:
            # Fall back to DefaultAzureCredential
            credential = DefaultAzureCredential()
            key_vault_url = f"https://{KEY_VAULT_NAME}.vault.azure.net"
            return SecretClient(vault_url=key_vault_url, credential=credential)
        except Exception as e:
            logging.error(f"Failed to create Key Vault client with fallback: {str(e)}")
            return None

def get_secret(secret_name: str, default_value: str = "") -> str:
    """
    Get a secret from Azure Key Vault.
    Uses caching to avoid unnecessary API calls.
    
    Args:
        secret_name: The name of the secret in Key Vault
        default_value: Default value if secret cannot be retrieved
        
    Returns:
        The secret value or the default value
    """
    # Check cache first
    if secret_name in _secret_cache:
        return _secret_cache[secret_name]
    
    # If Key Vault is not configured, return default
    if not USE_KEY_VAULT or not KEY_VAULT_NAME:
        return default_value
    
    client = get_key_vault_client()
    if not client:
        return default_value
    
    try:
        # Get secret from Key Vault
        secret = client.get_secret(secret_name)
        # Cache the value
        _secret_cache[secret_name] = secret.value
        return secret.value
    except ResourceNotFoundError:
        logging.warning(f"Secret {secret_name} not found in Key Vault")
        return default_value
    except Exception as e:
        logging.error(f"Error retrieving {secret_name} from Key Vault: {str(e)}")
        return default_value

def set_secret(secret_name: str, secret_value: str) -> bool:
    """
    Set a secret in Azure Key Vault.
    
    Args:
        secret_name: The name of the secret in Key Vault
        secret_value: The value to set
        
    Returns:
        True if successful, False otherwise
    """
    if not USE_KEY_VAULT or not KEY_VAULT_NAME:
        return False
    
    client = get_key_vault_client()
    if not client:
        return False
    
    try:
        # Set secret in Key Vault
        client.set_secret(secret_name, secret_value)
        # Update cache
        _secret_cache[secret_name] = secret_value
        return True
    except Exception as e:
        logging.error(f"Error setting {secret_name} in Key Vault: {str(e)}")
        return False

def delete_secret(secret_name: str) -> bool:
    """
    Delete a secret from Azure Key Vault.
    
    Args:
        secret_name: The name of the secret in Key Vault
        
    Returns:
        True if successful, False otherwise
    """
    if not USE_KEY_VAULT or not KEY_VAULT_NAME:
        return False
    
    client = get_key_vault_client()
    if not client:
        return False
    
    try:
        # Delete secret from Key Vault
        client.begin_delete_secret(secret_name)
        # Remove from cache
        if secret_name in _secret_cache:
            del _secret_cache[secret_name]
        return True
    except Exception as e:
        logging.error(f"Error deleting {secret_name} from Key Vault: {str(e)}")
        return False

def clear_cache() -> None:
    """Clear the secret cache."""
    _secret_cache.clear()
