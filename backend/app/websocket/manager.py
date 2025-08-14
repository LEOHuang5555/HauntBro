"""
WebSocket manager with Redis Streams for reliable messaging
Following 2024 production patterns for scalable real-time features
"""

import sys
from pathlib import Path
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from fastapi import WebSocket, WebSocketDisconnect
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.app.core.config import backend_config
from backend.app.core.security import security_service
from infrastructure.database.models import User

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Individual WebSocket connection with metadata"""
    
    def __init__(self, websocket: WebSocket, user_id: str, connection_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.connection_id = connection_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)
        self.is_alive = True
    
    async def send_json(self, data: Dict[str, Any]):
        """Send JSON data to WebSocket"""
        try:
            await self.websocket.send_json({
                **data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "connection_id": self.connection_id
            })
        except Exception as e:
            logger.error(f"Error sending message to {self.connection_id}: {e}")
            self.is_alive = False
    
    async def send_text(self, message: str):
        """Send text message to WebSocket"""
        try:
            await self.websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending text to {self.connection_id}: {e}")
            self.is_alive = False
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        self.last_heartbeat = datetime.now(timezone.utc)


class WebSocketManager:
    """
    WebSocket manager with Redis Streams for reliable messaging
    Supports connection management, authentication, and scalable messaging
    """
    
    def __init__(self):
        self.connections: Dict[str, Dict[str, WebSocketConnection]] = {}  # user_id -> {connection_id: connection}
        self.redis_client: Optional[redis.Redis] = None
        self.heartbeat_interval = 30  # seconds
        self.message_retention = 86400  # 24 hours in seconds
        self.consumer_group = "websocket_consumers"
        self.consumer_name = "websocket_manager"
        self.running = False
        
    async def initialize(self):
        """Initialize Redis connection and consumer group"""
        try:
            if not REDIS_AVAILABLE:
                logger.warning("⚠️ Redis not available - WebSocket will work without persistence")
                return True
            
            # Connect to Redis
            self.redis_client = redis.Redis.from_url(
                backend_config.redis.url,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis connection established for WebSocket manager")
            
            # Initialize consumer groups for notification streams
            try:
                await self.redis_client.xgroup_create(
                    "notifications", 
                    self.consumer_group, 
                    id="0", 
                    mkstream=True
                )
                logger.info("✅ Redis consumer group created")
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Error creating consumer group: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize WebSocket manager: {e}")
            # Still return True to allow WebSocket to work without Redis
            return True
    
    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: str, 
        connection_id: str
    ) -> bool:
        """
        Accept WebSocket connection and set up user session
        
        Args:
            websocket: WebSocket connection
            user_id: Authenticated user ID
            connection_id: Unique connection identifier
        
        Returns:
            Success status
        """
        try:
            await websocket.accept()
            
            # Create connection object
            connection = WebSocketConnection(websocket, user_id, connection_id)
            
            # Store connection
            if user_id not in self.connections:
                self.connections[user_id] = {}
            self.connections[user_id][connection_id] = connection
            
            logger.info(f"WebSocket connected: user {user_id}, connection {connection_id}")
            
            # Send welcome message
            await connection.send_json({
                "type": "connection_established",
                "message": "WebSocket connection established",
                "user_id": user_id,
                "connection_id": connection_id
            })
            
            # Deliver any missed messages from Redis Stream
            await self._deliver_missed_messages(user_id, connection)
            
            # Start background tasks for this connection
            asyncio.create_task(self._handle_connection(connection))
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False
    
    async def disconnect(self, user_id: str, connection_id: str):
        """Disconnect WebSocket and clean up"""
        try:
            if user_id in self.connections and connection_id in self.connections[user_id]:
                connection = self.connections[user_id][connection_id]
                connection.is_alive = False
                
                del self.connections[user_id][connection_id]
                
                # Clean up empty user connections
                if not self.connections[user_id]:
                    del self.connections[user_id]
                
                logger.info(f"WebSocket disconnected: user {user_id}, connection {connection_id}")
                
        except Exception as e:
            logger.error(f"WebSocket disconnect error: {e}")
    
    async def send_to_user(
        self, 
        user_id: str, 
        message: Dict[str, Any],
        persistent: bool = True
    ):
        """
        Send message to all connections of a user
        
        Args:
            user_id: Target user ID
            message: Message data
            persistent: Whether to store in Redis Stream for reliability
        """
        try:
            # Add message to Redis Stream for persistence and reliability
            if persistent and self.redis_client and REDIS_AVAILABLE:
                stream_key = f"notifications:{user_id}"
                await self.redis_client.xadd(
                    stream_key,
                    message,
                    maxlen=1000  # Keep last 1000 messages
                )
            
            # Send to active connections
            if user_id in self.connections:
                disconnected_connections = []
                
                for connection_id, connection in self.connections[user_id].items():
                    if connection.is_alive:
                        try:
                            await connection.send_json({
                                "type": "notification",
                                **message
                            })
                        except Exception as e:
                            logger.warning(f"Failed to send to connection {connection_id}: {e}")
                            disconnected_connections.append(connection_id)
                    else:
                        disconnected_connections.append(connection_id)
                
                # Clean up disconnected connections
                for conn_id in disconnected_connections:
                    await self.disconnect(user_id, conn_id)
            
            # If no active connections, message is still stored in Redis Stream
            if user_id not in self.connections or not self.connections[user_id]:
                logger.info(f"Message stored for offline user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
    
    async def broadcast(self, message: Dict[str, Any], user_ids: Optional[List[str]] = None):
        """
        Broadcast message to multiple users or all connected users
        
        Args:
            message: Message data
            user_ids: List of user IDs (None for all users)
        """
        try:
            target_users = user_ids or list(self.connections.keys())
            
            for user_id in target_users:
                await self.send_to_user(user_id, message)
                
            logger.info(f"Broadcasted message to {len(target_users)} users")
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
    
    async def send_system_notification(
        self, 
        user_id: str, 
        notification_type: str, 
        title: str, 
        content: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Send system notification to user"""
        try:
            message = {
                "type": "system_notification",
                "notification_type": notification_type,
                "title": title,
                "content": content,
                "data": data or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.send_to_user(user_id, message)
            
        except Exception as e:
            logger.error(f"Error sending system notification: {e}")
    
    async def _deliver_missed_messages(
        self, 
        user_id: str, 
        connection: WebSocketConnection
    ):
        """Deliver missed messages from Redis Stream"""
        try:
            if not self.redis_client or not REDIS_AVAILABLE:
                return
            
            stream_key = f"notifications:{user_id}"
            
            # Get messages from the last hour (adjust as needed)
            since_timestamp = int(
                (datetime.now(timezone.utc).timestamp() - 3600) * 1000
            )
            
            # Read messages from stream
            messages = await self.redis_client.xread(
                {stream_key: since_timestamp},
                count=100
            )
            
            for stream, msgs in messages:
                for msg_id, fields in msgs:
                    try:
                        await connection.send_json({
                            "type": "missed_notification",
                            "message_id": msg_id,
                            **fields
                        })
                    except Exception as e:
                        logger.warning(f"Failed to deliver missed message: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Error delivering missed messages: {e}")
    
    async def _handle_connection(self, connection: WebSocketConnection):
        """Handle individual WebSocket connection lifecycle"""
        try:
            while connection.is_alive:
                try:
                    # Wait for message with timeout
                    data = await asyncio.wait_for(
                        connection.websocket.receive_text(),
                        timeout=self.heartbeat_interval
                    )
                    
                    # Process received message
                    await self._process_message(connection, data)
                    
                except asyncio.TimeoutError:
                    # Send heartbeat ping
                    await connection.send_json({
                        "type": "ping",
                        "message": "heartbeat"
                    })
                    
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected: {connection.connection_id}")
                    break
                    
                except Exception as e:
                    logger.error(f"Connection handler error: {e}")
                    break
            
        finally:
            connection.is_alive = False
            await self.disconnect(connection.user_id, connection.connection_id)
    
    async def _process_message(self, connection: WebSocketConnection, data: str):
        """Process incoming WebSocket message"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "pong":
                # Update heartbeat
                connection.update_heartbeat()
                
            elif message_type == "subscribe":
                # Handle subscription to specific channels
                channels = message.get("channels", [])
                await self._handle_subscription(connection, channels)
                
            elif message_type == "unsubscribe":
                # Handle unsubscription
                channels = message.get("channels", [])
                await self._handle_unsubscription(connection, channels)
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {data}")
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    async def _handle_subscription(
        self, 
        connection: WebSocketConnection, 
        channels: List[str]
    ):
        """Handle channel subscription"""
        # Placeholder for channel-based subscriptions
        # Could implement topic-based messaging here
        await connection.send_json({
            "type": "subscription_confirmed",
            "channels": channels
        })
    
    async def _handle_unsubscription(
        self, 
        connection: WebSocketConnection, 
        channels: List[str]
    ):
        """Handle channel unsubscription"""
        # Placeholder for channel-based unsubscriptions
        await connection.send_json({
            "type": "unsubscription_confirmed",
            "channels": channels
        })
    
    def get_connected_users(self) -> List[Dict[str, Any]]:
        """Get list of connected users"""
        users = []
        for user_id, connections in self.connections.items():
            active_connections = [
                {
                    "connection_id": conn_id,
                    "connected_at": conn.connected_at.isoformat(),
                    "last_heartbeat": conn.last_heartbeat.isoformat()
                }
                for conn_id, conn in connections.items()
                if conn.is_alive
            ]
            
            if active_connections:
                users.append({
                    "user_id": user_id,
                    "connection_count": len(active_connections),
                    "connections": active_connections
                })
        
        return users
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        total_connections = sum(
            len([conn for conn in connections.values() if conn.is_alive])
            for connections in self.connections.values()
        )
        
        return {
            "total_users": len(self.connections),
            "total_connections": total_connections,
            "average_connections_per_user": (
                total_connections / len(self.connections) 
                if self.connections else 0
            ),
            "redis_connected": self.redis_client is not None
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()