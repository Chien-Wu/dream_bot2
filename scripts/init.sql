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

-- Note: ai_explanation column is already included in the CREATE TABLE statement above
-- For existing installations, the column addition is handled programmatically in the DatabaseService