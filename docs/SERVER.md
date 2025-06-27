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

### Multi-Tenant Operation with Azure Lighthouse

The MCP Server supports cross-tenant operations through the OAuth 2.0 On-Behalf-Of flow and Azure Lighthouse:

```python
def get_credential(resource_uri, user_token):
    """
    Get an Azure credential for a specific resource that preserves the user's identity.
    Uses OAuth 2.0 On-Behalf-Of flow to maintain the user's identity and permissions,
    including Lighthouse delegations to other tenants.
    """
    client_id = get_client_id()
    client_secret = get_client_secret()
    
    # Create a credential using On-Behalf-Of flow
    credential = OnBehalfOfCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        user_assertion=user_token,
    )
    
    return credential
```

#### How Cross-Tenant Access Works

1. Function App runs in the home tenant only
2. User authenticates with Azure AD in their home tenant
3. When accessing resources:
   - **Same-tenant resources**: Direct access with the user's permissions
   - **Cross-tenant resources**: Access through the user's Lighthouse delegations
   
The OBO flow automatically preserves the user's identity and delegations across tenant boundaries. No additional configuration is needed on the Function App itself - it inherits the user's Lighthouse permissions through their token.

This enables security analysts to investigate incidents across multiple tenants with a single authentication flow, while maintaining proper audit trails and access controls.

### Multi-Tenant Support

The server supports multi-tenant scenarios through Azure Lighthouse delegation:

1. **Configuration**: Specify the home tenant and managed tenant IDs
2. **Token Validation**: Verify tokens from multiple allowed tenants
3. **Tenant Selection**: Dynamically select the appropriate tenant for each operation
4. **Cross-Tenant Access**: Use OBO flow for cross-tenant resource access

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

#### Authentication Configuration

```json
{
  "Values": {
    "AZURE_HOME_TENANT_ID": "your_primary_tenant_id",
    "ENABLE_AUTO_TENANT_DISCOVERY": "true",
    "AZURE_CLIENT_ID": "your_app_registration_client_id",
    "AZURE_CLIENT_SECRET": "your_app_registration_client_secret",
    "REQUIRED_SCOPES": "api://your-app-id/incidents.read,api://your-app-id/metrics.read",
    "MULTI_TENANT_ENABLED": "true",
    "USE_KEY_VAULT": "true",
    "KEY_VAULT_NAME": "kv-triage-bot"
  }
}
```

#### LLM Configuration Options

The server supports two LLM deployment options for incident triage automation:

##### Option 1: OpenAI API (Default)
```json
{
  "Values": {
    "OPENAI_API_KEY": "your_openai_api_key",
    "OPENAI_MODEL": "gpt-4",
    "USE_AZURE_OPENAI": "false"
  }
}
```

##### Option 2: Azure OpenAI Service
```json
{
  "Values": {
    "USE_AZURE_OPENAI": "true",
    "OPENAI_API_KEY": "your_azure_openai_api_key",
    "OPENAI_API_VERSION": "2023-05-15",
    "OPENAI_ENDPOINT": "https://your-openai-resource.openai.azure.com/",
    "AZURE_OPENAI_DEPLOYMENT": "your_gpt4_deployment_name"
  }
}
```

### Key Vault Integration

For production deployments, sensitive configuration is stored in Azure Key Vault:

1. **Startup Configuration**: During initialization, the function app uses a managed identity to access Key Vault
2. **Secret Mapping**: Each environment variable maps to a Key Vault secret name
3. **Environment Variables**: The system can also read configuration from environment variables

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

1. **Register API App in Azure AD**:
   - Go to Azure Portal > Azure AD > App Registrations > New Registration
   - Name: "Triage Bot API"
   - Supported account types: "Accounts in any organizational directory (Any Azure AD directory - Multitenant)"
   - Redirect URI: Leave blank for now
   - Click Register
   - Copy the Application (client) ID - you'll need this later
   
