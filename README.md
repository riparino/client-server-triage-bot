# Client Server Triage Bot

A client-server architecture for an LLM-powered bot that allows for Azure/Azure Sentinel/Defender incident triage and security metrics gathering.

## Overview

This project implements a security incident triage system with two main components:

1. **Client (Python CLI)**: A command-line interface where users can authenticate with Azure CLI and interact with the triage bot.
2. **MCP Server (Azure Function)**: Receives tool commands and executes Azure queries to gather incident data and metrics.

## Features

- Azure AD authentication with App Registrations and custom API scopes
- Azure Functions Easy Auth for secure token validation
- Multi-tenant support and Azure Lighthouse integration for cross-tenant access
- Interactive chat interface for incident triage
- Real-time metrics and data visualization
- Integration with Azure Sentinel and Microsoft Defender
- Secure API communication between components

## Documentation

The project documentation is organized into distinct guides:

1. [Client Guide](docs/CLIENT.md) - Complete guide for installing, configuring, and using the CLI client
2. [Server Guide](docs/SERVER.md) - Comprehensive information about the MCP server, including deployment
3. [Authentication Guide](docs/AUTHENTICATION.md) - Detailed setup instructions for Azure AD authentication with multi-tenant support

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

2. Follow the server deployment instructions in [mcp-server/SERVER_GUIDE.md](mcp-server/SERVER_GUIDE.md)

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

#### User Authentication (SSO)
1. The CLI client uses Azure CLI (`az login`) to authenticate the user locally.
2. An Azure AD access token representing the user's identity is obtained with appropriate scopes.
3. This token is passed to the MCP server with each API request.
4. Azure Functions Easy Auth validates the token before your code executes.
5. Microsoft Identity Web performs additional validation of scopes and claims.

#### Service Authentication with On-Behalf-Of Flow
1. When accessing Azure resources, the server uses OAuth 2.0 On-Behalf-Of (OBO) flow.
2. The user's identity token is exchanged for a resource-specific token.
3. Resources are accessed as the original user, preserving identity context.
4. This enables proper audit trails and fine-grained permission enforcement.
5. Cross-tenant access is supported through Azure Lighthouse delegation.

#### Fallback to Managed Identity
1. If OBO flow fails or is not appropriate, the function app falls back to managed identity.
2. The MCP server has its own system-assigned managed identity.
3. No service principal credentials are stored in code or configuration.
4. All communication occurs within a secured Azure Virtual Network (VNET) environment.

#### Security Features

- **Managed Identity**: In production, the MCP server uses Azure Managed Identity rather than client secrets.
- **On-Behalf-Of Flow**: User identity is preserved when accessing resources using OAuth 2.0 OBO flow.
- **Multi-tenant Support**: Authentication across tenants using Azure Lighthouse for delegated resource management.
- **VNET Security**: The function app is deployed in a secured VNET with private endpoints for Azure services.
- **Microsoft Identity Web**: Token validation through Microsoft's official identity libraries.
- **Role-Based Access**: Optional role verification ensures only authorized personnel can access specific functionality.
- **Private Access**: VMs can only access the function app over peered VNETs or private connections.
- **Key Vault Integration**: Sensitive configuration is stored and retrieved from Azure Key Vault rather than environment variables.

For detailed setup instructions, see:
   - [CLI Guide](cli/CLI_GUIDE.md)
   - [Server Guide](mcp-server/SERVER_GUIDE.md)

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
