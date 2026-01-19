-- SQL script to add is_contract column to res_partner table
-- Run this in your PostgreSQL database

ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_contract BOOLEAN DEFAULT FALSE;

-- Verify the column was added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name='res_partner' AND column_name='is_contract';

