# Client Server Triage Bot

A client-server architecture for an LLM-powered bot that allows for Azure/Azure Sentinel/Defender incident triage and security metrics gathering.

## Overview

This project implements a security incident triage system for automated investigation of Azure Sentinel and Microsoft Defender alerts. The system uses a client-server architecture with two main components:

1. **Client (Python CLI)**: A command-line interface where security analysts authenticate with Azure AD and interact with the triage bot to investigate incidents.
2. **MCP Server (Azure Function)**: Receives tool commands from the client and executes predefined queries against Azure Security services to gather incident data, automate investigations, and provide context-aware recommendations.

### Incident Triage Focus
The system is specifically designed to automate the investigation of security incidents through:
- **Prebaked Queries**: Pre-defined security queries that are invoked via natural language prompts
- **Automated Investigation Tools**: Tool functions that execute common incident response tasks
- **Contextual Analysis**: LLM-powered analysis that correlates evidence and provides recommendations
- **Multi-analyst Support**: Enables multiple security analysts to use the system concurrently

The system is designed to work in both single and multi-tenant environments:

- **Single Tenant**: All resources and users are in one Azure AD tenant
- **Multi-Tenant**: Resources are distributed across multiple tenants with Azure Lighthouse delegations for centralized management

## Features

### Incident Triage Capabilities
- Automated investigation of security incidents using prebaked queries and tools
- LLM-powered analysis of incidents with contextual recommendations
- Custom tool functions for common incident response tasks
- Centralized incident handling across Azure Sentinel and Microsoft Defender
- Automated evidence gathering for faster incident resolution

### Technical Features
- Azure AD authentication with App Registrations and custom API scopes
- Azure Functions Easy Auth for secure token validation
- Multi-tenant support and Azure Lighthouse integration for cross-tenant access
- Interactive chat interface for guided incident triage
- Real-time security metrics and data visualization
- Integration with Azure Sentinel and Microsoft Defender APIs
- Secure API communication with end-to-end user identity preservation

## Documentation

This project maintains detailed documentation in the `/docs` directory which is essential for users to understand the system's security authentication model, incident triage capabilities, and deployment options.

- [Authentication Guide](/docs/AUTHENTICATION.md): Details on Azure AD authentication, App Registrations, API permissions, and multi-tenant support
- [Client Documentation](/docs/CLIENT.md): CLI usage, configuration, and incident triage workflows
- [Server Documentation](/docs/SERVER.md): Function App setup, configuration, and security considerations

> **Documentation is critical for security tools**: Proper documentation ensures analysts understand how to use the system effectively during security incidents when time is critical. The documentation in this project follows security best practices by clearly documenting authentication flows, access controls, and investigation capabilities.

## Deployment Options

### LLM Selection

The system supports two deployment options for the language model that powers the incident triage functionality:

1. **OpenAI API (default)**
   - Uses the public OpenAI API (GPT-4 or other models)
   - Requires an OpenAI API key
   - Simpler setup but sends data outside your Azure environment
   - Configure with `USE_AZURE_OPENAI=false`

2. **Azure OpenAI Service**
   - Uses Azure OpenAI Service deployments
   - Keeps all data within your Azure environment
   - Requires an Azure OpenAI resource and deployment
   - Better for organizations with strict data residency requirements
   - Configure with `USE_AZURE_OPENAI=true` and additional Azure-specific settings

Both the CLI client and MCP server need to be configured with the same LLM option. See the [Client Guide](docs/CLIENT.md) and [Server Guide](docs/SERVER.md) for detailed configuration instructions.

## Prerequisites

- Python 3.8 or higher
- Azure CLI installed and configured
- Access to Azure Sentinel/Defender resources
- Azure Functions Core Tools (for local development of MCP server)

## Quick Start

### For Administrators (Server Deployment)

If you're an administrator setting up the MCP server:

1. Clone the repository:
```
git clone https://github.com/username/client-server-triage-bot.git
cd client-server-triage-bot
```

2. Follow the server deployment instructions in [docs/SERVER.md](docs/SERVER.md)

### For Analysts (CLI Client)

If you're a security analyst using the CLI client:

1. Clone the repository:
```
git clone https://github.com/username/client-server-triage-bot.git
cd client-server-triage-bot
```

2. Install dependencies:
```
npm run install-all
```

3. Configure environment variables:
```
# For CLI
cp cli/.env.example cli/.env
# Edit cli/.env with your settings

# For MCP server
cp mcp-server/local.settings.json.example mcp-server/local.settings.json
# Edit local.settings.json with your settings
```

4. Run the CLI:
```
npm run cli
```

5. For local development of the MCP server (Azure Function):
```
npm run mcp-dev
```

## Security Considerations

### Authentication and Authorization

This system implements a secure identity model following Microsoft's recommended practices:

