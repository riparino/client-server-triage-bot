#!/usr/bin/env python3
"""
Azure Security Incident Triage Bot CLI

A command-line interface for interacting with Azure/Azure Sentinel/Defender to triage incidents
and gather security metrics.
"""

import os
import typer
import json
import asyncio
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
import subprocess
import requests
from datetime import datetime
import dotenv
from openai import AsyncOpenAI

# Load environment variables
dotenv.load_dotenv()

# Initialize Typer app and Rich console
app = typer.Typer(help="Azure Security Incident Triage CLI")
console = Console()

# Global variables
user_info = None
azure_token = None
FUNCTION_APP_URL = os.getenv("FUNCTION_APP_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2023-05-15")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "false").lower() == "true"
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")

# Initialize OpenAI client based on configuration
if USE_AZURE_OPENAI:
    # Azure OpenAI configuration
    client = AsyncOpenAI(
        api_key=OPENAI_API_KEY,
        api_version=OPENAI_API_VERSION,
        azure_endpoint=OPENAI_ENDPOINT,
    )
else:
    # Standard OpenAI configuration
    client = AsyncOpenAI(
        api_key=OPENAI_API_KEY,
    )

async def chat_with_model(messages):
    """Send messages to the OpenAI chat model and get a response."""
    try:
        if USE_AZURE_OPENAI:
            response = await client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                temperature=0.7,
            )
        else:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
            )
        return response.choices[0].message.content
    except Exception as e:
        console.print(f"[bold red]Error communicating with OpenAI API: {str(e)}[/bold red]")
        return "I encountered an error processing your request."

def check_azure_cli_login():
    """Check if user is logged in to Azure CLI."""
    try:
        result = subprocess.run(["az", "account", "show"], capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        console.print(f"[bold red]Error checking Azure CLI login: {str(e)}[/bold red]")
        return None

def get_azure_token():
    """Get an access token from Azure CLI for the Function App with proper scopes."""
    try:
        # Get the Function App URI and client ID from environment
        function_app_resource = os.getenv("FUNCTION_APP_RESOURCE", "api://your-function-app-id")
        client_id = os.getenv("AZURE_CLIENT_ID", "")
        
        # Determine if we should use resource or scope approach
        if function_app_resource.startswith("api://"):
            # Use scope approach for App Registration custom scopes
            # Add basic scope for read access if no specific scope provided
            scope = os.getenv("FUNCTION_APP_SCOPE", f"{function_app_resource}/incidents.read")
            result = subprocess.run(
                ["az", "account", "get-access-token", "--scope", scope, "--client-id", client_id],
                capture_output=True,
                text=True
            )
        else:
            # Fall back to resource approach (legacy)
            result = subprocess.run(
                ["az", "account", "get-access-token", "--resource", function_app_resource],
                capture_output=True,
                text=True
            )
        if result.returncode == 0:
            token_info = json.loads(result.stdout)
            return token_info.get("accessToken")
        return None
    except Exception as e:
        console.print(f"[bold red]Error getting Azure access token: {str(e)}[/bold red]")
        return None

def login_to_azure():
    """Login to Azure using Azure CLI."""
    try:
        console.print("[yellow]Logging in to Azure...[/yellow]")
        subprocess.run(["az", "login"], check=True)
        user_info = check_azure_cli_login()
        token = get_azure_token()
        
        if user_info and token:
            console.print("[green]Successfully logged in to Azure[/green]")
            return user_info, token
        else:
            console.print("[bold red]Failed to get user info or token[/bold red]")
            return None, None
    except Exception as e:
        console.print(f"[bold red]Error logging in to Azure: {str(e)}[/bold red]")
        return None, None

def call_mcp_function(endpoint: str, data: dict):
    """Call the MCP server Azure Function."""
    global azure_token
    
    try:
        # Check if we have a valid token
        if not azure_token:
            # Try to get a new token
            azure_token = get_azure_token()
            if not azure_token:
                console.print("[bold red]No valid Azure token. Please log in first.[/bold red]")
                return {"error": "Authentication required"}
                
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {azure_token}"
        }
        
        response = requests.post(f"{FUNCTION_APP_URL}/{endpoint}", json=data, headers=headers)
        
        # Check if unauthorized (token expired)
        if response.status_code == 401:
            console.print("[yellow]Token expired. Getting a new token...[/yellow]")
            azure_token = get_azure_token()
            if azure_token:
                headers["Authorization"] = f"Bearer {azure_token}"
                response = requests.post(f"{FUNCTION_APP_URL}/{endpoint}", json=data, headers=headers)
            else:
                return {"error": "Failed to refresh authentication token"}
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error calling MCP server: {str(e)}[/bold red]")
        return {"error": str(e)}

