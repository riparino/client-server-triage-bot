# Server Documentation

This document provides comprehensive information about the MCP server component of the triage bot system, including authentication setup, multi-tenant support, and deployment instructions.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Authentication](#authentication)
  - [Microsoft Identity Web Integration](#microsoft-identity-web-integration)
  - [OAuth 2.0 On-Behalf-Of Flow](#oauth-20-on-behalf-of-flow)
  - [Multi-Tenant Support](#multi-tenant-support)
- [Server Configuration](#server-configuration)
  - [Environment Variables](#environment-variables)
  - [Key Vault Integration](#key-vault-integration)
- [Deployment Guide](#deployment-guide)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The MCP server is implemented as an Azure Function App that serves as the backend for the triage bot system. It handles:

1. **Authentication and Authorization**: Validates user tokens and enforces access control
2. **Identity Propagation**: Uses OAuth 2.0 On-Behalf-Of flow to preserve user identity
3. **Cross-Tenant Access**: Supports Azure Lighthouse for managing resources across tenants
4. **API Endpoints**: Provides endpoints for incident management, metrics, and more

## Authentication

### Microsoft Identity Web Integration

The server uses Microsoft Identity Web for Python to validate tokens and enforce access control:

```python
from microsoft_identity_web import ConfidentialClientApplication, ClaimsValidator
from microsoft_identity_web.adapters import AzureFunctionsAuthAdapter

def authenticate_request(req: func.HttpRequest):
    token = get_token_from_header(req)
    
    if not token:
        return False, None, "No authentication token provided"
    
    # Use Microsoft Identity Web to validate token
    authenticator = get_authenticator()
    is_valid, user_info, error_message = authenticator.validate_token(token)
    
    # Add the token to user_info for potential OBO flow usage
    if user_info:
        user_info["token"] = token
    
    return is_valid, user_info, error_message
```

### OAuth 2.0 On-Behalf-Of Flow

The server implements the OAuth 2.0 On-Behalf-Of (OBO) flow to preserve user identity when accessing Azure resources:

1. **Token Exchange**: The user's token is exchanged for a resource-specific token
2. **Identity Preservation**: Resources are accessed as the original user, not the function app
3. **Audit Trail**: All operations appear in logs with the actual user identity
4. **Fine-grained Access Control**: Access is limited to what the user is allowed to do

```python
def get_credential(tenant_id=None, user_token=None):
    if user_token:
        # Create On-Behalf-Of credential with the user token
        obo_credential = OnBehalfOfCredential(
            tenant_id=tenant_id or get_home_tenant_id(),
            client_id=get_client_id(),
            client_secret=get_client_secret(),
            user_assertion=user_token
        )
        
        # Fall back to managed identity if OBO fails
        return ChainedTokenCredential(obo_credential, ManagedIdentityCredential())
    else:
        # Use managed identity for system operations
        return ManagedIdentityCredential()
```

### Multi-Tenant Support

The server supports multi-tenant scenarios through Azure Lighthouse delegation:

1. **Configuration**: Specify the home tenant and managed tenant IDs
2. **Token Validation**: Verify tokens from multiple allowed tenants
3. **Tenant Selection**: Dynamically select the appropriate tenant for each operation
4. **Cross-Tenant Access**: Use OBO flow or managed identity for cross-tenant resource access

```python
def validate_token(self, token):
    # Extract tenant ID from token issuer
    decoded_token = jwt.decode(token, options={"verify_signature": False})
    token_issuer = decoded_token.get("iss", "")
    token_tenant_id = extract_tenant_id_from_issuer(token_issuer)
    
    # Verify this is an allowed tenant
    if token_tenant_id != self.home_tenant_id and token_tenant_id not in self.managed_tenant_ids:
        return False, None, f"Token from unauthorized tenant: {token_tenant_id}"
        
    # Use the appropriate tenant's adapter for validation
    adapter = self.auth_adapters.get(token_tenant_id, self.auth_adapters[self.home_tenant_id])
    claims = adapter.validate_token(token)
    
    # Process claims and return user info
    user_info = extract_user_info_from_claims(claims)
    return True, user_info, None
```

## Server Configuration

### Environment Variables

The function app uses these environment variables (or Key Vault secrets):

```json
{
  "Values": {
    "AZURE_HOME_TENANT_ID": "your_primary_tenant_id",
    "AZURE_MANAGED_TENANTS": "tenant1,tenant2",
    "AZURE_CLIENT_ID": "your_app_registration_client_id",
    "AZURE_CLIENT_SECRET": "your_app_registration_client_secret",
    "REQUIRED_SCOPES": "api://your-app-id/incidents.read,api://your-app-id/metrics.read",
    "MULTI_TENANT_ENABLED": "true",
    "USE_KEY_VAULT": "true",
    "KEY_VAULT_NAME": "kv-triage-bot"
  }
}
```

### Key Vault Integration

For production deployments, sensitive configuration is stored in Azure Key Vault:

1. **System-Assigned Managed Identity**: The function app uses its managed identity to access Key Vault
2. **Secret Mapping**: Each environment variable maps to a Key Vault secret name
3. **Fallback**: If a secret isn't found in Key Vault, the system falls back to environment variables

```python
def get_config_value(key: str, default: Any = None) -> Any:
    if key in CONFIG_KEYS and os.environ.get("USE_KEY_VAULT", "false").lower() == "true":
        kv_secret_name = CONFIG_KEYS[key]
        secret_value = get_secret(kv_secret_name)
        if secret_value:
            return secret_value
    
    # Fall back to environment variables
    return os.environ.get(key, default)
```

## Deployment Guide

### Prerequisites

- Azure subscription with owner/contributor access
- Azure CLI installed and configured
- Azure Functions Core Tools installed

### Deployment Steps

1. **Register App in Azure AD**:
   - Create an App Registration in your Azure AD tenant
   - Configure API permissions and expose custom scopes
   - Set up authentication for multi-tenant access if needed

2. **Create Azure Resources**:
   - Create a Resource Group for your function app
   - Create an Azure Function App with system-assigned managed identity
   - Create an Azure Key Vault (for production deployments)

3. **Configure Azure Lighthouse** (for multi-tenant):
   - Set up delegations from managed tenants to your home tenant
   - Assign appropriate RBAC roles for cross-tenant access

4. **Deploy the Function App**:
   ```bash
   cd mcp-server
   func azure functionapp publish your-function-app-name
   ```

5. **Configure the Function App**:
   - Set up App Service Authentication (Easy Auth)
   - Configure application settings or Key Vault references
   - Grant the function app's managed identity access to required resources

## Troubleshooting

### Authentication Issues

- **Token validation fails**: Verify App Registration settings and token scopes
- **Multi-tenant validation fails**: Check Lighthouse delegations and tenant configurations
- **OBO flow errors**: Ensure the App Registration has proper API permissions

### Deployment Issues

- **Managed Identity errors**: Verify the function app has a system-assigned identity
- **Key Vault access denied**: Check RBAC permissions for the function app's identity
- **Missing settings**: Ensure all required configuration is set in app settings or Key Vault

### Cross-Tenant Access

- **Access denied to resources in managed tenants**: Verify Lighthouse delegations and RBAC roles
- **Token rejected by managed tenant**: Check multi-tenant settings in App Registration
