"""
Connection Tracking Service

This service tracks user connections to nodes for better load balancing.
"""

import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi import Request

from app.db import GetDB, crud
from app.db.models import User, Node, NodeConnectionLog

logger = logging.getLogger(__name__)


class ConnectionTracker:
    """
    Service to track user connections to nodes.
    """
    
    def __init__(self):
        # In-memory tracking of active connections
        # Format: {connection_id: {node_id, user_id, log_id}}
        self.active_connections: Dict[str, Dict] = {}
    
    def track_subscription_access(self, request: Request, user: User, node_id: Optional[int] = None):
        """
        Track when a user accesses their subscription.
        This helps identify which node they're likely connecting to.
        
        Args:
            request: FastAPI request object
            user: User object
            node_id: Node ID if known from resilient node group selection
        """
        if not node_id:
            return
        
        try:
            with GetDB() as db:
                # Extract connection info
                user_agent = request.headers.get("user-agent", "")
                client_ip = self._get_client_ip(request)
                subscription_token = getattr(user, 'subscription_token', None)
                
                # Log the connection
                connection_log = crud.log_node_connection(
                    db=db,
                    node_id=node_id,
                    user_id=user.id,
                    subscription_token=subscription_token,
                    user_agent=user_agent,
                    client_ip=client_ip
                )
                
                # Store in active connections for potential disconnection tracking
                connection_key = f"{user.id}_{node_id}_{client_ip}_{user_agent[:50]}"
                self.active_connections[connection_key] = {
                    'node_id': node_id,
                    'user_id': user.id,
                    'log_id': connection_log.id,
                    'connected_at': datetime.utcnow()
                }
                
                logger.debug(f"Tracked connection: User {user.id} -> Node {node_id}")
                
        except Exception as e:
            logger.error(f"Failed to track connection: {e}")
    
    def estimate_device_count(self, user_id: int, hours: int = 24) -> int:
        """
        Estimate number of different devices using the same subscription.
        Based on different user agents and IPs in recent connection logs.
        
        Args:
            user_id: User ID
            hours: Hours to look back (default: 24)
            
        Returns:
            Estimated number of devices
        """
        try:
            with GetDB() as db:
                since = datetime.utcnow() - timedelta(hours=hours)
                
                # Get recent connection logs for this user
                logs = db.query(NodeConnectionLog).filter(
                    NodeConnectionLog.user_id == user_id,
                    NodeConnectionLog.connected_at >= since
                ).all()
                
                if not logs:
                    return 1  # Default to 1 device
                
                # Count unique combinations of user_agent and client_ip
                unique_devices = set()
                for log in logs:
                    device_signature = f"{log.user_agent or 'unknown'}_{log.client_ip or 'unknown'}"
                    unique_devices.add(device_signature)
                
                return max(1, len(unique_devices))
                
        except Exception as e:
            logger.error(f"Failed to estimate device count for user {user_id}: {e}")
            return 1
    
    def cleanup_stale_connections(self, max_age_hours: int = 24):
        """
        Clean up stale connection tracking data.
        
        Args:
            max_age_hours: Maximum age of connections to keep in memory
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            stale_keys = []
            for key, conn_data in self.active_connections.items():
                if conn_data['connected_at'] < cutoff_time:
                    stale_keys.append(key)
            
            for key in stale_keys:
                del self.active_connections[key]
            
            if stale_keys:
                logger.debug(f"Cleaned up {len(stale_keys)} stale connection records")
                
        except Exception as e:
            logger.error(f"Failed to cleanup stale connections: {e}")
    
    def get_node_load_info(self, node_id: int) -> Dict:
        """
        Get current load information for a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            Dictionary with load information
        """
        try:
            with GetDB() as db:
                node = crud.get_node_by_id(db, node_id)
                if not node:
                    return {'active_connections': 0, 'total_connections': 0}
                
                return {
                    'active_connections': node.active_connections,
                    'total_connections': node.total_connections,
                    'avg_response_time': node.avg_response_time,
                    'success_rate': node.success_rate
                }
                
        except Exception as e:
            logger.error(f"Failed to get load info for node {node_id}: {e}")
            return {'active_connections': 0, 'total_connections': 0}
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request headers."""
        # Check common headers for real IP
        for header in ['x-forwarded-for', 'x-real-ip', 'cf-connecting-ip']:
            if header in request.headers:
                ip = request.headers[header].split(',')[0].strip()
                if ip:
                    return ip
        
        # Fallback to direct client IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return None


# Global instance
connection_tracker = ConnectionTracker()


def track_user_connection(request: Request, user: User, node_id: Optional[int] = None):
    """
    Global function to track user connections.
    
    Args:
        request: FastAPI request object
        user: User object
        node_id: Node ID if known
    """
    connection_tracker.track_subscription_access(request, user, node_id)


def get_estimated_device_count(user_id: int) -> int:
    """
    Get estimated device count for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Estimated number of devices
    """
    return connection_tracker.estimate_device_count(user_id)


def get_node_load_info(node_id: int) -> Dict:
    """
    Get load information for a node.
    
    Args:
        node_id: Node ID
        
    Returns:
        Load information dictionary
    """
    return connection_tracker.get_node_load_info(node_id)
