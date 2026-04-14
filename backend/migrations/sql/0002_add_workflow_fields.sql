-- Migration: 0002_add_workflow_fields
-- Adds is_running field to workflow_instances

ALTER TABLE workflow_instances ADD COLUMN is_running INTEGER DEFAULT 0 NOT NULL;
CREATE INDEX IF NOT EXISTS ix_workflow_instances_is_running ON workflow_instances(is_running);