def display_incident_details(incident):
    """Display incident details in a formatted table."""
    table = Table(title=f"Incident: {incident['title']}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in incident.items():
        if isinstance(value, dict):
            table.add_row(key, json.dumps(value, indent=2))
        elif isinstance(value, list):
            table.add_row(key, json.dumps(value, indent=2))
        else:
            table.add_row(key, str(value))
    
    console.print(table)

def display_chat_message(role, content):
    """Display a chat message with appropriate formatting."""
    if role == "user":
        console.print(Panel(content, title="You", border_style="blue"))
    elif role == "assistant":
        console.print(Panel(Markdown(content), title="Triage Bot", border_style="green"))
    elif role == "system":
        console.print(Panel(content, title="System", border_style="yellow"))
    else:
        console.print(Panel(content, title=role, border_style="white"))

@app.command()
def login():
    """Login to Azure and authenticate with the triage bot."""
    global user_info, azure_token
    
    # Check if already logged in
    user_info_check = check_azure_cli_login()
    token_check = get_azure_token()
    
    if user_info_check and token_check:
        user_info = user_info_check
        azure_token = token_check
        user_name = user_info.get("user", {}).get("name", "Unknown User")
        console.print(f"[green]Already logged in as: [bold]{user_name}[/bold][/green]")
    else:
        # Need to login
        user_info, azure_token = login_to_azure()
        
    if not user_info or not azure_token:
        console.print("[bold red]Failed to log in to Azure[/bold red]")
        return False
        
    # Validate with MCP server
    console.print("[yellow]Validating authentication with MCP server...[/yellow]")
    response = call_mcp_function("authenticate", {})
    
    if response.get("data") and "user_info" in response.get("data", {}):
        user_name = user_info.get("user", {}).get("name", "Unknown User")
        console.print(f"[green]Successfully authenticated as: [bold]{user_name}[/bold][/green]")
        return True
    else:
        console.print("[bold red]Failed to authenticate with the MCP server[/bold red]")
        console.print(f"[bold yellow]Error: {response.get('error', 'Unknown error')}[/bold yellow]")
        return False

@app.command()
def list_incidents(
    limit: int = typer.Option(10, help="Number of incidents to retrieve"),
    severity: Optional[str] = typer.Option(None, help="Filter by severity (low, medium, high, critical)")
):
    """List recent security incidents from Azure Sentinel."""
    if not check_session():
        return
    
    console.print("[yellow]Fetching incidents from Azure Sentinel...[/yellow]")
    data = {
        "limit": limit,
        "filter": {
            "severity": severity
        } if severity else {}
    }
    
    response = call_mcp_function("incidents/list", data)
    if "incidents" in response:
        incidents = response["incidents"]
        
        table = Table(title="Azure Sentinel Incidents")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Severity", style="red")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="blue")
        
        for incident in incidents:
            table.add_row(
                incident.get("id", "N/A"),
                incident.get("title", "N/A"),
                incident.get("severity", "N/A"),
                incident.get("status", "N/A"),
                incident.get("createdTime", "N/A")
            )
        
        console.print(table)
    else:
        console.print("[bold red]Failed to retrieve incidents[/bold red]")

@app.command()
def get_incident(incident_id: str):
    """Get detailed information about a specific incident."""
    if not check_session():
        return
    
    console.print(f"[yellow]Fetching details for incident {incident_id}...[/yellow]")
    response = call_mcp_function("incidents/get", {"id": incident_id})
    if "incident" in response:
        display_incident_details(response["incident"])
    else:
        console.print("[bold red]Failed to retrieve incident details[/bold red]")

@app.command()
async def chat(incident_id: Optional[str] = None):
    """Start an interactive chat session with the triage bot."""
    if not check_session():
        return
    
    console.print("[bold green]Starting interactive incident triage chat...[/bold green]")
    console.print("Type 'exit' or 'quit' to end the session.")
    
    context = {}
    if incident_id:
        response = call_mcp_function("incidents/get", {"id": incident_id})
        if "incident" in response:
            context["incident"] = response["incident"]
            console.print(f"[green]Loaded context for incident {incident_id}[/green]")
    
    messages = [
        {
            "role": "system", 
            "content": "You are an Azure Security Incident Triage Bot. Your job is to help security analysts investigate and triage incidents. "
                      "You can provide guidance, answer questions about Azure security, and help resolve incidents. "
                      "Be concise, accurate, and helpful."
        }
    ]
    
    # Add context if we have an incident
    if "incident" in context:
        incident_context = f"We are working on incident {incident_id}. Here are the details: {json.dumps(context['incident'], indent=2)}"
        messages.append({"role": "system", "content": incident_context})
        display_chat_message("system", f"Context loaded for incident {incident_id}")
    
    display_chat_message("assistant", "Hello! I'm your Azure Security Incident Triage assistant. How can I help you today?")
    
    while True:
        user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
        
        if user_input.lower() in ["exit", "quit"]:
            console.print("[yellow]Ending chat session...[/yellow]")
            break
        
        messages.append({"role": "user", "content": user_input})
        
        # Execute tool commands
        if user_input.startswith("/"):
            tool_command = user_input[1:].strip().split()
            if len(tool_command) > 0:
                command = tool_command[0]
                args = tool_command[1:]
                
                if command == "incident":
                    if len(args) > 0:
                        incident_id = args[0]
                        response = call_mcp_function("incidents/get", {"id": incident_id})
                        if "incident" in response:
                            context["incident"] = response["incident"]
                            display_incident_details(response["incident"])
                            incident_context = f"We are working on incident {incident_id}. Here are the details: {json.dumps(context['incident'], indent=2)}"
                            messages.append({"role": "system", "content": incident_context})
                        else:
                            display_chat_message("system", f"Failed to retrieve incident {incident_id}")
                elif command == "help":
                    help_text = """
                    Available commands:
                    /incident [id] - Load an incident by ID
                    /metrics - Show security metrics dashboard
                    /help - Show this help message
                    /exit or /quit - End the chat session
                    """
                    display_chat_message("system", help_text)
                    continue
                elif command in ["exit", "quit"]:
                    console.print("[yellow]Ending chat session...[/yellow]")
                    break
                else:
                    display_chat_message("system", f"Unknown command: {command}")
                    continue
        
        # Get AI response
        console.print("[dim]Thinking...[/dim]")
        response = await chat_with_model(messages)
        messages.append({"role": "assistant", "content": response})
        display_chat_message("assistant", response)

def check_session():
    """Check if user is logged in and has a valid Azure token."""
    global user_info, azure_token
    
    if not user_info or not azure_token:
        console.print("[yellow]You are not logged in. Please login first.[/yellow]")
        return login()
        
    # Verify token is still valid
    try:
        response = call_mcp_function("authenticate", {})
        if not response.get("data"):
            console.print("[yellow]Your session has expired. Please login again.[/yellow]")
            return login()
    except Exception:
        console.print("[yellow]Failed to validate session. Please login again.[/yellow]")
        return login()
        
    return True

@app.command()
def metrics():
    """Display security metrics dashboard."""
    if not check_session():
        return
    
    console.print("[yellow]Fetching security metrics...[/yellow]")
    response = call_mcp_function("metrics/dashboard", {})
    if "metrics" in response:
        metrics = response["metrics"]
        
        table = Table(title="Security Metrics Dashboard")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Change", style="yellow")
        
        for metric in metrics:
            change = metric.get("change", "N/A")
            change_style = "green" if change.startswith("+") else "red" if change.startswith("-") else "yellow"
            table.add_row(
                metric.get("name", "N/A"),
                str(metric.get("value", "N/A")),
                f"[{change_style}]{change}[/{change_style}]"
            )
        
        console.print(table)
    else:
        console.print("[bold red]Failed to retrieve security metrics[/bold red]")

@app.callback()
def main():
    """Azure Security Incident Triage Bot CLI."""
    console.print(Panel.fit(
        "[bold blue]Azure Security Incident Triage Bot[/bold blue]\n"
        "[green]A CLI tool for triaging Azure security incidents[/green]",
        border_style="green"
    ))
    
    # Check environment variables
    if not FUNCTION_APP_URL:
        console.print("[bold yellow]Warning: FUNCTION_APP_URL environment variable not set. Please set it in .env file.[/bold yellow]")
    
    if not OPENAI_API_KEY:
        console.print("[bold yellow]Warning: OPENAI_API_KEY environment variable not set. Please set it in .env file.[/bold yellow]")

if __name__ == "__main__":
    app()
