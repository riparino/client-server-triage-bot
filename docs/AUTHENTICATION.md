# Authentication Guide

This document provides detailed instructions for setting up secure authentication for the Triage Bot using Azure AD, App Registrations, custom API permissions, and multi-tenant support via Azure Lighthouse.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Setting Up App Registrations](#setting-up-app-registrations)
  - [API App Registration](#api-app-registration)
  - [CLI App Registration](#cli-app-registration)
- [Azure Functions Easy Auth](#azure-functions-easy-auth)
- [OAuth 2.0 On-Behalf-Of Flow](#oauth-20-on-behalf-of-flow)
- [Multi-Tenant Support](#multi-tenant-support)
- [Azure Key Vault Integration](#azure-key-vault-integration)

---

## Architecture Overview

The authentication architecture consists of these key components:

1. **Client Authentication**: Azure CLI-based authentication for the CLI client
2. **Token Validation**: Microsoft Identity Web for validating tokens in the Function App
3. **On-Behalf-Of Flow**: Identity preservation when accessing Azure resources
4. **Multi-Tenant Support**: Access to resources across tenants via Azure Lighthouse
5. **Key Vault Integration**: Secure storage of credentials and configuration

Authentication flow:

```
┌────────────┐      (1) Login       ┌──────────────┐
│            │ ─────────────────────>│              │
│   User     │                      │   Azure AD    │
│            │ <─────────────────────│              │
└────────────┘      (2) Token       └──────────────┘
      │                                    ▲
      │ (3) Token                          │
      ▼                                    │ (4) Validate
┌────────────┐       (5) Call       ┌──────────────┐
│            │ ─────────────────────>│              │
│  CLI Client│                      │ Function App  │
│            │ <─────────────────────│              │
└────────────┘       (6) Data       └──────────────┘
                                           │
                                           │ (7) OBO Flow
                                           ▼
                                    ┌──────────────┐
                                    │              │
                                    │Azure Resources│
                                    │              │
                                    └──────────────┘
```

## Setting Up App Registrations

### API App Registration

1. **Create the API App Registration**:
   ```
   az ad app create --display-name "Triage Bot API" --sign-in-audience "AzureADMyOrg"
   ```

2. **Note the Application (client) ID**:
   ```
   az ad app list --display-name "Triage Bot API" --query "[].appId" -o tsv
   ```

3. **Create a client secret**:
   ```
   az ad app credential reset --id <app-id> --append
   ```

4. **Configure API permissions**:
   - Microsoft Graph: User.Read (delegated)
   - Microsoft Sentinel API: Data.Read (delegated)
   - Azure Security Center: SecurityEvents.Read (delegated)

5. **Expose an API**:
   ```
   # Set the App ID URI
   az ad app update --id <app-id> --identifier-uris "api://<app-id>"
   
   # Add custom scopes
   az ad app update --id <app-id> --set oauth2Permissions="[{\"id\":\"<uuid>\",\"adminConsentDescription\":\"Read incidents\",\"adminConsentDisplayName\":\"Read Incidents\",\"isEnabled\":true,\"type\":\"User\",\"userConsentDescription\":\"Read incidents\",\"userConsentDisplayName\":\"Read Incidents\",\"value\":\"incidents.read\"},{\"id\":\"<uuid>\",\"adminConsentDescription\":\"Read metrics\",\"adminConsentDisplayName\":\"Read Metrics\",\"isEnabled\":true,\"type\":\"User\",\"userConsentDescription\":\"Read metrics\",\"userConsentDisplayName\":\"Read Metrics\",\"value\":\"metrics.read\"}]"
   ```

6. **For multi-tenant support**:
   ```
   az ad app update --id <app-id> --available-to-other-tenants true
   ```

### CLI App Registration

1. **Create the CLI App Registration**:
   ```
   az ad app create --display-name "Triage Bot CLI" --sign-in-audience "AzureADMyOrg"
   ```

2. **Note the Application (client) ID**:
   ```
   az ad app list --display-name "Triage Bot CLI" --query "[].appId" -o tsv
   ```

3. **Configure API permissions**:
   - Add permission to the API App's custom scopes (Admin consent required)

## Azure Functions Easy Auth

Set up Easy Auth in your Function App for token validation:

1. **Enable App Service Authentication**:
   ```
   az webapp auth update --resource-group <resource-group> --name <function-app-name> --enabled true --action "AllowAnonymous" --aad-allowed-token-audiences "api://<api-app-id>" --aad-client-id "<api-app-id>" --aad-client-secret "<api-client-secret>" --aad-token-issuer-url "https://login.microsoftonline.com/<tenant-id>/v2.0"
   ```

2. **Configure Function App Settings**:
   ```
   az functionapp config appsettings set --name <function-app-name> --resource-group <resource-group> --settings "AZURE_HOME_TENANT_ID=<home-tenant-id>" "AZURE_CLIENT_ID=<api-app-id>" "AZURE_CLIENT_SECRET=<api-client-secret>" "REQUIRED_SCOPES=incidents.read,metrics.read" "MULTI_TENANT_ENABLED=true" "AZURE_MANAGED_TENANTS=<managed-tenant-1>,<managed-tenant-2>"
   ```

## OAuth 2.0 On-Behalf-Of Flow

The OAuth 2.0 On-Behalf-Of (OBO) flow preserves user identity when accessing Azure resources.

### How OBO Flow Works

1. **Token Acquisition**: The user authenticates and receives an access token for the Function App API
2. **Token Validation**: The Function App validates this token using Microsoft Identity Web
3. **Token Exchange**: When the Function App needs to access Azure resources, it exchanges the user's token for a new token specifically for that resource
4. **Resource Access**: Resources are accessed using the exchanged token, preserving the user's identity

### Benefits of OBO Flow

- **Identity Preservation**: All operations appear as the end user, not the app identity
- **Proper Audit Trails**: Azure Activity Logs show the actual user performing actions
- **Fine-grained Access Control**: Access is limited to what the user is allowed to do
- **Cross-Tenant Operations**: Works seamlessly with Azure Lighthouse delegated resources

### Implementation

The Function App implements OBO flow using the Azure Identity SDK:

```python
def get_credential(tenant_id=None, user_token=None):
    if user_token:
        # Use On-Behalf-Of credential when a user token is available
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

def get_graph_token(tenant_id=None, user_token=None):
    credential = get_credential(tenant_id, user_token)
    token = credential.get_token("https://graph.microsoft.com/.default")
    return token.token
```

## Multi-Tenant Support

For environments involving users accessing resources across multiple tenants through Azure Lighthouse:

### Azure Lighthouse Delegation Setup

1. In the managed tenant (where the resources exist), go to "Service providers" in Azure Portal
2. Select "Create an Azure Lighthouse definition (multi-tenant)"
3. Select the managing tenant as the service provider
4. Add the required permissions:
   - For Sentinel: "Azure Sentinel Contributor" and "Reader"
   - For Security Center: "Security Admin" and "Security Reader"
5. Complete the delegation process

### Multi-Tenant App Registration Configuration

1. In your home tenant's App Registration:
   - Go to "Authentication" tab
   - Under "Supported account types", select "Accounts in any organizational directory (Any Azure AD directory - Multitenant)"
   - Save your changes

2. Update your Function App configuration with:
   ```
   "MULTI_TENANT_ENABLED": "true"
   "AZURE_HOME_TENANT_ID": "<your-home-tenant-id>"
   "AZURE_MANAGED_TENANTS": "<managed-tenant-1>,<managed-tenant-2>"
   ```

### CLI Multi-Tenant Configuration

Update your CLI client's `.env` file to include:

```
# Multi-tenant configuration
MULTI_TENANT_ENABLED=true
AZURE_HOME_TENANT_ID=your-home-tenant-id
# Comma-separated list of tenant IDs for cross-tenant access
AZURE_MANAGED_TENANTS=managed-tenant-1,managed-tenant-2
```

## Azure Key Vault Integration

For production deployments, store sensitive configuration in Azure Key Vault:

1. **Create an Azure Key Vault**:
   ```
   az keyvault create --name <keyvault-name> --resource-group <resource-group> --location <location>
   ```

2. **Grant the Function App access to Key Vault**:
   ```
   az keyvault set-policy --name <keyvault-name> --object-id <function-app-managed-identity-object-id> --secret-permissions get list
   ```

3. **Store secrets in Key Vault**:
   ```
   az keyvault secret set --vault-name <keyvault-name> --name "azure-client-id" --value "<app-client-id>"
   az keyvault secret set --vault-name <keyvault-name> --name "azure-client-secret" --value "<app-client-secret>"
   az keyvault secret set --vault-name <keyvault-name> --name "azure-home-tenant-id" --value "<tenant-id>"
   az keyvault secret set --vault-name <keyvault-name> --name "azure-managed-tenants" --value "<tenant1>,<tenant2>"
   az keyvault secret set --vault-name <keyvault-name> --name "required-scopes" --value "incidents.read,metrics.read"
   az keyvault secret set --vault-name <keyvault-name> --name "multi-tenant-enabled" --value "true"
   ```

4. **Configure the Function App to use Key Vault**:
   ```
   az functionapp config appsettings set --name <function-app-name> --resource-group <resource-group> --settings "USE_KEY_VAULT=true" "KEY_VAULT_NAME=<keyvault-name>"
   ```

The function app will automatically retrieve secrets from Key Vault using its managed identity.
