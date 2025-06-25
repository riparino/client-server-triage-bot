#!/usr/bin/env python3
"""
Azure Sentinel Triage Bot Server
Main Flask application for handling client requests and Azure Sentinel data retrieval.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
import sys
import os

# Add server directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth.azure_auth import AzureAuthHelper
from data.sentinel_client import SentinelClient
from utils.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize components
config_manager = ConfigManager()
auth_helper = AzureAuthHelper()
sentinel_client = SentinelClient()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Check authentication status."""
    try:
        is_authenticated = auth_helper.check_authentication()
        return jsonify({
            'authenticated': is_authenticated,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
        return jsonify({'error': 'Authentication check failed'}), 500

@app.route('/api/tenants', methods=['GET'])
def get_tenants():
    """Get list of available tenants."""
    try:
        tenants = config_manager.get_tenants()
        return jsonify({
            'tenants': tenants,
            'count': len(tenants)
        })
    except Exception as e:
        logger.error(f"Error retrieving tenants: {str(e)}")
        return jsonify({'error': 'Failed to retrieve tenants'}), 500

@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    """Get Sentinel incidents from specified tenant(s)."""
    try:
        tenant_id = request.args.get('tenant_id')
        severity = request.args.get('severity', 'all')
        status = request.args.get('status', 'active')
        limit = int(request.args.get('limit', 10))
        
        if not tenant_id:
            return jsonify({'error': 'tenant_id parameter is required'}), 400
        
        incidents = sentinel_client.get_incidents(
            tenant_id=tenant_id,
            severity=severity,
            status=status,
            limit=limit
        )
        
        return jsonify({
            'incidents': incidents,
            'count': len(incidents),
            'tenant_id': tenant_id
        })
        
    except Exception as e:
        logger.error(f"Error retrieving incidents: {str(e)}")
        return jsonify({'error': 'Failed to retrieve incidents'}), 500

@app.route('/api/incidents/<incident_id>/details', methods=['GET'])
def get_incident_details(incident_id):
    """Get detailed information for a specific incident."""
    try:
        tenant_id = request.args.get('tenant_id')
        
        if not tenant_id:
            return jsonify({'error': 'tenant_id parameter is required'}), 400
        
        incident_details = sentinel_client.get_incident_details(
            tenant_id=tenant_id,
            incident_id=incident_id
        )
        
        return jsonify(incident_details)
        
    except Exception as e:
        logger.error(f"Error retrieving incident details: {str(e)}")
        return jsonify({'error': 'Failed to retrieve incident details'}), 500

@app.route('/api/chat', methods=['POST'])
def chat_query():
    """Process natural language queries about incidents."""
    try:
        data = request.get_json()
        query = data.get('query', '')
        tenant_id = data.get('tenant_id')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Process the natural language query
        # This would integrate with an LLM for natural language processing
        response = {
            'query': query,
            'response': f"Processed query: {query}",
            'suggestions': [
                "Show me high severity incidents",
                "List active incidents in the last 24 hours",
                "Get incident details for ID: XXX"
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        return jsonify({'error': 'Failed to process query'}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Azure Sentinel Triage Bot Server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)