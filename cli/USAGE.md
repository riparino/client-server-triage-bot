# [DEPRECATED] CLI Usage Instructions

⚠️ **NOTE: This document is deprecated. Please refer to the [Client Documentation](../docs/CLIENT.md) instead.**

This document provides detailed instructions on how to use the Azure Security Incident Triage CLI tool.

## Available Commands

### Login

```bash
python triage_bot.py login
```

Authenticate with Azure using Azure CLI and obtain a session token for the MCP server.

### List Incidents

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

### Get Incident Details

```bash
python triage_bot.py get-incident INCIDENT_ID
```

Get detailed information about a specific incident.

Example:
```bash
python triage_bot.py get-incident incident-123
```

### Interactive Chat

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

#### Chat Commands

During a chat session, you can use the following commands:

- `/incident [id]`: Load an incident by ID
- `/metrics`: Show security metrics dashboard
- `/help`: Show help message
- `/exit` or `/quit`: End the chat session

### Security Metrics

```bash
python triage_bot.py metrics
```

Display the security metrics dashboard.

## Examples

### Workflow Example

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