2. **Configure API Permissions and Scopes**:
   - In your new App Registration > Expose an API
   - Set Application ID URI: click "Set" and use default (api://{client-id})
   - Add Scopes:
     - Add a scope named "incidents.read"
       - Admin & user consent display name: "Read Security Incidents"
       - Description: "Allows the application to read security incidents on behalf of the signed-in user"
     - Add a scope named "metrics.read"
       - Admin & user consent display name: "Read Security Metrics"
       - Description: "Allows the application to read security metrics on behalf of the signed-in user"
   
3. **Add Client Secret**:
   - Go to Certificates & secrets > Client secrets
   - Add a new client secret, give it a description and expiration
   - Copy the secret value immediately (you cannot see it again)

4. **Create Azure Resources**:
   - Create a Resource Group for your function app
   ```bash
   az group create --name rg-triage-bot --location eastus
   ```
   
   - Create an Azure Key Vault
   ```bash
   az keyvault create --name kv-triage-bot --resource-group rg-triage-bot --location eastus
   ```
   
   - Create an Azure Function App with system-assigned managed identity
   ```bash
   az functionapp create --name func-triage-bot --resource-group rg-triage-bot --storage-account satriagebot --consumption-plan-location eastus --runtime python --runtime-version 3.9 --functions-version 4
   az functionapp identity assign --name func-triage-bot --resource-group rg-triage-bot
   ```

5. **Set Function App Configuration**:
   ```bash
   az functionapp config appsettings set --name func-triage-bot --resource-group rg-triage-bot --settings \
     "AZURE_CLIENT_ID=your-app-client-id" \
     "AZURE_CLIENT_SECRET=your-app-client-secret" \
     "AZURE_HOME_TENANT_ID=your-home-tenant-id" \
     "MULTI_TENANT_ENABLED=true" \
     "ENABLE_AUTO_TENANT_DISCOVERY=true" \
     "USE_KEY_VAULT=true" \
     "KEY_VAULT_NAME=kv-triage-bot" \
     "USE_EASY_AUTH=true" \
     "REQUIRED_SCOPES=api://your-app-id/incidents.read,api://your-app-id/metrics.read"
   ```

6. **Configure Azure Key Vault Access**:
   ```bash
   # Get the function app's managed identity object ID
   func_identity_id=$(az functionapp identity show --name func-triage-bot --resource-group rg-triage-bot --query principalId --output tsv)
   
   # Grant Key Vault access
   az keyvault set-policy --name kv-triage-bot --resource-group rg-triage-bot --object-id $func_identity_id --secret-permissions get list
   ```

7. **Configure Azure Lighthouse** (for multi-tenant):
   - Set up delegations from managed tenants to your home tenant
   - This is done by the administrators of the managed tenants
   - Assign appropriate RBAC roles for cross-tenant access (like Security Reader)

8. **Enable Easy Auth for Function App**:
   - In Azure Portal > your Function App > Authentication
   - Click "Add identity provider"
   - Select "Microsoft"
   - In App registration type > select "Pick an existing app registration in this directory"
   - Select your "Triage Bot API" app registration
   - Set Issuer URL: "https://login.microsoftonline.com/{tenant-id}/v2.0"
   - Under Allowed token audiences: add your API URI (api://{client-id})
   - Enable "Require authentication"

9. **Deploy the Function App**:
   ```bash
   cd mcp-server
   func azure functionapp publish func-triage-bot
   ```

5. **Configure the Function App**:
   - Set up App Service Authentication (Easy Auth)
   - Configure application settings or Key Vault references
   - Grant the function app's managed identity access to Key Vault (for startup configuration only)

## Troubleshooting

### Authentication Issues

- **Token validation fails**: Verify App Registration settings and token scopes
- **Multi-tenant validation fails**: Check Lighthouse delegations and tenant configurations
- **OBO flow errors**: Ensure the App Registration has proper API permissions

### Deployment Issues

- **Key Vault access errors**: Verify the function app has a system-assigned identity for startup configuration
- **Key Vault access denied**: Check RBAC permissions for the function app's identity
- **Missing settings**: Ensure all required configuration is set in app settings or Key Vault

### Cross-Tenant Access

- **Access denied to resources in managed tenants**: Verify Lighthouse delegations and RBAC roles
- **Token rejected by managed tenant**: Check multi-tenant settings in App Registration
