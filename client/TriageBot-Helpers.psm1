# Azure Sentinel Triage Bot - PowerShell Helper Functions
# Additional utility functions for the triage bot client

<#
.SYNOPSIS
    Helper functions for Azure Sentinel Triage Bot Client
.DESCRIPTION  
    This module provides additional utility functions for working with
    the Azure Sentinel Triage Bot, including authentication helpers,
    data formatting functions, and configuration management.
#>

function Test-AzureCliAuthentication {
    <#
    .SYNOPSIS
        Test if Azure CLI is properly authenticated
    #>
    try {
        $account = az account show --output json 2>$null | ConvertFrom-Json
        if ($account) {
            Write-Host "✓ Authenticated as: $($account.user.name)" -ForegroundColor Green
            Write-Host "  Subscription: $($account.name)" -ForegroundColor Gray
            Write-Host "  Tenant: $($account.tenantId)" -ForegroundColor Gray
            return $true
        }
    } catch {
        Write-Host "✗ Azure CLI authentication failed" -ForegroundColor Red
        Write-Host "  Please run 'az login' to authenticate" -ForegroundColor Yellow
        return $false
    }
    return $false
}

function Format-IncidentTable {
    <#
    .SYNOPSIS
        Format incidents as a table for better readability
    #>
    param(
        [Parameter(Mandatory)]
        [array]$Incidents
    )
    
    if (-not $Incidents -or $Incidents.Count -eq 0) {
        Write-Host "No incidents to display." -ForegroundColor Yellow
        return
    }
    
    # Create custom objects for table formatting
    $tableData = $Incidents | ForEach-Object {
        [PSCustomObject]@{
            'ID' = $_.incident_number
            'Title' = if ($_.title.Length -gt 40) { $_.title.Substring(0, 37) + "..." } else { $_.title }
            'Severity' = $_.severity
            'Status' = $_.status
            'Alerts' = $_.alert_count
            'Created' = ([DateTime]$_.created_time).ToString("MM/dd HH:mm")
            'Owner' = if ($_.owner -eq 'Unassigned') { '-' } else { $_.owner.Split('@')[0] }
        }
    }
    
    # Display as table
    $tableData | Format-Table -AutoSize
}

function Export-IncidentReport {
    <#
    .SYNOPSIS
        Export incidents to CSV file
    #>
    param(
        [Parameter(Mandatory)]
        [array]$Incidents,
        
        [string]$OutputPath = "incidents_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
    )
    
    try {
        $Incidents | Export-Csv -Path $OutputPath -NoTypeInformation
        Write-Host "✓ Report exported to: $OutputPath" -ForegroundColor Green
        return $OutputPath
    } catch {
        Write-Error "Failed to export report: $($_.Exception.Message)"
        return $null
    }
}

function Get-IncidentStatistics {
    <#
    .SYNOPSIS
        Calculate and display incident statistics
    #>
    param(
        [Parameter(Mandatory)]
        [array]$Incidents
    )
    
    if (-not $Incidents -or $Incidents.Count -eq 0) {
        Write-Host "No incidents for statistics." -ForegroundColor Yellow
        return
    }
    
    # Calculate statistics
    $total = $Incidents.Count
    $high = ($Incidents | Where-Object { $_.severity -eq 'High' }).Count
    $medium = ($Incidents | Where-Object { $_.severity -eq 'Medium' }).Count
    $low = ($Incidents | Where-Object { $_.severity -eq 'Low' }).Count
    $active = ($Incidents | Where-Object { $_.status -ne 'Closed' }).Count
    $closed = ($Incidents | Where-Object { $_.status -eq 'Closed' }).Count
    $unassigned = ($Incidents | Where-Object { $_.owner -eq 'Unassigned' }).Count
    
    # Display statistics
    Write-Host "`nIncident Statistics:" -ForegroundColor Cyan
    Write-Host "===================" -ForegroundColor Cyan
    Write-Host "Total Incidents: $total" -ForegroundColor White
    Write-Host ""
    Write-Host "By Severity:" -ForegroundColor Yellow
    Write-Host "  High:   $high" -ForegroundColor Red
    Write-Host "  Medium: $medium" -ForegroundColor Yellow  
    Write-Host "  Low:    $low" -ForegroundColor Green
    Write-Host ""
    Write-Host "By Status:" -ForegroundColor Yellow
    Write-Host "  Active: $active" -ForegroundColor White
    Write-Host "  Closed: $closed" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Assignment:" -ForegroundColor Yellow
    Write-Host "  Unassigned: $unassigned" -ForegroundColor Red
    Write-Host "  Assigned:   $($total - $unassigned)" -ForegroundColor Green
}

function Show-ServerHealth {
    <#
    .SYNOPSIS
        Display detailed server health information
    #>
    param(
        [string]$ServerUrl = "http://localhost:5000"
    )
    
    try {
        $healthResponse = Invoke-RestMethod -Uri "$ServerUrl/health" -Method Get -Timeout 10
        $authResponse = Invoke-RestMethod -Uri "$ServerUrl/api/auth/status" -Method Get -Timeout 10
        
        Write-Host "`nServer Health Status:" -ForegroundColor Cyan
        Write-Host "=====================" -ForegroundColor Cyan
        Write-Host "Server URL: $ServerUrl" -ForegroundColor White
        Write-Host "Status: " -NoNewline -ForegroundColor White
        
        if ($healthResponse.status -eq "healthy") {
            Write-Host "✓ Healthy" -ForegroundColor Green
        } else {
            Write-Host "✗ Unhealthy" -ForegroundColor Red
        }
        
        Write-Host "Version: $($healthResponse.version)" -ForegroundColor White
        Write-Host "Last Check: $($healthResponse.timestamp)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Authentication: " -NoNewline -ForegroundColor White
        
        if ($authResponse.authenticated) {
            Write-Host "✓ Connected" -ForegroundColor Green
        } else {
            Write-Host "✗ Not authenticated" -ForegroundColor Red
        }
        
    } catch {
        Write-Host "`nServer Health Status:" -ForegroundColor Cyan
        Write-Host "=====================" -ForegroundColor Cyan
        Write-Host "Server URL: $ServerUrl" -ForegroundColor White
        Write-Host "Status: ✗ Unreachable" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Start-TriageBotClient {
    <#
    .SYNOPSIS
        Simplified function to start the triage bot client
    #>
    param(
        [string]$ServerUrl = "http://localhost:5000",
        [switch]$CheckHealth
    )
    
    if ($CheckHealth) {
        Show-ServerHealth -ServerUrl $ServerUrl
        Write-Host ""
    }
    
    # Check Azure CLI authentication
    if (-not (Test-AzureCliAuthentication)) {
        Write-Host "Please authenticate with Azure CLI first:" -ForegroundColor Yellow
        Write-Host "  az login" -ForegroundColor White
        return
    }
    
    Write-Host ""
    Write-Host "Starting Triage Bot Client..." -ForegroundColor Green
    
    # Get the directory of this script to find the main client script
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $clientScript = Join-Path $scriptDir "TriageBot-Client.ps1"
    
    if (Test-Path $clientScript) {
        & $clientScript -ServerUrl $ServerUrl
    } else {
        Write-Error "Could not find TriageBot-Client.ps1 in $scriptDir"
    }
}

# Export functions for use in other scripts
Export-ModuleMember -Function Test-AzureCliAuthentication, Format-IncidentTable, Export-IncidentReport, Get-IncidentStatistics, Show-ServerHealth, Start-TriageBotClient