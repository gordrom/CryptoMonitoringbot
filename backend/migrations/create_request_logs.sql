-- Create request_logs table
CREATE TABLE IF NOT EXISTS request_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    method TEXT NOT NULL,
    url TEXT NOT NULL,
    client_host TEXT,
    query_params JSONB,
    request_body JSONB,
    response_body JSONB,
    status_code INTEGER,
    processing_time FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_request_logs_request_id ON request_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_request_logs_timestamp ON request_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_request_logs_method ON request_logs(method);
CREATE INDEX IF NOT EXISTS idx_request_logs_status_code ON request_logs(status_code); 