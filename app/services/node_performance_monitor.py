"""
Node Performance Monitoring Service

This service periodically checks node performance and updates metrics.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import aiohttp
from sqlalchemy.orm import Session

from app.db import GetDB, crud
from app.db.models import Node
from app.models.node import NodeStatus

logger = logging.getLogger(__name__)


class NodePerformanceMonitor:
    """
    Service to monitor node performance and update metrics.
    """
    
    def __init__(self, check_interval: int = 300):  # 5 minutes default
        self.check_interval = check_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the performance monitoring service."""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Node performance monitor started")
    
    async def stop(self):
        """Stop the performance monitoring service."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Node performance monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._check_all_nodes()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _check_all_nodes(self):
        """Check performance of all connected nodes."""
        with GetDB() as db:
            # Get all connected nodes
            nodes = crud.get_nodes(db, status=NodeStatus.connected)
            
            if not nodes:
                return
            
            logger.debug(f"Checking performance of {len(nodes)} nodes")
            
            # Check nodes concurrently
            tasks = [self._check_node_performance(node) for node in nodes]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_node_performance(self, node: Node):
        """Check performance of a single node."""
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            # Simple HTTP health check to the node's API
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"http://{node.address}:{node.api_port}/health"
                async with session.get(url) as response:
                    if response.status == 200:
                        success = True
                    else:
                        error_message = f"HTTP {response.status}"
        
        except asyncio.TimeoutError:
            error_message = "Timeout"
        except aiohttp.ClientError as e:
            error_message = f"Connection error: {str(e)}"
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Record the metric
        with GetDB() as db:
            try:
                crud.record_node_performance(
                    db=db,
                    node_id=node.id,
                    response_time=response_time,
                    success=success,
                    error_message=error_message
                )
                logger.debug(f"Node {node.name}: {response_time:.1f}ms, success={success}")
            except Exception as e:
                logger.error(f"Failed to record performance for node {node.name}: {e}")
    
    async def cleanup_old_data(self):
        """Clean up old performance data."""
        with GetDB() as db:
            try:
                # Clean up performance metrics older than 7 days
                crud.cleanup_old_performance_metrics(db, days_to_keep=7)
                
                # Clean up connection logs older than 30 days
                crud.cleanup_old_connection_logs(db, days_to_keep=30)
                
                logger.info("Cleaned up old performance and connection data")
            except Exception as e:
                logger.error(f"Failed to cleanup old data: {e}")


# Global instance
performance_monitor = NodePerformanceMonitor()


async def start_performance_monitoring():
    """Start the global performance monitoring service."""
    await performance_monitor.start()


async def stop_performance_monitoring():
    """Stop the global performance monitoring service."""
    await performance_monitor.stop()


def schedule_performance_check(node_id: int):
    """
    Schedule an immediate performance check for a specific node.
    This can be called when a node status changes.
    """
    async def check_node():
        with GetDB() as db:
            node = crud.get_node_by_id(db, node_id)
            if node and node.status == NodeStatus.connected:
                await performance_monitor._check_node_performance(node)
    
    # Schedule the check to run in the background
    asyncio.create_task(check_node())


# Cleanup task that runs daily
async def daily_cleanup_task():
    """Daily cleanup task for old performance data."""
    while True:
        try:
            await asyncio.sleep(24 * 60 * 60)  # Wait 24 hours
            await performance_monitor.cleanup_old_data()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in daily cleanup task: {e}")


# Start the daily cleanup task
asyncio.create_task(daily_cleanup_task())
