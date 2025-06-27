"""
Azure authentication module using Microsoft Identity Web for Python.
Provides token validation and multi-tenant access through Azure Lighthouse delegated resource management.
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple, List
import json
import azure.functions as func
from microsoft_identity_web import ConfidentialClientApplication, ClaimsValidator, AuthError
from microsoft_identity_web.adapters import AzureFunctionsAuthAdapter

# Import Key Vault utilities
from key_vault_utils import get_secret

# Constants
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

# Config keys mapping to Key Vault secret names
CONFIG_KEYS = {
    "AZURE_HOME_TENANT_ID": "azure-home-tenant-id",  # Primary tenant where the Function App is registered
    "AZURE_CLIENT_ID": "azure-client-id",  # App registration client ID for API
    "AZURE_CLIENT_SECRET": "azure-client-secret",  # App registration client secret
    "REQUIRED_SCOPES": "required-scopes",  # Comma separated list of required scopes
    "MULTI_TENANT_ENABLED": "multi-tenant-enabled",  # Whether multi-tenant auth is enabled
    "ENABLE_AUTO_TENANT_DISCOVERY": "enable-auto-tenant-discovery"  # Auto-discover tenants user has access to
}

def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get configuration value, first trying Key Vault, then environment variables.
    """
    # If the key is in our config mapping, try Key Vault
    if key in CONFIG_KEYS:
        kv_secret_name = CONFIG_KEYS[key]
        secret_value = get_secret(kv_secret_name)
        if secret_value:
            return secret_value
    
    # Fall back to environment variables
    return os.environ.get(key, default)

# Get configuration values
def get_home_tenant_id() -> str:
    """Get the primary Azure AD tenant ID where the Function App is registered."""
    return get_config_value("AZURE_HOME_TENANT_ID", "")

def is_auto_tenant_discovery_enabled() -> bool:
    """Check if automatic tenant discovery is enabled."""
    return get_config_value("ENABLE_AUTO_TENANT_DISCOVERY", "false").lower() == "true"

def get_managed_tenant_ids() -> List[str]:
    """
    Get the list of Azure AD tenant IDs the user has access to via Azure Lighthouse.
    With auto-discovery enabled, this will be determined dynamically from token claims
    rather than a predefined list.
    """
    # Since we're implementing auto-discovery, this returns an empty list
    # Tenants will be authorized based on token issuer/claims during runtime
    return []

def is_multi_tenant_enabled() -> bool:
    """Check if multi-tenant support is enabled."""
    return get_config_value("MULTI_TENANT_ENABLED", "false").lower() == "true"

def get_client_id() -> str:
    """Get the App Registration client ID for the API."""
    return get_config_value("AZURE_CLIENT_ID", "")

def get_client_secret() -> str:
    """Get the App Registration client secret."""
    return get_config_value("AZURE_CLIENT_SECRET", "")

def get_required_scopes() -> list:
    """Get required scopes from config."""
    scopes = get_config_value("REQUIRED_SCOPES", "")
    return scopes.split(",") if scopes else []

def get_token_from_header(req: func.HttpRequest) -> Optional[str]:
    """Extract the Bearer token from the Authorization header."""
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    return auth_header.split("Bearer ")[1]

