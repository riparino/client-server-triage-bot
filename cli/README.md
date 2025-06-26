# Client Documentation

This document provides comprehensive information about the CLI client component of the triage bot system, including installation, configuration, and usage instructions.

## Table of Contents
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
  - [Configuration](#configuration)
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
- Valid Azure account with appropriate permissions

### Setup

1. Clone the repository:
```bash
git clone https://github.com/username/client-server-triage-bot.git
cd client-server-triage-bot
```

2. Install CLI dependencies:
```bash
cd cli
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
# For CLI
cp cli/.env.example cli/.env
# Edit cli/.env with your settings
```

### Configuration

The CLI client requires the following configuration in the `.env` file:

```
# MCP Server connection
MCP_SERVER_URL=https://your-function-app.azurewebsites.net
MCP_API_VERSION=v1

# Azure configuration
AZURE_TENANT_ID=your-tenant-id

# OpenAI configuration (choose one of the options below)

# Option 1: Standard OpenAI (default)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
USE_AZURE_OPENAI=false

# Option 2: Azure OpenAI
USE_AZURE_OPENAI=true
OPENAI_API_KEY=your-azure-openai-api-key
OPENAI_API_VERSION=2023-05-15
OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

## Usage Instructions

### Available Commands

#### Login

```bash
python triage_bot.py login
```

Authenticate with Azure using Azure CLI and obtain a session token for the MCP server.

#### List Incidents

```bash
python triage_bot.py list-incidents
```

List recent security incidents from Azure Sentinel.

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
python triage_bot.py get-incident incident-123
```

#### Interactive Chat

```bash
python triage_bot.py chat
```

Start an interactive chat session with the triage bot.

Options:
- `--incident-id TEXT`: Load an incident by ID for context

Example:
```bash
python triage_bot.py chat --incident-id incident-123
```

##### Chat Commands

During a chat session, you can use the following commands:

- `/incident [id]`: Load an incident by ID
- `/metrics`: Show security metrics dashboard
- `/help`: Show help message
- `/exit` or `/quit`: End the chat session

#### Security Metrics

```bash
python triage_bot.py metrics
```

Display the security metrics dashboard.

### Examples

#### Workflow Example

1. Login to Azure
```bash
python triage_bot.py login
```

2. List recent incidents
```bash
python triage_bot.py list-incidents
```

3. Get details for a specific incident
```bash
python triage_bot.py get-incident incident-5
```

4. Start a chat session with context for this incident
```bash
python triage_bot.py chat --incident-id incident-5
```

5. During the chat, ask questions about the incident:
```
How would you recommend I triage this incident?
```

6. Check metrics
```
/metrics
```

7. End the session
```
/exit
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**:
   - Ensure you've run `az login` and have an active Azure session
   - Verify that your Azure account has access to the required resources
   - Check that the `.env` file has the correct `AZURE_TENANT_ID`

2. **Connection Issues**:
   - Verify the `MCP_SERVER_URL` in your `.env` file
   - Ensure the MCP server is running and accessible
   - Check your network connection and firewall settings

3. **Permission Errors**:
   - Confirm you have the necessary permissions in Azure AD
   - Verify RBAC assignments for Azure Sentinel and Defender
   - Check the logs for specific permission errors

4. **OpenAI/Azure OpenAI Issues**:
   - If using Azure OpenAI, verify that your `AZURE_OPENAI_DEPLOYMENT` is correct
   - Check that your API keys and endpoints are correctly configured
   - Set `USE_AZURE_OPENAI` to either "true" or "false" as needed

### Log Files

The CLI client writes logs to `cli/logs/triage_bot.log`. Check this file for detailed error information when troubleshooting issues.

### Getting Help

If you encounter issues not covered here, please:
1. Check the detailed error message in the logs
2. Verify your Azure CLI is correctly configured
3. Ensure your Azure account has the necessary permissions
4. Contact support with the error details and log files
