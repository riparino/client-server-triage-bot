# Azure Sentinel Triage Bot

A client-server architecture application that helps security analysts triage Microsoft Sentinel incidents across multiple Azure tenants. The application is designed to run from Privileged Access Workstation (PAW) VMs in Azure and leverages Azure Lighthouse delegations for multi-tenant access.

## Architecture Overview

```
┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│                     │       │                     │       │                     │
│  PowerShell Client  │◄─────►│   Python Server     │◄─────►│  Azure Sentinel     │
│                     │  REST │                     │  APIs │                     │
│ • Interactive Chat  │  API  │ • Flask Web Server  │       │ • Multiple Tenants  │
│ • Command Interface │       │ • Auth Management   │       │ • Incident Data     │
│ • Tenant Switching  │       │ • API Orchestration │       │ • Lighthouse Access │
│                     │       │                     │       │                     │
└─────────────────────┘       └─────────────────────┘       └─────────────────────┘
```

### Key Components

- **Client**: PowerShell-based interactive interface for security analysts
- **Server**: Python Flask API that handles authentication and Azure Sentinel integration
- **Configuration**: JSON-based tenant and application configuration management
- **Authentication**: Azure CLI-based authentication leveraging existing z-account privileges

## Features

- 🔐 **Multi-tenant Support**: Access Sentinel data across ~70 tenants using Azure Lighthouse
- 💬 **Interactive Chat**: Natural language queries for incident information
- 🔑 **CLI Authentication**: Leverages existing Azure CLI authentication (z-account)
- 📊 **Incident Management**: Query, filter, and analyze security incidents
- ⚡ **Real-time Data**: Direct integration with Azure Sentinel REST APIs
- 🛡️ **PAW Compatible**: Designed for Privileged Access Workstation environments

## Prerequisites

### Server Requirements
- Python 3.8+
- Azure CLI installed and configured
- Access to Azure Sentinel workspaces
- Network connectivity to Azure APIs

### Client Requirements
- PowerShell 5.1+
- Network access to the Python server
- Azure CLI (for authentication)

### Azure Requirements
- Azure Lighthouse delegations configured for target tenants
- Proper RBAC permissions for Sentinel access
- Valid Azure authentication (z-account privileges)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/riparino/client-server-triage-bot.git
cd client-server-triage-bot
```

### 2. Set Up the Python Server

```bash
cd server
pip install -r requirements.txt
```

### 3. Configure Tenants

Edit `config/tenants.json` to add your Azure tenants:

```json
{
  "tenants": [
    {
      "tenant_id": "your-tenant-id",
      "tenant_name": "Production Tenant",
      "subscription_id": "your-subscription-id",
      "resource_group": "rg-sentinel",
      "workspace_name": "law-sentinel-prod",
      "enabled": true,
      "description": "Production environment Sentinel workspace"
    }
  ],
  "default_tenant": "your-tenant-id"
}
```

### 4. Configure Environment Variables

Copy and customize the environment configuration:

```bash
cp config/.env.example config/.env
# Edit config/.env with your specific settings
```

## Usage

### Starting the Server

```bash
cd server
python app.py
```

The server will start on `http://localhost:5000` by default.

### Running the PowerShell Client

```powershell
cd client
.\TriageBot-Client.ps1
```

For remote servers:
```powershell
.\TriageBot-Client.ps1 -ServerUrl "http://your-server:5000"
```

### Interactive Commands

Once the client is running, you can use these commands:

#### Basic Commands
- `help` - Show available commands
- `status` - Check connection and authentication status
- `tenants` - List available tenants
- `exit` - Exit the application

#### Tenant Management
- `tenant <tenant-id>` - Switch to a specific tenant
- `tenant` - Show current tenant

#### Incident Queries
- `incidents` - Get recent incidents from current tenant
- `incidents <tenant-id>` - Get incidents from specific tenant
- `incidents high` - Filter high severity incidents
- `incident <incident-id>` - Get detailed incident information

#### Natural Language Queries
You can also use natural language queries:
- "Show me high severity incidents"
- "List active incidents from the last 24 hours"
- "What are the current security alerts?"
- "Get incident details for ID 12345"

## Configuration

### Server Configuration (`config/app_config.json`)

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  },
  "authentication": {
    "method": "azure_cli",
    "token_cache_duration_minutes": 55
  },
  "sentinel": {
    "api_version": "2023-02-01",
    "default_incident_limit": 50,
    "request_timeout_seconds": 30
  }
}
```

### Client Configuration (`config/client_config.json`)

```json
{
  "client": {
    "name": "Azure Sentinel Triage Bot Client",
    "default_server_url": "http://localhost:5000",
    "connection_timeout_seconds": 30
  },
  "display": {
    "show_timestamps": true,
    "max_description_length": 100
  }
}
```

## API Endpoints

The server exposes the following REST API endpoints:

### Health Check
- `GET /health` - Server health status

### Authentication
- `GET /api/auth/status` - Check authentication status

### Tenant Management
- `GET /api/tenants` - List available tenants

### Incident Management
- `GET /api/incidents` - Get incidents with filtering
  - Parameters: `tenant_id`, `severity`, `status`, `limit`
- `GET /api/incidents/{id}/details` - Get incident details
  - Parameters: `tenant_id`

### Chat Interface
- `POST /api/chat` - Process natural language queries
  - Body: `{"query": "your query", "tenant_id": "optional"}`

## Development

### Server Development

```bash
cd server
pip install -r requirements.txt
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

### Adding New Tenants

Use the configuration manager to add tenants programmatically:

```python
from utils.config_manager import ConfigManager

config_manager = ConfigManager()
new_tenant = {
    "tenant_id": "new-tenant-id",
    "tenant_name": "New Tenant",
    "subscription_id": "subscription-id",
    "resource_group": "resource-group",
    "workspace_name": "workspace-name",
    "enabled": True
}

config_manager.add_tenant(new_tenant)
```

### Extending the Client

The PowerShell client can be extended with additional commands by modifying the `Invoke-Command` function in `TriageBot-Client.ps1`.

## Security Considerations

- 🔐 **Authentication**: Uses Azure CLI authentication - ensure proper z-account configuration
- 🛡️ **Network Security**: Run on isolated PAW networks with appropriate firewall rules
- 🔒 **Access Control**: Leverage Azure RBAC for fine-grained access control
- 📝 **Audit Logging**: All API calls are logged for security audit purposes
- 🚫 **Credential Storage**: No credentials stored in configuration files

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   ```bash
   # Re-authenticate with Azure CLI
   az login
   az account list
   ```

2. **Connection Issues**
   ```bash
   # Test server connectivity
   curl http://localhost:5000/health
   ```

3. **Permission Errors**
   - Verify Azure RBAC permissions for Sentinel workspaces
   - Check Azure Lighthouse delegation status
   - Ensure z-account has appropriate privileges

### Logging

Server logs are available in:
- Console output (when running in debug mode)
- `logs/server.log` (when configured)

Client logs can be enabled with:
```powershell
$VerbosePreference = "Continue"
.\TriageBot-Client.ps1 -Verbose
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review server and client logs
3. Open an issue on GitHub with detailed information
