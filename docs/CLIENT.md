# Client Documentation

This document provides comprehensive information about the CLI client component of the triage bot system, including installation, configuration, and usage instructions for authentication and cross-tenant access.

## Table of Contents
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
  - [Configuration](#configuration)
- [Authentication](#authentication)
  - [Single Tenant Authentication](#single-tenant-authentication)
  - [Multi-Tenant Authentication](#multi-tenant-authentication)
  - [Token Acquisition](#token-acquisition)
- [Usage Instructions](#usage-instructions)
  - [Available Commands](#available-commands)
  - [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- Python 3.8 or higher
- Azure CLI installed and configured
- Access to Azure Sentinel/Defender resources
- Valid Azure AD account with appropriate permissions

### Setup

1. Clone the repository:
```bash
git clone https://github.com/username/client-server-triage-bot.git
cd client-server-triage-bot
```

2. Install dependencies:
```bash
cd cli
pip install -r requirements.txt
```

### Configuration

1. Create a `.env` file based on the provided template:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your settings:
```bash
# Azure Function App URL for the MCP server
FUNCTION_APP_URL=https://your-function-app.azurewebsites.net/api

# OpenAI API settings for the chat interface
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# Azure Configuration
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_cli_app_client_id
FUNCTION_APP_RESOURCE=api://your-function-app-id
FUNCTION_APP_SCOPE=api://your-function-app-id/incidents.read api://your-function-app-id/metrics.read

# Multi-tenant configuration (if needed)
MULTI_TENANT_ENABLED=true
AZURE_HOME_TENANT_ID=your-home-tenant-id
AZURE_MANAGED_TENANTS=managed-tenant-1,managed-tenant-2
```

## Authentication

The CLI client uses Azure AD authentication through OAuth 2.0 to secure access to the MCP Server and Azure resources.

### Single Tenant Authentication

For single tenant scenarios:

1. Configure your `.env` file with your tenant ID
2. Run the CLI login command: `python triage_bot.py login`
3. Follow the Azure CLI prompts if not already logged in
4. The CLI will obtain a token with the appropriate scopes for the MCP server

### Multi-Tenant Authentication

For multi-tenant scenarios with Azure Lighthouse:

1. Configure your `.env` file with:
   - `MULTI_TENANT_ENABLED=true`
   - `AZURE_HOME_TENANT_ID=` (your primary tenant ID)
   - `AZURE_MANAGED_TENANTS=` (comma-separated list of managed tenant IDs)
2. Ensure Azure Lighthouse delegations are set up from managed tenants to your home tenant
3. Run the CLI login command: `python triage_bot.py login`
4. The CLI will obtain tokens that work across tenants via Lighthouse delegation

### Token Acquisition

The client gets tokens using Azure CLI with specific scopes for the MCP server:

```python
def get_azure_token():
    function_app_resource = os.getenv("FUNCTION_APP_RESOURCE", "api://your-function-app-id")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    scope = os.getenv("FUNCTION_APP_SCOPE", f"{function_app_resource}/incidents.read")
    
    result = subprocess.run(
        ["az", "account", "get-access-token", "--scope", scope, "--client-id", client_id],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        token_info = json.loads(result.stdout)
        return token_info.get("accessToken")
    return None
```

## Usage Instructions

### Available Commands

- `login`: Authenticate with Azure AD and get a token
- `incidents`: List and manage security incidents
- `metrics`: Get security metrics and statistics
- `chat`: Start an interactive chat session for incident triage

### Examples

List recent incidents:
```bash
python triage_bot.py incidents list --days 7
```

Get security metrics:
```bash
python triage_bot.py metrics summary --days 30
```

Start a chat session:
```bash
python triage_bot.py chat
```

## Troubleshooting

### Authentication Issues

- **Token acquisition fails**: Ensure you're logged in with `az login` and have proper permissions
- **Access denied to MCP Server**: Verify your app registration has the required scopes
- **Multi-tenant access issues**: Check Azure Lighthouse delegations are properly configured

### Client Errors

- **Connection errors**: Verify the FUNCTION_APP_URL is correct and accessible
- **Missing dependencies**: Ensure all packages in requirements.txt are installed

### Azure Resource Access

- **Unable to access resources in managed tenants**: Verify Lighthouse delegations and multi-tenant settings
- **Permission errors**: Check that your user has appropriate RBAC roles assigned