class MicrosoftIdentityAuthenticator:
    """
    Microsoft Identity Web authenticator for Azure Functions.
    Supports multi-tenant validation for Azure Lighthouse scenarios.
    """
    
    def __init__(self):
        self.home_tenant_id = get_home_tenant_id()
        self.multi_tenant_enabled = is_multi_tenant_enabled()
        self.auto_tenant_discovery = is_auto_tenant_discovery_enabled()
        self.client_id = get_client_id()
        self.client_secret = get_client_secret()
        self.required_scopes = get_required_scopes()
        
        # Dictionary of auth adapters - will be populated dynamically with auto-discovery
        self.auth_adapters = {}
        
        # Create adapter for home tenant
        self.auth_adapters[self.home_tenant_id] = AzureFunctionsAuthAdapter(
            tenant_id=self.home_tenant_id,
            client_id=self.client_id,
            client_credential=self.client_secret
        )
        
        # Create the confidential client application for the home tenant
        self.app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.home_tenant_id}"
        )
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[Any, Any]], Optional[str]]:
        """
        Validate a user's Azure AD token and return user information.
        For multi-tenant scenarios, attempts validation against all configured tenants.
        
        Returns:
            Tuple[bool, Dict, str]: (is_valid, user_info, error_message)
        """
        try:
            # Try to parse just enough of the token to get the issuer (tenant) information
            # We need this to know which tenant's adapter to use for validation
            try:
                import jwt
                # Just decode the header and payload without verification
                decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
                token_issuer = decoded_token.get("iss", "")
                token_tenant_id = None
                
                # Extract tenant ID from issuer
                # Format could be either:
                # - https://sts.windows.net/{tenant_id}/
                # - https://login.microsoftonline.com/{tenant_id}/v2.0
                if "sts.windows.net" in token_issuer:
                    token_tenant_id = token_issuer.split("/")[-2] if token_issuer else None
                elif "login.microsoftonline.com" in token_issuer:
                    token_tenant_id = token_issuer.split("/")[-2] if token_issuer else None
                
                logging.info(f"Token issued by tenant: {token_tenant_id or 'unknown'}")
                
                # For multi-tenant scenarios with auto-discovery enabled
                # Any tenant that issues a valid token is considered authorized
                # The validation is done through JWT signature verification
                if self.multi_tenant_enabled and token_tenant_id:
                    if token_tenant_id != self.home_tenant_id:
                        logging.info(f"Cross-tenant access detected from tenant: {token_tenant_id}")
                        # With auto-discovery, we dynamically create an adapter for this tenant
                        if self.auto_tenant_discovery and token_tenant_id not in self.auth_adapters:
                            logging.info(f"Auto-creating validator for tenant: {token_tenant_id}")
                            self.auth_adapters[token_tenant_id] = AzureFunctionsAuthAdapter(
                                tenant_id=token_tenant_id,
                                client_id=self.client_id,
                                client_credential=self.client_secret
                            )
            except Exception as e:
                logging.error(f"Error parsing token for tenant info: {str(e)}")
                token_tenant_id = None
            
            # Choose the appropriate adapter based on the token's tenant
            adapter = None
            if token_tenant_id in self.auth_adapters:
                logging.info(f"Using adapter for tenant {token_tenant_id}")
                adapter = self.auth_adapters[token_tenant_id]
            else:
                # If no tenant-specific adapter found, try the home tenant adapter
                logging.info(f"No specific adapter for tenant {token_tenant_id}, using home tenant adapter")
                adapter = self.auth_adapters[self.home_tenant_id]
            
            # Validate the token using the selected adapter
            claims = adapter.validate_token(token)
            
            # Validate required scopes
            if self.required_scopes:
                token_scopes = claims.get("scp", "").split(" ")
                if not any(scope in token_scopes for scope in self.required_scopes):
                    return False, None, f"Token doesn't have any of the required scopes: {self.required_scopes}"
            
            # Extract user info from claims
            user_info = {
                "id": claims.get("oid"),
                "name": claims.get("name"),
                "email": claims.get("preferred_username"),
                "roles": claims.get("roles", []),
                "scopes": claims.get("scp", "").split(" ") if "scp" in claims else [],
                # Include tenant information for multi-tenant scenarios
                "tenant_id": claims.get("tid"),  # The tenant ID that issued the token
                "issuer": claims.get("iss")      # The full issuer URL
            }
            
            return True, user_info, None
        except AuthError as e:
            logging.error(f"Token validation error: {str(e)}")
            return False, None, f"Token validation error: {str(e)}"
        except Exception as e:
            logging.error(f"Error validating token: {str(e)}")
            return False, None, f"Error validating token: {str(e)}"

# Create a singleton authenticator
_authenticator = None

def get_authenticator():
    """Get or create the Microsoft Identity authenticator."""
    global _authenticator
    if _authenticator is None:
        _authenticator = MicrosoftIdentityAuthenticator()
    return _authenticator

def get_credential(tenant_id: Optional[str] = None, user_token: Optional[str] = None):
    """
    Get the appropriate credential for authenticating with Azure services.
    
    This function supports multiple authentication modes:
    1. On-Behalf-Of (OBO) flow when a user token is provided
    2. Managed Identity for system operations when no user token is available
    
    Args:
        tenant_id: Optional tenant ID for multi-tenant scenarios. If provided, the credential
                  will be configured to work with resources in the specified tenant.
        user_token: Optional user access token for OBO flow. If provided, access to Azure
                   resources will be done using the user's identity.
    
    Returns:
        An Azure credential that can be used to authenticate with Azure services.
    """
    try:
        from azure.identity import OnBehalfOfCredential
        
        logging.info(f"Getting credential for tenant: {tenant_id or 'default'}, OBO: {bool(user_token)}")
        
        # If we have a user token, use OBO flow to preserve user identity
        if user_token:
            client_id = get_client_id()
            client_secret = get_client_secret()
            authority_host = f"https://login.microsoftonline.com/{tenant_id or get_home_tenant_id()}"
            
            logging.info(f"Setting up OBO credential with authority: {authority_host}")
            
            # Create On-Behalf-Of credential with the user token
            # This allows calls to Azure services to be made as the user, not as the Function App
            obo_credential = OnBehalfOfCredential(
                tenant_id=tenant_id or get_home_tenant_id(),
                client_id=client_id,
                client_secret=client_secret,
                user_assertion=user_token
            )
            
            # Use OBO flow for accessing resources
            return obo_credential
        
        # For all scenarios, we require a user token for OBO flow
        else:
            # Enforce OBO flow by requiring a user token
            logging.error("Cannot create credential without user token - OBO flow is required")
            raise ValueError("User token is required for authentication. All operations must use On-Behalf-Of flow.")
    except Exception as e:
        logging.error(f"Failed to get credential: {str(e)}")
        raise ValueError("Credential configuration error. Check your configuration for managed identity, OBO flow, or Azure Lighthouse delegations.")

