-- Add confidence column to forecast_history table
ALTER TABLE forecast_history
ADD COLUMN IF NOT EXISTS confidence FLOAT;

-- Add accuracy_score column if it doesn't exist
ALTER TABLE forecast_history
ADD COLUMN IF NOT EXISTS accuracy_score FLOAT;

-- Add actual_price column if it doesn't exist
ALTER TABLE forecast_history
ADD COLUMN IF NOT EXISTS actual_price FLOAT; 