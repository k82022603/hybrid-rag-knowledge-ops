-- Test Users Seed Script for E2E Testing
-- Version: 1.0
-- Created: 2026-01-26
--
-- This script creates test user accounts for E2E testing.
-- Run after schema.sql to seed the auth_users table.
--
-- Test Accounts:
--   Email: test@example.com, Password: password123, Role: USER
--   Email: admin@example.com, Password: admin123!, Role: ADMIN,USER
--
-- BCrypt passwords are pre-hashed using strength 10.
-- Generated with: new BCryptPasswordEncoder(10).encode(password)

-- Ensure auth_users table exists
CREATE TABLE IF NOT EXISTS auth_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    roles VARCHAR(255) DEFAULT 'USER',
    is_active BOOLEAN DEFAULT true,
    is_locked BOOLEAN DEFAULT false,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clear existing test users (optional, remove if you want to keep existing data)
-- DELETE FROM auth_users WHERE email IN ('test@example.com', 'admin@example.com');

-- Insert test user (password: password123)
-- BCrypt hash: $2a$10$ prefix for Java compatibility
INSERT INTO auth_users (email, username, password_hash, first_name, last_name, roles, is_active, is_locked, failed_login_attempts)
VALUES (
    'test@example.com',
    'testuser',
    '$2a$10$AJfMv872SXOwwTOB9HNP7eir9LEhj1pihhFt/Dhpd1.R1PVvtHq3S',
    'Test',
    'User',
    'USER',
    true,
    false,
    0
)
ON CONFLICT (email) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    is_active = true,
    is_locked = false,
    failed_login_attempts = 0,
    updated_at = CURRENT_TIMESTAMP;

-- Insert admin user (password: admin123!)
-- BCrypt hash: $2a$10$ prefix for Java compatibility
INSERT INTO auth_users (email, username, password_hash, first_name, last_name, roles, is_active, is_locked, failed_login_attempts)
VALUES (
    'admin@example.com',
    'adminuser',
    '$2a$10$TklJOu/IfeMpihl740smseaj.Y1MaJHcFTvFjPc6k62Bdce4XJq22',
    'Admin',
    'User',
    'ADMIN,USER',
    true,
    false,
    0
)
ON CONFLICT (email) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    is_active = true,
    is_locked = false,
    failed_login_attempts = 0,
    updated_at = CURRENT_TIMESTAMP;

-- Verify inserted users
SELECT id, email, username, roles, is_active FROM auth_users WHERE email IN ('test@example.com', 'admin@example.com');
