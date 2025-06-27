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

#### Required Configuration

```bash
# Azure Function App URL - update with your actual deployed function app URL
FUNCTION_APP_URL=https://your-function-app.azurewebsites.net/api

# Azure AD tenant configuration
AZURE_TENANT_ID=your_tenant_id
AZURE_HOME_TENANT_ID=your-home-tenant-id  # Same as AZURE_TENANT_ID for most cases

# App Registration client ID for CLI app (create in Azure Portal > App registrations)
AZURE_CLIENT_ID=your_cli_app_client_id  

# Function App API identifier (from the API App Registration)
FUNCTION_APP_RESOURCE=api://your-function-app-id
FUNCTION_APP_SCOPE=api://your-function-app-id/incidents.read api://your-function-app-id/metrics.read
```

#### Multi-tenant Configuration
```bash
# Enable multi-tenant support for Azure Lighthouse scenarios
MULTI_TENANT_ENABLED=true
```

#### AI Chat Interface Configuration
```bash
# OpenAI API settings for the chat interface
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# Optional: Azure OpenAI settings (only needed if USE_AZURE_OPENAI=true)
USE_AZURE_OPENAI=false
OPENAI_API_VERSION=2023-05-15
OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

3. Register a Client App in Azure AD:
   - Go to Azure Portal > Azure AD > App Registrations > New Registration
   - Name: "Triage Bot CLI Client"
   - Supported account types: Choose based on your needs (single or multi-tenant)
   - Redirect URI: http://localhost (for native client)
   - API permissions: Add permission for your MCP Server API app registration
     - Add a permission > My APIs > Select your "Triage Bot API"
     - Select the required scopes (incidents.read, metrics.read)
   - Copy the Application (client) ID and use it for AZURE_CLIENT_ID in your .env file
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
   ```
   MULTI_TENANT_ENABLED=true
   AZURE_HOME_TENANT_ID=your-primary-tenant-id
   ```

2. Ensure Azure Lighthouse delegations are set up:
   - The managed tenants should delegate resources to your home tenant
   - Users in your home tenant will have access to resources across all delegated tenants
   - No need to list managed tenants - the system dynamically detects tenant permissions

3. Login to Azure CLI with your primary tenant account:
   ```bash
   az login --tenant your-primary-tenant-id
   ```

4. Run the CLI login command: 
   ```bash
   python triage_bot.py login
   ```

5. The CLI will obtain tokens that work across all tenants you have access to via Lighthouse delegation

> **Note:** Users only need access to the tenants they're authorized for - the system automatically detects these permissions based on the tokens and delegations without requiring a predefined list of tenant IDs.

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

### Incident Triage Capabilities

The CLI's main purpose is to provide an interactive interface for Azure security incident triage:

1. **Azure Control Plane & Data Plane Analysis**: Investigate across Azure environments
   - **Identity Pivots**: Analyze user activities, service principals, and managed identities
   - **Resource Pivots**: Investigate VMs, storage accounts, databases, network components
   - **Access Pattern Pivots**: Examine authentication events, role assignments, policy changes
   - **Activity Log Pivots**: Review management operations, deployment changes, Azure RBAC modifications

2. **Cross-Product Integrated Analysis**: Tools that correlate data across security products
   - Microsoft Sentinel incident correlation with Microsoft Defender alerts
   - Azure Security Center recommendations with Azure resource health
   - Azure Monitor metrics and logs with security telemetry
   - Custom log integration for application-specific insights

3. **MITRE ATT&CK Framework Mapping**: The system provides:
   - Mapping alerts to MITRE ATT&CK tactics, techniques, and procedures (TTPs)
   - Identification of full attack sequence across the kill chain
   - Similar incident patterns from historical data based on TTPs
   - Potential false positive analysis based on behavioral patterns

4. **Multi-analyst Collaborative Investigation**: Security team members can:
   - Work on incidents simultaneously across shared context
   - Share investigation findings and evidence
   - Add notes and context to document investigation steps
   - Track investigation progress and remediation actions

### How to Invoke Tools and Queries

When using the chat interface, you can invoke prebaked tools and queries using natural language commands in the following ways:

#### Starting the Chat Interface

```bash
python triage_bot.py chat
```

#### Invoking Prebaked Queries

Simply ask for the information using natural language. The system will automatically identify and run the appropriate query:

```
> Show me failed login attempts in the last 24 hours
> List high severity incidents from Sentinel
> Find all alerts related to IP address 192.168.1.100
> Show me user activity for jsmith@example.com
```

#### Invoking Investigation Tools

Request specific analysis tools using natural language prompts:

```
> Analyze the attack path for incident 42684e72-e7f6-4b3a-b7a6-8d23da0728b3
> Generate a timeline of events for alert 2bd453d0-7956-4d7e-bd91-5ae6655fb2a2
> Correlate this incident with related Microsoft Defender findings
> Check 192.168.1.100 against threat intelligence sources
> Compare this incident pattern with similar incidents in the last 7 days
```

#### Tool Command Reference

| Task | Example Command |
| ---- | -------------- |
| Login authentication | `python triage_bot.py login` |
| List recent incidents | `python triage_bot.py list-incidents --limit 10` |
| Get incident details | `python triage_bot.py get-incident 42684e72-e7f6-4b3a-b7a6-8d23da0728b3` |
| View security insights dashboard | `python triage_bot.py metrics` |
| Start interactive triage | `python triage_bot.py chat` |
| Show available tools | `python triage_bot.py tools` |

> **Tip**: When using the chat interface, type `/help` to see a list of available commands and tools.
> For a comprehensive list of tools and example commands, run `python triage_bot.py tools`.

### Examples

List recent incidents:
```bash
python triage_bot.py list-incidents
```

View security insights dashboard:
```bash
python triage_bot.py metrics
```

Start a chat session:
```bash
python triage_bot.py chat
```

### Detailed Command Usage

#### List Incidents
```bash
python triage_bot.py list-incidents
```

Options:
- `--limit INTEGER`: Number of incidents to retrieve (default: 10)
- `--severity TEXT`: Filter by severity (low, medium, high, critical)

Example:
```bash
python triage_bot.py list-incidents --limit 20 --severity high
```

#### Get Incident Details
```bash
python triage_bot.py get-incident INCIDENT_ID
```

Get detailed information about a specific incident.

Example:
```bash
python triage_bot.py get-incident 42684e72-e7f6-4b3a-b7a6-8d23da0728b3
```

#### Interactive Chat
```bash
python triage_bot.py chat
```

Start an interactive chat session with the triage bot assistant to investigate incidents using natural language.

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
