-- MySQL 8.4 schema for AI Customer Support Intelligence.
-- Run with: mysql -u root -p < database/schema.sql
CREATE DATABASE IF NOT EXISTS customer_support_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE customer_support_db;

CREATE TABLE IF NOT EXISTS users (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  full_name VARCHAR(255) NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  role ENUM('admin','agent') NOT NULL DEFAULT 'agent',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tickets (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ticket_number VARCHAR(20) NOT NULL UNIQUE,
  subject VARCHAR(500) NOT NULL,
  description TEXT NOT NULL,
  status ENUM('open','in_progress','resolved','closed') NOT NULL DEFAULT 'open',
  priority ENUM('low','medium','high','urgent') NULL,
  category VARCHAR(100) NULL,
  customer_name VARCHAR(255) NULL,
  customer_email VARCHAR(255) NULL,
  created_by INT NOT NULL,
  assigned_to INT NULL,
  is_urgent BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  resolved_at DATETIME NULL,
  CONSTRAINT fk_tickets_created_by FOREIGN KEY (created_by) REFERENCES users(id),
  CONSTRAINT fk_tickets_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
  INDEX ix_tickets_status (status),
  INDEX ix_tickets_priority (priority),
  INDEX ix_tickets_created_at (created_at),
  INDEX ix_tickets_ticket_number (ticket_number)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_predictions (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ticket_id INT NOT NULL UNIQUE,
  predicted_category VARCHAR(100) NULL,
  category_confidence FLOAT NULL,
  predicted_priority VARCHAR(50) NULL,
  priority_confidence FLOAT NULL,
  predicted_sentiment ENUM('positive','neutral','negative') NULL,
  sentiment_confidence FLOAT NULL,
  is_urgent_rule_based BOOLEAN NOT NULL DEFAULT FALSE,
  model_version VARCHAR(50) NULL,
  predicted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_predictions_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  INDEX ix_ticket_predictions_ticket_id (ticket_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_status_history (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ticket_id INT NOT NULL,
  old_status ENUM('open','in_progress','resolved','closed') NULL,
  new_status ENUM('open','in_progress','resolved','closed') NOT NULL,
  changed_by INT NOT NULL,
  comment TEXT NULL,
  changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_status_history_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  CONSTRAINT fk_status_history_user FOREIGN KEY (changed_by) REFERENCES users(id),
  INDEX ix_ticket_status_history_ticket_id (ticket_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  ticket_id INT NULL,
  action VARCHAR(100) NOT NULL,
  details TEXT NULL,
  ip_address VARCHAR(45) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_audit_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE SET NULL,
  INDEX ix_audit_logs_created_at (created_at),
  INDEX ix_audit_logs_user_id (user_id),
  INDEX ix_audit_logs_ticket_id (ticket_id)
) ENGINE=InnoDB;
