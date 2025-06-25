"""
Microsoft Sentinel Client
Handles communication with Azure Sentinel REST APIs for incident management.
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from auth.azure_auth import AzureAuthHelper

logger = logging.getLogger(__name__)

class SentinelClient:
    """Client for interacting with Microsoft Sentinel APIs."""
    
    def __init__(self):
        self.auth_helper = AzureAuthHelper()
        self.base_url = "https://management.azure.com"
        self.api_version = "2023-02-01"
    
    def _get_headers(self, tenant_id: Optional[str] = None) -> Dict[str, str]:
        """Get HTTP headers with authentication token."""
        token = self.auth_helper.get_access_token(tenant_id)
        if not token:
            raise Exception("Failed to get access token")
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def _build_url(self, subscription_id: str, resource_group: str, workspace_name: str, endpoint: str) -> str:
        """Build Sentinel API URL."""
        base_path = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        workspace_path = f"/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}"
        sentinel_path = f"/providers/Microsoft.SecurityInsights/{endpoint}"
        
        return f"{self.base_url}{base_path}{workspace_path}{sentinel_path}?api-version={self.api_version}"
    
    def get_incidents(self, tenant_id: str, subscription_id: str = None, 
                     resource_group: str = None, workspace_name: str = None,
                     severity: str = "all", status: str = "active", limit: int = 10) -> List[Dict]:
        """
        Get Sentinel incidents from a specific workspace.
        
        Args:
            tenant_id: Azure tenant ID
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            workspace_name: Log Analytics workspace name
            severity: Filter by severity (all, high, medium, low, informational)
            status: Filter by status (active, closed, all)
            limit: Maximum number of incidents to return
        """
        try:
            # For demo purposes, use placeholder values if not provided
            if not subscription_id:
                subscription_id = "00000000-0000-0000-0000-000000000000"
            if not resource_group:
                resource_group = "rg-sentinel"
            if not workspace_name:
                workspace_name = "law-sentinel"
            
            url = self._build_url(subscription_id, resource_group, workspace_name, "incidents")
            headers = self._get_headers(tenant_id)
            
            # Build OData filter
            filters = []
            if status != "all":
                if status == "active":
                    filters.append("properties/status ne 'Closed'")
                elif status == "closed":
                    filters.append("properties/status eq 'Closed'")
            
            if severity != "all":
                severity_map = {
                    "high": "High",
                    "medium": "Medium", 
                    "low": "Low",
                    "informational": "Informational"
                }
                if severity.lower() in severity_map:
                    filters.append(f"properties/severity eq '{severity_map[severity.lower()]}'")
            
            params = {
                '$top': limit,
                '$orderby': 'properties/createdTimeUtc desc'
            }
            
            if filters:
                params['$filter'] = ' and '.join(filters)
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                incidents = data.get('value', [])
                
                # Transform incidents to simplified format
                simplified_incidents = []
                for incident in incidents:
                    props = incident.get('properties', {})
                    simplified_incident = {
                        'id': incident.get('name', ''),
                        'title': props.get('title', 'No title'),
                        'description': props.get('description', ''),
                        'severity': props.get('severity', 'Unknown'),
                        'status': props.get('status', 'Unknown'),
                        'created_time': props.get('createdTimeUtc', ''),
                        'last_updated': props.get('lastModifiedTimeUtc', ''),
                        'incident_number': props.get('incidentNumber', 0),
                        'tactics': props.get('additionalData', {}).get('tactics', []),
                        'alert_count': props.get('additionalData', {}).get('alertsCount', 0),
                        'owner': props.get('owner', {}).get('email', 'Unassigned')
                    }
                    simplified_incidents.append(simplified_incident)
                
                logger.info(f"Retrieved {len(simplified_incidents)} incidents from tenant {tenant_id}")
                return simplified_incidents
            
            elif response.status_code == 401:
                logger.error("Authentication failed - token may be expired")
                return []
            elif response.status_code == 403:
                logger.error("Access denied - insufficient permissions for Sentinel workspace")
                return []
            elif response.status_code == 404:
                logger.error("Sentinel workspace not found")
                return []
            else:
                logger.error(f"Failed to get incidents: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out while getting incidents")
            return []
        except Exception as e:
            logger.error(f"Error getting incidents: {str(e)}")
            return []
    
    def get_incident_details(self, tenant_id: str, incident_id: str,
                           subscription_id: str = None, resource_group: str = None, 
                           workspace_name: str = None) -> Dict:
        """Get detailed information for a specific incident."""
        try:
            # For demo purposes, use placeholder values if not provided
            if not subscription_id:
                subscription_id = "00000000-0000-0000-0000-000000000000"
            if not resource_group:
                resource_group = "rg-sentinel"
            if not workspace_name:
                workspace_name = "law-sentinel"
            
            url = self._build_url(subscription_id, resource_group, workspace_name, f"incidents/{incident_id}")
            headers = self._get_headers(tenant_id)
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                incident = response.json()
                props = incident.get('properties', {})
                
                # Get additional details like alerts and entities
                details = {
                    'id': incident.get('name', ''),
                    'title': props.get('title', ''),
                    'description': props.get('description', ''),
                    'severity': props.get('severity', ''),
                    'status': props.get('status', ''),
                    'created_time': props.get('createdTimeUtc', ''),
                    'last_updated': props.get('lastModifiedTimeUtc', ''),
                    'incident_number': props.get('incidentNumber', 0),
                    'tactics': props.get('additionalData', {}).get('tactics', []),
                    'techniques': props.get('additionalData', {}).get('techniques', []),
                    'alert_count': props.get('additionalData', {}).get('alertsCount', 0),
                    'comment_count': props.get('additionalData', {}).get('commentsCount', 0),
                    'owner': props.get('owner', {}),
                    'labels': props.get('labels', []),
                    'first_activity_time': props.get('firstActivityTimeUtc', ''),
                    'last_activity_time': props.get('lastActivityTimeUtc', ''),
                    'provider_name': props.get('additionalData', {}).get('alertProductNames', []),
                    'related_analytic_rule_ids': props.get('relatedAnalyticRuleIds', [])
                }
                
                logger.info(f"Retrieved details for incident {incident_id}")
                return details
            else:
                logger.error(f"Failed to get incident details: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting incident details: {str(e)}")
            return {}
    
    def get_sample_incidents(self, tenant_id: str, count: int = 5) -> List[Dict]:
        """Get sample incidents for testing purposes."""
        sample_incidents = []
        
        for i in range(count):
            incident = {
                'id': f'sample-incident-{i+1}',
                'title': f'Sample Security Incident #{i+1}',
                'description': f'This is a sample incident for testing purposes - Incident {i+1}',
                'severity': ['High', 'Medium', 'Low'][i % 3],
                'status': ['New', 'Active', 'Closed'][i % 3],
                'created_time': (datetime.utcnow() - timedelta(days=i)).isoformat() + 'Z',
                'last_updated': (datetime.utcnow() - timedelta(hours=i)).isoformat() + 'Z',
                'incident_number': 1000 + i,
                'tactics': ['InitialAccess', 'Persistence', 'Execution'][i % 3:i % 3 + 1],
                'alert_count': (i + 1) * 2,
                'owner': f'analyst{i+1}@contoso.com' if i % 2 == 0 else 'Unassigned'
            }
            sample_incidents.append(incident)
        
        logger.info(f"Generated {count} sample incidents for tenant {tenant_id}")
        return sample_incidents