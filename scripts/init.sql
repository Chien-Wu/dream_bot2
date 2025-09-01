-- Database initialization script for Dream Line Bot

-- Create database (if not exists)
CREATE DATABASE IF NOT EXISTS dream_bot_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE dream_bot_db;

-- User threads table
CREATE TABLE IF NOT EXISTS user_threads (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE,
    thread_id VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_user_id (user_id),
    INDEX idx_thread_id (thread_id)
);

-- Message history table
CREATE TABLE IF NOT EXISTS message_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',
    ai_response TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    ai_explanation TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);

-- AI detail table for comprehensive AI response analysis
CREATE TABLE IF NOT EXISTS ai_detail (
    id INT PRIMARY KEY AUTO_INCREMENT,
    message_history_id INT,
    intent VARCHAR(50),
    queries JSON,
    sources JSON,
    gaps JSON,
    policy_scope TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    policy_risk TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    policy_pii TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    policy_escalation TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    notes TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_message_history_id (message_history_id),
    INDEX idx_intent (intent),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (message_history_id) REFERENCES message_history(id) ON DELETE CASCADE
);

-- Organization data table
CREATE TABLE IF NOT EXISTS organization_data (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    organization_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    completion_status ENUM('incomplete', 'complete') DEFAULT 'incomplete',
    handover_flag_expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_id (user_id),
    INDEX idx_user_id (user_id),
    INDEX idx_completion_status (completion_status),
    INDEX idx_handover_flag_expires_at (handover_flag_expires_at)
);

-- Note: ai_explanation column is already included in the CREATE TABLE statement above
-- For existing installations, the column addition is handled programmatically in the DatabaseService