async def get_token_for_resource(
    resource: str, 
    tenant_id: Optional[str] = None,
    user_token: Optional[str] = None
) -> Optional[str]:
    """
    Get an access token for a specific Azure resource.
    Supports cross-tenant scenarios through Azure Lighthouse.
    
    When a user_token is provided, uses the OAuth 2.0 On-Behalf-Of (OBO) flow
    to acquire a token with the user's identity. This ensures proper security
    context propagation for audit and access control.
    
    Args:
        resource: The resource identifier (e.g., https://graph.microsoft.com/.default)
        tenant_id: Optional tenant ID for multi-tenant scenarios
        user_token: Optional user access token for OBO flow
        
    Returns:
        The access token or None if token acquisition fails
    """
    try:
        # Get the appropriate credential based on tenant
        logging.info(f"Getting async token for resource {resource} in tenant {tenant_id or 'default'}, OBO: {bool(user_token)}")
        
        # If multi-tenant is enabled and a tenant ID is provided, verify it's either 
        # the home tenant or one of the managed tenants
        if is_multi_tenant_enabled() and tenant_id:
            home_tenant_id = get_home_tenant_id()
            managed_tenants = get_managed_tenant_ids()
            
            if tenant_id != home_tenant_id and tenant_id not in managed_tenants:
                logging.error(f"Requested tenant {tenant_id} is not in the list of managed tenants")
                return None
                
            logging.info(f"Verified tenant {tenant_id} is authorized for access")
            
        # Get credential with OBO flow if user token is provided
        credential = get_credential(tenant_id, user_token)
        
        # Request a token for the specified resource
        token = credential.get_token(resource)
        return token.token
    except Exception as e:
        logging.error(f"Failed to get token for resource {resource} in tenant {tenant_id or 'default'}: {str(e)}")
        return None

def get_graph_token(tenant_id: Optional[str] = None, user_token: Optional[str] = None) -> Optional[str]:
    """
    Get an access token for Microsoft Graph API.
    Supports cross-tenant scenarios through Azure Lighthouse.
    
    When user_token is provided, uses On-Behalf-Of flow to get a token with the user's
    identity preserved, ensuring proper audit trails and access control.
    
    Args:
        tenant_id: Optional tenant ID for multi-tenant scenarios
        user_token: Optional user access token for OBO flow
        
    Returns:
        The Graph API access token or None if token acquisition fails
    """
    try:
        # Use the synchronous version directly instead of the async function
        credential = get_credential(tenant_id, user_token)
        token = credential.get_token("https://graph.microsoft.com/.default")
        return token.token
    except Exception as e:
        logging.error(f"Failed to get Graph API token for tenant {tenant_id or 'default'}, OBO: {bool(user_token)}: {str(e)}")
        return None

def authenticate_request(req: func.HttpRequest) -> Tuple[bool, Optional[Dict[Any, Any]], Optional[str]]:
    """
    Authenticate an incoming HTTP request using Microsoft Identity Web.
    
    Returns:
        Tuple[bool, Optional[Dict], Optional[str]]: (is_authenticated, user_info, error_message)
        
    The user_info dictionary is extended with a "token" field containing the original token,
    which can be used for On-Behalf-Of flow.
    """
    token = get_token_from_header(req)
    
    if not token:
        return False, None, "No authentication token provided"
    
    # Use Microsoft Identity Web to validate token
    authenticator = get_authenticator()
    is_valid, user_info, error_message = authenticator.validate_token(token)
    
    if not is_valid:
        return False, None, error_message or "Invalid or expired authentication token"
    
    # Add the token to user_info for potential OBO flow usage
    if user_info:
        user_info["token"] = token
    
    return True, user_info, None
