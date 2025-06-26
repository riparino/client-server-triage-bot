# Server Documentation

This document provides comprehensive information about the MCP server component of the triage bot system, including authentication setup and deployment instructions.

## Table of Contents
- [Authentication Setup](#authentication-setup)
  - [Overview](#overview)
  - [Setup Steps](#setup-steps)
  - [How Authentication Works](#how-authentication-works)
  - [Troubleshooting](#troubleshooting)
- [Deployment Guide](#deployment-guide)
  - [Prerequisites](#prerequisites)
  - [Deployment Steps](#deployment-steps)
  - [Configuration](#configuration)
  - [Monitoring and Maintenance](#monitoring-and-maintenance)

---

# Authentication Setup

## Overview

Our architecture uses Azure CLI authentication to provide secure access to Azure resources:

1. The CLI client authenticates the user via `az login` which generates Azure AD tokens
2. These tokens are passed to the Azure Function MCP server
3. The MCP server validates the tokens and uses them to access Azure resources 

## Setup Steps

### 1. Register an Application in Azure AD

First, you need to register an application in Azure AD for the Azure Function:

1. Sign in to the [Azure portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** > **App registrations** > **New registration**
3. Enter a name for the application (e.g., "Triage Bot MCP Server")
4. Select **Accounts in this organizational directory only** for supported account types
5. Leave the Redirect URI blank
6. Click **Register**
7. Note the **Application (client) ID** and **Directory (tenant) ID** for later use

### 2. Set Up API Permissions

1. In your new app registration, navigate to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph** > **Application permissions**
4. Add the following permissions:
   - `SecurityEvents.Read.All`
   - `SecurityIncident.Read.All` 
   - `User.Read.All`
   - `Directory.Read.All`
5. Click **Grant admin consent**

### 3. Create a Client Secret

1. In your app registration, navigate to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and select an expiration period
4. Click **Add**
5. **IMPORTANT**: Copy the secret value immediately as it won't be shown again

### 4. Configure the Azure Function

Update the function app settings with the following values:

```
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_app_registration_client_id
AZURE_CLIENT_SECRET=your_client_secret
```

### 5. Configure Access Control for Azure Resources

Grant appropriate permissions to the managed identity or service principal for accessing Azure Sentinel and Defender:

```bash
# Get the principal ID
principalId=$(az ad sp show --id <your-app-client-id> --query id --output tsv)

# Assign Security Reader role 
az role assignment create --assignee $principalId \
  --role "Security Reader" \
  --scope /subscriptions/<subscription-id>

# Assign Azure Sentinel Contributor role
az role assignment create --assignee $principalId \
  --role "Azure Sentinel Contributor" \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.OperationalInsights/workspaces/<workspace-name>
```

## How Authentication Works

1. **CLI Client Flow**:
   - User runs `az login` via the CLI client
   - CLI gets Azure AD token using Azure CLI
   - Token is passed to the MCP server with each request

2. **MCP Server Flow**: 
   - MCP server validates the user's token
   - If valid, MCP server uses its service principal to access Azure resources
   - Service principal has appropriate RBAC permissions for Azure Sentinel/Defender

## Troubleshooting

Common authentication issues:

1. **Token Expired**: Azure AD tokens expire after 1 hour. The CLI handles refreshing the token automatically.

2. **Insufficient Permissions**: If you see "Unauthorized" or "Access Denied" errors:
   - Verify that the user has sufficient permissions in Azure AD
   - Check that the service principal has the correct role assignments
   - Ensure all required API permissions are granted

3. **Authentication Failure**: If authentication fails:
   - Check that the tenant ID matches between the client and function app
   - Verify the client ID and secret are correct
   - Ensure the Azure Function can reach Azure AD endpoints

---

# Deployment Guide

## Prerequisites

- Azure CLI installed and configured
- Azure Functions Core Tools installed
- An Azure subscription
- VS Code with Azure Functions extension (optional)

## Deployment Steps

### 1. Create Azure Resources

```bash
# Login to Azure
az login

# Create a resource group
az group create --name rg-triage-bot --location eastus

# Create a storage account
az storage account create --name satriagebot --location eastus --resource-group rg-triage-bot --sku Standard_LRS

# Create a function app
az functionapp create --resource-group rg-triage-bot --consumption-plan-location eastus --runtime python --runtime-version 3.9 --functions-version 4 --name func-triage-bot --storage-account satriagebot --os-type linux
```

### 2. Configure Application Settings

```bash
# Set function app settings
az functionapp config appsettings set --name func-triage-bot --resource-group rg-triage-bot --settings \
AZURE_TENANT_ID=your_tenant_id \
AZURE_CLIENT_ID=your_client_id \
AZURE_CLIENT_SECRET=your_client_secret \
APPINSIGHTS_INSTRUMENTATIONKEY=your_app_insights_key \
ALLOWED_USERS=user_id_1,user_id_2
```

### 3. Deploy the Function

#### Using Azure Functions Core Tools:

```bash
cd mcp-server
func azure functionapp publish func-triage-bot
```

#### Using GitHub Actions (CI/CD):

1. Create GitHub secrets for your Azure credentials
2. Use the provided workflow file in `.github/workflows/deploy-function.yml`
3. Push changes to trigger the deployment

### 4. Verify Deployment

```bash
# Test the function
curl -X GET https://func-triage-bot.azurewebsites.net/api/health -H "Authorization: Bearer {your_token}"
```

## Configuration

### Application Settings

Key | Description
--- | ---
`AZURE_TENANT_ID` | Your Azure AD tenant ID
`AZURE_CLIENT_ID` | Application (client) ID for the registered Azure AD app
`AZURE_CLIENT_SECRET` | Client secret for the registered Azure AD app
`ALLOWED_USERS` | Comma-separated list of Azure AD user IDs allowed to access the function (optional)
`SENTINEL_WORKSPACE_ID` | ID of your Azure Sentinel workspace
`SENTINEL_API_VERSION` | API version for Azure Sentinel (e.g., "2022-01-01-preview")
`DEFENDER_API_VERSION` | API version for Microsoft Defender (e.g., "2021-10-01")

## Monitoring and Maintenance

### Monitoring

1. Set up Application Insights for monitoring:
```bash
az monitor app-insights component create --app func-triage-bot --location eastus --resource-group rg-triage-bot --application-type web
```

2. View logs in Azure portal:
   - Navigate to your function app
   - Select "Monitor" in the left menu
   - View function invocations, failures, and performance

### Scaling

The default consumption plan scales automatically based on load. For higher performance:

```bash
# Switch to Premium plan if needed
az functionapp plan create --name premium-plan --resource-group rg-triage-bot --location eastus --sku EP1
az functionapp update --name func-triage-bot --resource-group rg-triage-bot --plan premium-plan
```

### Updating

To update the function app:

```bash
cd mcp-server
func azure functionapp publish func-triage-bot
```

### Troubleshooting Deployment Issues

1. **Deployment Failures**:
   - Check the deployment logs in Azure portal
   - Verify that the function app settings are correct
   - Ensure that all dependencies are included in requirements.txt

2. **Runtime Errors**:
   - Check the function logs in Azure portal
   - Use Application Insights to identify errors
   - Test locally using `func start` before deploying
