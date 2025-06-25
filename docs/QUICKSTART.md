# Quick Start Guide

## Prerequisites Check

Before starting, ensure you have:

1. **Python 3.8+** installed
   ```bash
   python3 --version
   ```

2. **PowerShell 5.1+** available
   ```bash
   pwsh --version
   ```

3. **Azure CLI** installed and authenticated
   ```bash
   az --version
   az account show
   ```

## Quick Setup (5 minutes)

### 1. Install Server Dependencies

```bash
cd server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Tenants

Edit `config/tenants.json` with your actual tenant information:

```json
{
  "tenants": [
    {
      "tenant_id": "your-actual-tenant-id",
      "tenant_name": "Your Tenant Name",
      "subscription_id": "your-subscription-id",
      "resource_group": "your-sentinel-rg",
      "workspace_name": "your-sentinel-workspace",
      "enabled": true,
      "description": "Production Sentinel workspace"
    }
  ],
  "default_tenant": "your-actual-tenant-id"
}
```

### 3. Start the Server

```bash
cd server
python app.py
```

The server will start on http://localhost:5000

### 4. Run the Client

Open a new terminal:

```powershell
cd client
.\TriageBot-Client.ps1
```

## First Commands to Try

Once the client is running:

1. **Check status**: `status`
2. **List tenants**: `tenants`
3. **Get incidents**: `incidents`
4. **Get help**: `help`

## Sample Natural Language Queries

- "Show me high severity incidents"
- "List active incidents from the last 24 hours"
- "What are the current security alerts?"

## Troubleshooting

### Server won't start
- Check Python version: `python3 --version`
- Install dependencies: `pip install -r requirements.txt`
- Check port availability: `netstat -an | grep 5000`

### Authentication issues
- Verify Azure CLI login: `az account show`
- Re-authenticate: `az login`
- Check tenant access: `az account list`

### Client connection issues
- Verify server is running: `curl http://localhost:5000/health`
- Check firewall settings
- Try different port: `.\TriageBot-Client.ps1 -ServerUrl "http://localhost:5001"`

## Production Deployment

For production deployment on PAW environments:

1. Use environment variables for configuration
2. Enable HTTPS with proper certificates
3. Configure proper logging
4. Set up monitoring and alerting
5. Use a proper WSGI server like Gunicorn

See README.md for detailed production setup instructions.