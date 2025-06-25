"""
Azure Authentication Helper
Handles authentication to Azure using CLI-based approach with z-account privileges.
"""

import subprocess
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AzureAuthHelper:
    """Helper class for Azure authentication and token management."""
    
    def __init__(self):
        self._cached_tokens = {}
        self._token_expiry = {}
    
    def check_authentication(self) -> bool:
        """Check if user is authenticated with Azure CLI."""
        try:
            result = subprocess.run(
                ['az', 'account', 'show'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                logger.info(f"Authenticated as: {account_info.get('user', {}).get('name', 'Unknown')}")
                return True
            else:
                logger.warning("Not authenticated with Azure CLI")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Azure CLI authentication check timed out")
            return False
        except Exception as e:
            logger.error(f"Error checking Azure CLI authentication: {str(e)}")
            return False
    
    def get_access_token(self, tenant_id: Optional[str] = None, resource: str = "https://management.azure.com/") -> Optional[str]:
        """Get access token for Azure API calls."""
        try:
            # Check cache first
            cache_key = f"{tenant_id}_{resource}"
            if self._is_token_valid(cache_key):
                return self._cached_tokens[cache_key]
            
            cmd = ['az', 'account', 'get-access-token', '--resource', resource]
            if tenant_id:
                cmd.extend(['--tenant', tenant_id])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                token_info = json.loads(result.stdout)
                access_token = token_info.get('accessToken')
                expires_on = token_info.get('expiresOn')
                
                # Cache the token
                self._cached_tokens[cache_key] = access_token
                if expires_on:
                    # Parse expiry time and cache it
                    expiry_time = datetime.fromisoformat(expires_on.replace('Z', '+00:00'))
                    self._token_expiry[cache_key] = expiry_time
                
                return access_token
            else:
                logger.error(f"Failed to get access token: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def _is_token_valid(self, cache_key: str) -> bool:
        """Check if cached token is still valid."""
        if cache_key not in self._cached_tokens:
            return False
        
        if cache_key not in self._token_expiry:
            return True  # Assume valid if no expiry info
        
        # Check if token expires within next 5 minutes
        now = datetime.utcnow()
        buffer_time = timedelta(minutes=5)
        
        return self._token_expiry[cache_key] > (now + buffer_time)
    
    def get_available_tenants(self) -> List[Dict]:
        """Get list of available tenants from Azure CLI."""
        try:
            result = subprocess.run(
                ['az', 'account', 'list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                accounts = json.loads(result.stdout)
                tenants = []
                
                for account in accounts:
                    tenant_info = {
                        'tenant_id': account.get('tenantId'),
                        'tenant_name': account.get('tenantDisplayName', account.get('name', 'Unknown')),
                        'subscription_id': account.get('id'),
                        'subscription_name': account.get('name'),
                        'state': account.get('state'),
                        'is_default': account.get('isDefault', False)
                    }
                    tenants.append(tenant_info)
                
                return tenants
            else:
                logger.error(f"Failed to list tenants: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting available tenants: {str(e)}")
            return []
    
    def switch_tenant(self, tenant_id: str) -> bool:
        """Switch to a specific tenant context."""
        try:
            result = subprocess.run(
                ['az', 'account', 'set', '--subscription', tenant_id],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Switched to tenant: {tenant_id}")
                return True
            else:
                logger.error(f"Failed to switch tenant: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error switching tenant: {str(e)}")
            return False
    
    def clear_token_cache(self):
        """Clear cached tokens."""
        self._cached_tokens.clear()
        self._token_expiry.clear()
        logger.info("Token cache cleared")