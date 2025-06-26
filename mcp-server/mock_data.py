"""
Mock data utilities for development and testing.
"""

import random
import datetime
from typing import Dict, Any, List
import uuid

# Mock incident severity levels
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]

# Mock incident status
INCIDENT_STATUSES = ["New", "Active", "Investigating", "Resolved", "Closed"]

# Mock incident types
INCIDENT_TYPES = [
    "Suspicious sign-in activity",
    "Malware detected",
    "Suspicious resource deployment",
    "Unusual network activity",
    "Data exfiltration",
    "Privilege escalation",
    "Brute force attack"
]

def generate_mock_incidents(limit: int = 10, filter_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Generate mock incident data for testing.
    
    Args:
        limit: Number of incidents to generate
        filter_params: Optional filtering parameters
        
    Returns:
        List of mock incidents
    """
    filter_params = filter_params or {}
    severity = filter_params.get("severity")
    status = filter_params.get("status")
    date_from = filter_params.get("date_from")
    date_to = filter_params.get("date_to")
    
    incidents = []
    
    for i in range(limit):
        # Generate random incident
        incident_severity = severity or random.choice(SEVERITY_LEVELS)
        incident_status = status or random.choice(INCIDENT_STATUSES)
        
        # Generate random date in the past 7 days
        days_ago = random.randint(0, 7)
        incident_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        
        # Skip if doesn't match date filter
        if date_from and incident_date < datetime.datetime.fromisoformat(date_from):
            continue
        if date_to and incident_date > datetime.datetime.fromisoformat(date_to):
            continue
            
        incident_id = str(uuid.uuid4())
        
        incident = {
            "id": incident_id,
            "title": f"{random.choice(INCIDENT_TYPES)} - {incident_id[:8]}",
            "severity": incident_severity,
            "status": incident_status,
            "created": incident_date.isoformat(),
            "assignedTo": "unassigned" if random.random() < 0.3 else f"user{random.randint(1, 5)}@example.com",
            "type": random.choice(INCIDENT_TYPES),
            "resourceName": f"vm-{random.randint(1000, 9999)}",
            "subscriptionId": f"subscription-{random.randint(1, 5)}"
        }
        
        incidents.append(incident)
    
    return incidents

def generate_mock_incident_detail(incident_id: str) -> Dict[str, Any]:
    """
    Generate detailed mock incident data for a specific incident ID.
    
    Args:
        incident_id: The incident ID to generate details for
        
    Returns:
        Detailed incident information
    """
    # Basic incident information
    incident = {
        "id": incident_id,
        "title": f"{random.choice(INCIDENT_TYPES)} - {incident_id[:8]}",
        "severity": random.choice(SEVERITY_LEVELS),
        "status": random.choice(INCIDENT_STATUSES),
        "created": (datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 7))).isoformat(),
        "assignedTo": "unassigned" if random.random() < 0.3 else f"user{random.randint(1, 5)}@example.com",
        "type": random.choice(INCIDENT_TYPES),
        "resourceName": f"vm-{random.randint(1000, 9999)}",
        "subscriptionId": f"subscription-{random.randint(1, 5)}",
        
        # Additional detailed information
        "description": f"Detailed description for incident {incident_id[:8]}. This incident was detected by Azure Sentinel based on anomalous activity patterns.",
        "alertsCount": random.randint(1, 10),
        "entitiesCount": random.randint(1, 20),
        "lastActivityTime": (datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 48))).isoformat(),
        "owner": {
            "name": f"User {random.randint(1, 5)}",
            "email": f"user{random.randint(1, 5)}@example.com",
            "assignedTime": (datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 24))).isoformat()
        },
        "relatedResources": [
            {
                "id": f"resource-{random.randint(1000, 9999)}",
                "name": f"vm-{random.randint(1000, 9999)}",
                "type": "VirtualMachine"
            }
            for _ in range(random.randint(1, 3))
        ],
        "alerts": [
            {
                "id": f"alert-{random.randint(1000, 9999)}",
                "name": f"Alert {i+1} for {incident_id[:8]}",
                "severity": random.choice(SEVERITY_LEVELS),
                "time": (datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 48))).isoformat()
            }
            for i in range(random.randint(1, 5))
        ],
        "timeline": [
            {
                "time": (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat(),
                "action": action,
                "user": f"user{random.randint(1, 5)}@example.com" if action != "Created" else "System"
            }
            for hours, action in sorted([(random.randint(1, 48), action) for action in
                                        ["Created", "StatusChanged", "CommentAdded", "AssigneeChanged"][:random.randint(1, 4)]], 
                                        key=lambda x: x[0], reverse=True)
        ],
        "comments": [
            {
                "id": f"comment-{random.randint(1000, 9999)}",
                "user": f"user{random.randint(1, 5)}@example.com",
                "text": f"Comment {i+1} on incident {incident_id[:8]}",
                "time": (datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 48))).isoformat()
            }
            for i in range(random.randint(0, 3))
        ],
        "recommendations": [
            "Investigate suspicious login attempts",
            "Check for unauthorized changes to security groups",
            "Review network traffic logs",
            "Apply latest security patches"
        ][:random.randint(1, 4)]
    }
    
    return incident

def generate_mock_metrics_dashboard() -> Dict[str, Any]:
    """
    Generate mock security metrics dashboard data.
    
    Returns:
        Dict containing security metrics data
    """
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year
    
    # Generate data for the last 30 days
    days = 30
    date_points = [(datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") 
                  for i in range(days)]
    date_points.reverse()
    
    # Generate some trend data
    incident_trend = [random.randint(3, 15) for _ in range(days)]
    severity_counts = {
        "Critical": random.randint(5, 15),
        "High": random.randint(15, 40),
        "Medium": random.randint(30, 70),
        "Low": random.randint(40, 100)
    }
    
    # Calculate some derived metrics
    total_incidents = sum(severity_counts.values())
    incident_by_type = {
        incident_type: random.randint(10, 50) 
        for incident_type in INCIDENT_TYPES
    }
    
    top_resources = [
        {
            "name": f"resource-{i}",
            "count": random.randint(5, 25)
        }
        for i in range(1, 6)
    ]
    
    top_resources.sort(key=lambda x: x["count"], reverse=True)
    
    # Generate MTTR (Mean Time To Resolution) in hours for each severity
    mttr_by_severity = {
        "Critical": round(random.uniform(1, 8), 1),
        "High": round(random.uniform(8, 24), 1),
        "Medium": round(random.uniform(24, 72), 1),
        "Low": round(random.uniform(72, 168), 1)
    }
    
    dashboard = {
        "summary": {
            "totalIncidents": total_incidents,
            "openIncidents": random.randint(int(total_incidents * 0.2), int(total_incidents * 0.5)),
            "resolvedLast24h": random.randint(5, 20),
            "newLast24h": random.randint(5, 25),
            "meanTimeToResolution": round(random.uniform(10, 48), 1),  # hours
            "criticalIncidents": severity_counts["Critical"]
        },
        "trend": {
            "dates": date_points,
            "incidents": incident_trend
        },
        "severityDistribution": {
            "labels": list(severity_counts.keys()),
            "values": list(severity_counts.values())
        },
        "incidentsByType": {
            "labels": list(incident_by_type.keys()),
            "values": list(incident_by_type.values())
        },
        "topAffectedResources": top_resources,
        "resolutionTimes": {
            "labels": list(mttr_by_severity.keys()),
            "values": list(mttr_by_severity.values())
        },
        "statusDistribution": {
            "labels": INCIDENT_STATUSES,
            "values": [random.randint(10, 50) for _ in INCIDENT_STATUSES]
        }
    }
    
    return dashboard
