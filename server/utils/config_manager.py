"""
Configuration Manager
Handles application configuration and tenant management.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration and tenant settings."""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Default to config directory relative to server root
            server_dir = Path(__file__).parent.parent
            self.config_dir = server_dir.parent / "config"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_dir.mkdir(exist_ok=True)
        self._tenant_config_file = self.config_dir / "tenants.json"
        self._app_config_file = self.config_dir / "app_config.json"
        
        # Initialize default configurations
        self._init_default_configs()
    
    def _init_default_configs(self):
        """Initialize default configuration files if they don't exist."""
        # Initialize tenant configuration
        if not self._tenant_config_file.exists():
            default_tenants = {
                "tenants": [
                    {
                        "tenant_id": "example-tenant-1",
                        "tenant_name": "Example Tenant 1",
                        "subscription_id": "sub-id-1",
                        "resource_group": "rg-sentinel-1",
                        "workspace_name": "law-sentinel-1",
                        "enabled": True,
                        "description": "Example tenant configuration"
                    },
                    {
                        "tenant_id": "example-tenant-2", 
                        "tenant_name": "Example Tenant 2",
                        "subscription_id": "sub-id-2",
                        "resource_group": "rg-sentinel-2",
                        "workspace_name": "law-sentinel-2",
                        "enabled": True,
                        "description": "Another example tenant configuration"
                    }
                ],
                "default_tenant": "example-tenant-1"
            }
            
            with open(self._tenant_config_file, 'w') as f:
                json.dump(default_tenants, f, indent=2)
            
            logger.info(f"Created default tenant configuration: {self._tenant_config_file}")
        
        # Initialize app configuration
        if not self._app_config_file.exists():
            default_app_config = {
                "server": {
                    "host": "0.0.0.0",
                    "port": 5000,
                    "debug": False
                },
                "authentication": {
                    "method": "azure_cli",
                    "token_cache_duration_minutes": 55
                },
                "sentinel": {
                    "api_version": "2023-02-01",
                    "default_incident_limit": 50,
                    "request_timeout_seconds": 30
                },
                "logging": {
                    "level": "INFO",
                    "file": "logs/server.log",
                    "max_file_size_mb": 10,
                    "backup_count": 5
                },
                "features": {
                    "enable_chat_interface": True,
                    "enable_incident_details": True,
                    "enable_multi_tenant_queries": True
                }
            }
            
            with open(self._app_config_file, 'w') as f:
                json.dump(default_app_config, f, indent=2)
            
            logger.info(f"Created default app configuration: {self._app_config_file}")
    
    def get_app_config(self) -> Dict[str, Any]:
        """Get application configuration."""
        try:
            with open(self._app_config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading app configuration: {str(e)}")
            return {}
    
    def get_tenants(self) -> List[Dict[str, Any]]:
        """Get list of configured tenants."""
        try:
            with open(self._tenant_config_file, 'r') as f:
                config = json.load(f)
                return config.get('tenants', [])
        except Exception as e:
            logger.error(f"Error loading tenant configuration: {str(e)}")
            return []
    
    def get_tenant_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific tenant."""
        tenants = self.get_tenants()
        for tenant in tenants:
            if tenant.get('tenant_id') == tenant_id:
                return tenant
        return None
    
    def get_enabled_tenants(self) -> List[Dict[str, Any]]:
        """Get list of enabled tenants only."""
        tenants = self.get_tenants()
        return [tenant for tenant in tenants if tenant.get('enabled', True)]
    
    def get_default_tenant(self) -> Optional[str]:
        """Get the default tenant ID."""
        try:
            with open(self._tenant_config_file, 'r') as f:
                config = json.load(f)
                return config.get('default_tenant')
        except Exception as e:
            logger.error(f"Error loading default tenant: {str(e)}")
            return None
    
    def add_tenant(self, tenant_config: Dict[str, Any]) -> bool:
        """Add a new tenant configuration."""
        try:
            with open(self._tenant_config_file, 'r') as f:
                config = json.load(f)
            
            # Check if tenant already exists
            existing_tenant_ids = [t.get('tenant_id') for t in config.get('tenants', [])]
            if tenant_config.get('tenant_id') in existing_tenant_ids:
                logger.warning(f"Tenant {tenant_config.get('tenant_id')} already exists")
                return False
            
            config['tenants'].append(tenant_config)
            
            with open(self._tenant_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Added tenant: {tenant_config.get('tenant_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding tenant: {str(e)}")
            return False
    
    def update_tenant(self, tenant_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing tenant configuration."""
        try:
            with open(self._tenant_config_file, 'r') as f:
                config = json.load(f)
            
            tenants = config.get('tenants', [])
            for i, tenant in enumerate(tenants):
                if tenant.get('tenant_id') == tenant_id:
                    tenants[i].update(updates)
                    
                    with open(self._tenant_config_file, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    logger.info(f"Updated tenant: {tenant_id}")
                    return True
            
            logger.warning(f"Tenant {tenant_id} not found for update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating tenant: {str(e)}")
            return False
    
    def remove_tenant(self, tenant_id: str) -> bool:
        """Remove a tenant configuration."""
        try:
            with open(self._tenant_config_file, 'r') as f:
                config = json.load(f)
            
            tenants = config.get('tenants', [])
            original_count = len(tenants)
            
            config['tenants'] = [t for t in tenants if t.get('tenant_id') != tenant_id]
            
            if len(config['tenants']) < original_count:
                with open(self._tenant_config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                logger.info(f"Removed tenant: {tenant_id}")
                return True
            else:
                logger.warning(f"Tenant {tenant_id} not found for removal")
                return False
                
        except Exception as e:
            logger.error(f"Error removing tenant: {str(e)}")
            return False
    
    def validate_tenant_config(self, tenant_config: Dict[str, Any]) -> bool:
        """Validate tenant configuration structure."""
        required_fields = ['tenant_id', 'tenant_name', 'subscription_id', 'resource_group', 'workspace_name']
        
        for field in required_fields:
            if field not in tenant_config or not tenant_config[field]:
                logger.error(f"Missing or empty required field: {field}")
                return False
        
        return True
    
    def get_lighthouse_delegations(self) -> List[Dict[str, Any]]:
        """Get Azure Lighthouse delegation information (placeholder for future implementation)."""
        # This would integrate with Azure Lighthouse APIs to get actual delegation info
        # For now, return configured tenants as placeholder
        return self.get_enabled_tenants()