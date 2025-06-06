-- Add performance tracking fields to nodes table
-- Run this SQL script directly on your database

-- Add performance tracking columns to nodes table
ALTER TABLE nodes ADD COLUMN avg_response_time REAL DEFAULT NULL;
ALTER TABLE nodes ADD COLUMN success_rate REAL DEFAULT NULL;
ALTER TABLE nodes ADD COLUMN last_performance_check DATETIME DEFAULT NULL;
ALTER TABLE nodes ADD COLUMN active_connections INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE nodes ADD COLUMN total_connections INTEGER DEFAULT 0 NOT NULL;

-- Create node_performance_metrics table
CREATE TABLE node_performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response_time REAL NOT NULL,
    success BOOLEAN NOT NULL,
    error_message VARCHAR(512),
    FOREIGN KEY (node_id) REFERENCES nodes(id),
    UNIQUE(created_at, node_id)
);

-- Create index for performance metrics
CREATE INDEX ix_node_performance_metrics_node_id ON node_performance_metrics(node_id);

-- Create node_connection_logs table
CREATE TABLE node_connection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    subscription_token VARCHAR(256),
    connected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    disconnected_at DATETIME,
    user_agent VARCHAR(512),
    client_ip VARCHAR(45),
    FOREIGN KEY (node_id) REFERENCES nodes(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create indexes for connection logs
CREATE INDEX ix_node_connection_logs_node_id ON node_connection_logs(node_id);
CREATE INDEX ix_node_connection_logs_user_id ON node_connection_logs(user_id);
CREATE INDEX ix_node_connection_logs_connected_at ON node_connection_logs(connected_at);

-- Verify the changes
SELECT name FROM sqlite_master WHERE type='table' AND name IN ('node_performance_metrics', 'node_connection_logs');
PRAGMA table_info(nodes);