1. **Token-based Authentication**: Azure AD OAuth 2.0 tokens with defined scopes
2. **Microsoft Identity Web**: Industry-standard token validation using Microsoft's identity libraries
3. **Azure Functions Easy Auth**: Built-in token validation at the platform level
4. **On-Behalf-Of Flow**: Preserves user identity for end-to-end auditing
5. **Least Privilege Access**: Custom API scopes enforce proper authorization
6. **No Secrets in Client**: Client relies on Azure CLI for secure token acquisition

### Key Security Features

- **Microsoft Identity Web Integration**: Uses Microsoft's official libraries for token validation
- **Dynamic Tenant Discovery**: Automatically detects authorized tenants based on token claims
- **Azure Key Vault Integration**: Securely stores secrets and connection strings
- **Managed Identity for Startup**: Uses managed identity for Key Vault access during startup
- **RBAC Enforcement**: Respects Azure RBAC permissions when accessing resources

For detailed security information, see the [Authentication Guide](docs/AUTHENTICATION.md).

## Architecture

```
┌─────────────┐                       ┌─────────────┐
│             │                       │             │
│   Client    │◄─────────────────────►│  MCP Server │
│  (Python)   │                       │   (Azure    │
│             │                       │  Function)  │
└─────────────┘                       └─────────────┘
       ▲                                     │
       │                                     │
       │                                     ▼
       │                             ┌─────────────┐
       │                             │             │
       └─────────────────────────────┤Azure Services│
                                     │             │
                                     └─────────────┘
```

### Authentication Flow

#### User Authentication (Security Review Details)
1. The CLI client uses Azure CLI (`az login`) to authenticate the user locally.
2. An Azure AD access token representing the user's identity is obtained with explicitly defined scopes.
3. The token is issued to a registered client application with the user's consent to access specific API scopes.
4. This token is passed to the MCP server as a Bearer token in the Authorization header with each API request.
5. Azure Functions Easy Auth validates the token's signature, expiration, audience, and issuer before allowing the request.
6. Microsoft Identity Web performs additional validation of scopes and claims.
7. All token validation follows OAuth 2.0 and OpenID Connect standards using Microsoft's official libraries.

#### Service Authentication with On-Behalf-Of Flow (Security Review Details)
1. When accessing Azure resources, the server uses OAuth 2.0 On-Behalf-Of (OBO) flow.
2. The user's identity token is exchanged for a resource-specific token using Microsoft's Azure Identity SDK.
3. All resources are accessed as the original authenticated user, preserving identity context end-to-end.
4. This enables proper audit trails and fine-grained RBAC permission enforcement in Azure Activity Logs.
5. Cross-tenant access is supported through Azure Lighthouse delegations with automatic tenant discovery.
6. Tenant permissions are validated dynamically based on the token issuer and claims during runtime.

#### User Identity Propagation
1. The system uses OAuth 2.0 On-Behalf-Of flow for operations.
2. Azure resources are accessed with the user's identity throughout the request chain.
3. Communication occurs within a secured Azure Virtual Network (VNET) environment.
4. During startup/initialization, Key Vault is accessed to load configuration using managed identity.

#### Security Features

- **User Identity Flow**: Operations use the user's identity via OAuth 2.0 On-Behalf-Of flow.
- **Identity Context Preservation**: User identity is maintained throughout the request chain.
- **Multi-User Support**: Multiple analysts can use the system concurrently with their individual identities.
- **Multi-tenant Support**: Authentication across tenants using Azure Lighthouse for delegated resource management.
- **VNET Security**: The function app is deployed in a secured VNET with private endpoints for Azure services.
- **Microsoft Identity Web**: Token validation through Microsoft's official identity libraries.
- **Role-Based Access**: Role verification ensures only authorized personnel can access specific functionality.
- **Key Vault Integration**: Sensitive configuration is stored in Azure Key Vault.

For detailed setup instructions, see:
   - [Client Guide](docs/CLIENT.md)
   - [Server Guide](docs/SERVER.md)

## Project Structure

```
client-server-triage-bot/
├── cli/                      # Python CLI client
│   ├── triage_bot.py         # Main CLI application
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Example environment variables
│
├── docs/                     # Project documentation
│   ├── CLIENT.md             # Client documentation
│   ├── SERVER.md             # Server documentation
│   └── AUTHENTICATION.md     # Authentication guide
│
├── mcp-server/               # Azure Function MCP server
│   ├── azure_auth.py         # Authentication with Microsoft Identity Web
│   ├── function_app.py       # Main Azure Function
│   ├── key_vault_utils.py    # Key Vault integration utilities
│   ├── requirements.txt      # Python dependencies
│   └── local.settings.json.example # Example settings file
│
└── README.md                 # This file (you are here)
```

## License

[License information]
