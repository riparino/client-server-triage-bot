"""
Startup script for the MCP Server function app.
This runs when the function app starts and validates configuration.
"""

import os
import logging
import sys

# Try to import Azure modules
try:
    from azure.identity import ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient
    HAS_AZURE_MODULES = True
except ImportError:
    HAS_AZURE_MODULES = False

# Import Key Vault utilities
try:
    from key_vault_utils import get_key_vault_client, get_secret
    HAS_KEY_VAULT_UTILS = True
except ImportError:
    HAS_KEY_VAULT_UTILS = False

def validate_configuration():
    """Validate the function app configuration."""
    # Check if running in Azure Functions
    is_azure_functions = os.environ.get("FUNCTIONS_WORKER_RUNTIME") is not None
    logging.info(f"Running in Azure Functions environment: {is_azure_functions}")
    
    # Log authentication flow information
    logging.info("Authentication Flow:")
    logging.info("1. Users authenticate via Azure CLI (az login)")
    logging.info("2. User tokens are passed to this Function App")
    logging.info("3. Function App validates user tokens")
    logging.info("4. Function App uses its managed identity for Azure service access")
    
    # Check for managed identity
    if is_azure_functions:
        logging.info("Verifying managed identity configuration...")
        # We'll only know if it's configured correctly when we actually use it
    else:
        logging.warning("Not running in Azure Functions - managed identity unavailable")
    
    # Check if Key Vault is configured
    key_vault_name = os.environ.get("KEY_VAULT_NAME")
    use_key_vault = os.environ.get("USE_KEY_VAULT", "true").lower() == "true"
    
    if use_key_vault and not key_vault_name:
        logging.warning("USE_KEY_VAULT is true but KEY_VAULT_NAME is not set")
    
    if use_key_vault and key_vault_name:
        logging.info(f"Key Vault configuration: {key_vault_name}")
        
        # Check if we can access Key Vault
        if HAS_AZURE_MODULES and HAS_KEY_VAULT_UTILS:
            try:
                client = get_key_vault_client()
                if client:
                    # Try to get a test secret to validate access
                    tenant_id = get_secret("azure-tenant-id")
                    if tenant_id:
                        logging.info("Successfully connected to Key Vault and retrieved secrets")
                    else:
                        logging.warning("Connected to Key Vault but could not retrieve required secrets")
                else:
                    logging.warning("Failed to create Key Vault client")
            except Exception as e:
                logging.error(f"Error accessing Key Vault: {str(e)}")
        else:
            logging.warning("Azure modules or Key Vault utilities not available")
    
    # Check required configuration
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    if not tenant_id and (not use_key_vault or not key_vault_name):
        logging.warning("AZURE_TENANT_ID is not set and not using Key Vault")
    
    # Validate Managed Identity
    if is_azure_functions and HAS_AZURE_MODULES:
        try:
            credential = ManagedIdentityCredential()
            # Just creating the credential doesn't validate it
            # We'll log the presence but actual validation happens at token acquisition time
            logging.info("Managed Identity credential created successfully")
        except Exception as e:
            logging.error(f"Error creating Managed Identity credential: {str(e)}")

def main():
    """Main entry point for the startup script."""
    logging.info("Starting MCP Server function app")
    validate_configuration()
    logging.info("MCP Server function app startup complete")

# Run the startup script
if __name__ == "__main__":
    main()
