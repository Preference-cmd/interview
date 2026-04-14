-- Schema migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Initial migration record
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('0001_initial_schema');

-- Stores
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER NOT NULL,
    store_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    city TEXT,
    category TEXT,
    rating REAL DEFAULT 0.0,
    monthly_orders INTEGER DEFAULT 0,
    gmv_last_7d REAL DEFAULT 0.0,
    review_count INTEGER DEFAULT 0,
    review_reply_rate REAL DEFAULT 0.0,
    ros_health TEXT DEFAULT 'unknown',
    competitor_avg_discount REAL DEFAULT 0.0,
    issues TEXT DEFAULT '[]',
    raw_data TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_stores_store_id ON stores (store_id);

-- Workflow instances
CREATE TABLE IF NOT EXISTS workflow_instances (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    current_state TEXT DEFAULT 'NEW_STORE',
    consecutive_failures INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    started_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_store_id ON workflow_instances (store_id);
CREATE INDEX IF NOT EXISTS ix_workflow_instances_current_state ON workflow_instances (current_state);

-- Agent runs
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    agent_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    state_at_run TEXT,
    input_data TEXT DEFAULT '{}',
    output_data TEXT DEFAULT '{}',
    error_msg TEXT,
    retry_count INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE INDEX IF NOT EXISTS ix_agent_runs_store_id ON agent_runs (store_id);
CREATE INDEX IF NOT EXISTS ix_agent_runs_status ON agent_runs (status);
CREATE INDEX IF NOT EXISTS ix_agent_runs_created_at ON agent_runs (created_at);
CREATE INDEX IF NOT EXISTS ix_agent_runs_store_created ON agent_runs (store_id, created_at);

-- Event logs
CREATE TABLE IF NOT EXISTS event_logs (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    agent_type TEXT,
    message TEXT,
    extra_data TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE INDEX IF NOT EXISTS ix_event_logs_store_id ON event_logs (store_id);
CREATE INDEX IF NOT EXISTS ix_event_logs_event_type ON event_logs (event_type);
CREATE INDEX IF NOT EXISTS ix_event_logs_created_at ON event_logs (created_at);
CREATE INDEX IF NOT EXISTS ix_event_logs_store_created ON event_logs (store_id, created_at);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT DEFAULT 'warning',
    message TEXT,
    extra_data TEXT DEFAULT '{}',
    acknowledged INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE INDEX IF NOT EXISTS ix_alerts_store_id ON alerts (store_id);
CREATE INDEX IF NOT EXISTS ix_alerts_severity ON alerts (severity);
CREATE INDEX IF NOT EXISTS ix_alerts_acknowledged ON alerts (acknowledged);
CREATE INDEX IF NOT EXISTS ix_alerts_created_at ON alerts (created_at);
CREATE INDEX IF NOT EXISTS ix_alerts_store_created ON alerts (store_id, created_at);

-- Reports
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    content_md TEXT,
    content_json TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE INDEX IF NOT EXISTS ix_reports_store_id ON reports (store_id);
CREATE INDEX IF NOT EXISTS ix_reports_report_type ON reports (report_type);
CREATE INDEX IF NOT EXISTS ix_reports_created_at ON reports (created_at);
CREATE INDEX IF NOT EXISTS ix_reports_store_created ON reports (store_id, created_at);
