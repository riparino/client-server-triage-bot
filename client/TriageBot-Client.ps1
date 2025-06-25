#Requires -Version 5.1

<#
.SYNOPSIS
    Azure Sentinel Triage Bot Client
    Interactive PowerShell client for querying Sentinel incidents across multiple tenants.

.DESCRIPTION
    This script provides an interactive chat interface for querying Azure Sentinel incidents
    through a Python Flask server. It supports multi-tenant operations using Azure Lighthouse
    delegations and CLI-based authentication.

.PARAMETER ServerUrl
    Base URL of the triage bot server (default: http://localhost:5000)

.PARAMETER ConfigPath
    Path to client configuration file (default: ../config/client_config.json)

.EXAMPLE
    .\TriageBot-Client.ps1
    Start the interactive client with default settings

.EXAMPLE
    .\TriageBot-Client.ps1 -ServerUrl "http://triagebot-server:5000"
    Connect to a remote server instance
#>

param(
    [string]$ServerUrl = "http://localhost:5000",
    [string]$ConfigPath = "../config/client_config.json"
)

# Global variables
$Script:ServerBaseUrl = $ServerUrl.TrimEnd('/')
$Script:ApiBase = "$Script:ServerBaseUrl/api"
$Script:SessionData = @{
    CurrentTenant = $null
    LastQuery = $null
    CommandHistory = @()
}

# Import required modules
try {
    Import-Module Microsoft.PowerShell.Utility -Force
    Import-Module Microsoft.PowerShell.Management -Force
} catch {
    Write-Warning "Failed to import required modules: $($_.Exception.Message)"
}

function Initialize-Client {
    <#
    .SYNOPSIS
        Initialize the triage bot client
    #>
    
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "Azure Sentinel Triage Bot Client" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host ""
    
    # Check server connectivity
    Write-Host "Checking server connectivity..." -ForegroundColor Yellow
    if (Test-ServerConnection) {
        Write-Host "✓ Connected to server: $Script:ServerBaseUrl" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to connect to server: $Script:ServerBaseUrl" -ForegroundColor Red
        Write-Host "Please ensure the server is running and accessible." -ForegroundColor Red
        return $false
    }
    
    # Check authentication status
    Write-Host "Checking authentication status..." -ForegroundColor Yellow
    $authStatus = Get-AuthenticationStatus
    if ($authStatus.authenticated) {
        Write-Host "✓ Authentication successful" -ForegroundColor Green
    } else {
        Write-Host "✗ Authentication failed" -ForegroundColor Red
        Write-Host "Please run 'az login' to authenticate with Azure CLI." -ForegroundColor Red
        return $false
    }
    
    # Load available tenants
    Write-Host "Loading available tenants..." -ForegroundColor Yellow
    $tenants = Get-AvailableTenants
    if ($tenants -and $tenants.Count -gt 0) {
        Write-Host "✓ Found $($tenants.Count) available tenants" -ForegroundColor Green
        
        # Display tenant list
        Write-Host "`nAvailable Tenants:" -ForegroundColor Cyan
        for ($i = 0; $i -lt $tenants.Count; $i++) {
            $tenant = $tenants[$i]
            Write-Host "  [$($i + 1)] $($tenant.tenant_name) ($($tenant.tenant_id))" -ForegroundColor White
        }
    } else {
        Write-Host "⚠ No tenants found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    return $true
}

function Test-ServerConnection {
    <#
    .SYNOPSIS
        Test connectivity to the triage bot server
    #>
    
    try {
        $response = Invoke-RestMethod -Uri "$Script:ServerBaseUrl/health" -Method Get -Timeout 10
        return $response.status -eq "healthy"
    } catch {
        Write-Verbose "Server connection test failed: $($_.Exception.Message)"
        return $false
    }
}

function Get-AuthenticationStatus {
    <#
    .SYNOPSIS
        Check authentication status with the server
    #>
    
    try {
        $response = Invoke-RestMethod -Uri "$Script:ApiBase/auth/status" -Method Get -Timeout 10
        return $response
    } catch {
        Write-Verbose "Auth status check failed: $($_.Exception.Message)"
        return @{ authenticated = $false }
    }
}

function Get-AvailableTenants {
    <#
    .SYNOPSIS
        Get list of available tenants from the server
    #>
    
    try {
        $response = Invoke-RestMethod -Uri "$Script:ApiBase/tenants" -Method Get -Timeout 15
        return $response.tenants
    } catch {
        Write-Verbose "Failed to get tenants: $($_.Exception.Message)"
        return @()
    }
}

function Get-Incidents {
    <#
    .SYNOPSIS
        Get incidents from a specific tenant
    #>
    param(
        [Parameter(Mandatory)]
        [string]$TenantId,
        
        [string]$Severity = "all",
        [string]$Status = "active", 
        [int]$Limit = 10
    )
    
    try {
        $params = @{
            tenant_id = $TenantId
            severity = $Severity
            status = $Status
            limit = $Limit
        }
        
        $queryString = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&"
        $uri = "$Script:ApiBase/incidents?$queryString"
        
        Write-Host "Querying incidents from tenant: $TenantId..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri $uri -Method Get -Timeout 30
        
        return $response
    } catch {
        Write-Error "Failed to get incidents: $($_.Exception.Message)"
        return $null
    }
}

function Get-IncidentDetails {
    <#
    .SYNOPSIS
        Get detailed information for a specific incident
    #>
    param(
        [Parameter(Mandatory)]
        [string]$TenantId,
        
        [Parameter(Mandatory)]
        [string]$IncidentId
    )
    
    try {
        $uri = "$Script:ApiBase/incidents/$IncidentId/details?tenant_id=$TenantId"
        
        Write-Host "Getting details for incident: $IncidentId..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri $uri -Method Get -Timeout 30
        
        return $response
    } catch {
        Write-Error "Failed to get incident details: $($_.Exception.Message)"
        return $null
    }
}

function Send-ChatQuery {
    <#
    .SYNOPSIS
        Send a natural language query to the chat interface
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Query,
        
        [string]$TenantId = $null
    )
    
    try {
        $body = @{
            query = $Query
        }
        
        if ($TenantId) {
            $body.tenant_id = $TenantId
        }
        
        $jsonBody = $body | ConvertTo-Json
        
        Write-Host "Processing query: $Query" -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri "$Script:ApiBase/chat" -Method Post -Body $jsonBody -ContentType "application/json" -Timeout 30
        
        return $response
    } catch {
        Write-Error "Failed to process chat query: $($_.Exception.Message)"
        return $null
    }
}

function Show-IncidentSummary {
    <#
    .SYNOPSIS
        Display a formatted summary of incidents
    #>
    param(
        [Parameter(Mandatory)]
        [object]$IncidentData
    )
    
    if (-not $IncidentData.incidents -or $IncidentData.incidents.Count -eq 0) {
        Write-Host "No incidents found." -ForegroundColor Yellow
        return
    }
    
    Write-Host "`nIncident Summary:" -ForegroundColor Cyan
    Write-Host "=" * 50 -ForegroundColor Cyan
    
    foreach ($incident in $IncidentData.incidents) {
        $severityColor = switch ($incident.severity) {
            "High" { "Red" }
            "Medium" { "Yellow" }
            "Low" { "Green" }
            default { "White" }
        }
        
        Write-Host "`n[$($incident.incident_number)] $($incident.title)" -ForegroundColor White
        Write-Host "  Severity: " -NoNewline -ForegroundColor Gray
        Write-Host $incident.severity -ForegroundColor $severityColor
        Write-Host "  Status: $($incident.status)" -ForegroundColor Gray
        Write-Host "  Created: $($incident.created_time)" -ForegroundColor Gray
        Write-Host "  Alerts: $($incident.alert_count)" -ForegroundColor Gray
        
        if ($incident.description) {
            $shortDesc = if ($incident.description.Length -gt 100) {
                $incident.description.Substring(0, 100) + "..."
            } else {
                $incident.description
            }
            Write-Host "  Description: $shortDesc" -ForegroundColor Gray
        }
    }
    
    Write-Host "`nTotal incidents: $($IncidentData.count)" -ForegroundColor Cyan
}

function Show-Commands {
    <#
    .SYNOPSIS
        Display available commands
    #>
    
    Write-Host "`nAvailable Commands:" -ForegroundColor Cyan
    Write-Host "==================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Basic Commands:" -ForegroundColor Yellow
    Write-Host "  help, h                    - Show this help message"
    Write-Host "  exit, quit, q              - Exit the application"
    Write-Host "  clear, cls                 - Clear the screen"
    Write-Host "  status                     - Show connection and auth status"
    Write-Host ""
    Write-Host "Tenant Commands:" -ForegroundColor Yellow
    Write-Host "  tenants                    - List available tenants"
    Write-Host "  tenant <id>                - Switch to specific tenant"
    Write-Host ""
    Write-Host "Incident Commands:" -ForegroundColor Yellow
    Write-Host "  incidents [tenant_id]      - Get recent incidents"
    Write-Host "  incidents high [tenant_id] - Get high severity incidents"
    Write-Host "  incident <id> [tenant_id]  - Get incident details"
    Write-Host ""
    Write-Host "Chat Commands:" -ForegroundColor Yellow
    Write-Host "  Just type natural language queries like:"
    Write-Host "  - 'Show me high severity incidents'"
    Write-Host "  - 'List active incidents from last 24 hours'"
    Write-Host "  - 'What are the current security alerts?'"
    Write-Host ""
}

function Start-InteractiveSession {
    <#
    .SYNOPSIS
        Start the interactive chat session
    #>
    
    Write-Host "`nStarting interactive session..." -ForegroundColor Green
    Write-Host "Type 'help' for available commands or enter natural language queries." -ForegroundColor Gray
    Write-Host "Type 'exit' to quit.`n" -ForegroundColor Gray
    
    while ($true) {
        # Show prompt
        $prompt = if ($Script:SessionData.CurrentTenant) {
            "[$($Script:SessionData.CurrentTenant)] > "
        } else {
            "> "
        }
        
        Write-Host $prompt -NoNewline -ForegroundColor Green
        $input = Read-Host
        
        # Handle empty input
        if ([string]::IsNullOrWhiteSpace($input)) {
            continue
        }
        
        # Add to command history
        $Script:SessionData.CommandHistory += $input
        $Script:SessionData.LastQuery = $input
        
        # Parse and execute command
        $result = Invoke-Command -InputObject $input
        
        # Check if user wants to exit
        if ($result -eq "EXIT") {
            break
        }
    }
}

function Invoke-Command {
    <#
    .SYNOPSIS
        Parse and execute user commands
    #>
    param(
        [Parameter(Mandatory)]
        [string]$InputObject
    )
    
    $command = $InputObject.Trim().ToLower()
    $parts = $command -split '\s+' | Where-Object { $_ -ne '' }
    
    if ($parts.Count -eq 0) {
        return
    }
    
    $mainCommand = $parts[0]
    
    switch ($mainCommand) {
        { $_ -in @("help", "h") } {
            Show-Commands
        }
        
        { $_ -in @("exit", "quit", "q") } {
            Write-Host "Goodbye!" -ForegroundColor Green
            return "EXIT"
        }
        
        { $_ -in @("clear", "cls") } {
            Clear-Host
            Write-Host "Azure Sentinel Triage Bot Client" -ForegroundColor Cyan
        }
        
        "status" {
            Write-Host "Server: $Script:ServerBaseUrl" -ForegroundColor White
            $authStatus = Get-AuthenticationStatus
            Write-Host "Authentication: " -NoNewline -ForegroundColor White
            if ($authStatus.authenticated) {
                Write-Host "✓ Connected" -ForegroundColor Green
            } else {
                Write-Host "✗ Not authenticated" -ForegroundColor Red
            }
            Write-Host "Current Tenant: $($Script:SessionData.CurrentTenant ?? 'None')" -ForegroundColor White
        }
        
        "tenants" {
            $tenants = Get-AvailableTenants
            if ($tenants) {
                Write-Host "`nAvailable Tenants:" -ForegroundColor Cyan
                for ($i = 0; $i -lt $tenants.Count; $i++) {
                    $tenant = $tenants[$i]
                    $marker = if ($tenant.tenant_id -eq $Script:SessionData.CurrentTenant) { " (current)" } else { "" }
                    Write-Host "  [$($i + 1)] $($tenant.tenant_name) ($($tenant.tenant_id))$marker" -ForegroundColor White
                }
            } else {
                Write-Host "No tenants available." -ForegroundColor Yellow
            }
        }
        
        "tenant" {
            if ($parts.Count -gt 1) {
                $Script:SessionData.CurrentTenant = $parts[1]
                Write-Host "Switched to tenant: $($parts[1])" -ForegroundColor Green
            } else {
                Write-Host "Usage: tenant <tenant_id>" -ForegroundColor Yellow
            }
        }
        
        "incidents" {
            $tenantId = if ($parts.Count -gt 1) { $parts[1] } else { $Script:SessionData.CurrentTenant }
            $severity = if ($parts.Count -gt 2) { $parts[2] } else { "all" }
            
            if (-not $tenantId) {
                Write-Host "Please specify a tenant ID or set a current tenant." -ForegroundColor Yellow
                return
            }
            
            $incidents = Get-Incidents -TenantId $tenantId -Severity $severity
            if ($incidents) {
                Show-IncidentSummary -IncidentData $incidents
            }
        }
        
        "incident" {
            if ($parts.Count -lt 2) {
                Write-Host "Usage: incident <incident_id> [tenant_id]" -ForegroundColor Yellow
                return
            }
            
            $incidentId = $parts[1]
            $tenantId = if ($parts.Count -gt 2) { $parts[2] } else { $Script:SessionData.CurrentTenant }
            
            if (-not $tenantId) {
                Write-Host "Please specify a tenant ID or set a current tenant." -ForegroundColor Yellow
                return
            }
            
            $details = Get-IncidentDetails -TenantId $tenantId -IncidentId $incidentId
            if ($details) {
                Write-Host "`nIncident Details:" -ForegroundColor Cyan
                Write-Host "=================" -ForegroundColor Cyan
                $details | Format-List
            }
        }
        
        default {
            # Treat as natural language query
            $response = Send-ChatQuery -Query $InputObject -TenantId $Script:SessionData.CurrentTenant
            if ($response) {
                Write-Host "`nResponse:" -ForegroundColor Cyan
                Write-Host $response.response -ForegroundColor White
                
                if ($response.suggestions) {
                    Write-Host "`nSuggestions:" -ForegroundColor Yellow
                    foreach ($suggestion in $response.suggestions) {
                        Write-Host "  • $suggestion" -ForegroundColor Gray
                    }
                }
            }
        }
    }
}

# Main execution
try {
    if (Initialize-Client) {
        Start-InteractiveSession
    } else {
        Write-Host "Failed to initialize client. Exiting." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Error "An unexpected error occurred: $($_.Exception.Message)"
    exit 1
}