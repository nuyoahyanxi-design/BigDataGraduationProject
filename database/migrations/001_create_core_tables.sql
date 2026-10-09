-- V1.0: database-design.md, five tables / 51 fields. DDL implicitly commits.
CREATE DATABASE IF NOT EXISTS bigdata_graduation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bigdata_graduation;
SET time_zone = '+00:00';

CREATE TABLE users (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
 username VARCHAR(50) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 password_hash VARCHAR(255) NOT NULL,
 nickname VARCHAR(50) DEFAULT NULL,
 role VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'learner',
 status VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'active',
 interest_tags JSON NOT NULL,
 created_at DATETIME(3) NOT NULL,
 updated_at DATETIME(3) NOT NULL,
 PRIMARY KEY (id),
 UNIQUE KEY uk_users_username (username),
 KEY idx_users_status_role_id (status,role,id),
 CONSTRAINT ck_users_role CHECK (role IN ('learner','admin')),
 CONSTRAINT ck_users_status CHECK (status IN ('active','disabled','deleted')),
 CONSTRAINT ck_users_username CHECK (CHAR_LENGTH(TRIM(username)) > 0 AND BINARY username = BINARY LOWER(username)),
 CONSTRAINT ck_users_time CHECK (updated_at >= created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE resources (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
 title VARCHAR(200) NOT NULL,
 resource_type VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 category_code VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 tags JSON NOT NULL,
 difficulty TINYINT UNSIGNED NOT NULL DEFAULT 1,
 summary VARCHAR(1000) NOT NULL,
 content LONGTEXT DEFAULT NULL,
 content_url VARCHAR(1000) DEFAULT NULL,
 source_name VARCHAR(255) DEFAULT NULL,
 license_note VARCHAR(500) DEFAULT NULL,
 status VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'draft',
 version_no INT UNSIGNED NOT NULL DEFAULT 1,
 created_by BIGINT UNSIGNED NOT NULL,
 published_at DATETIME(3) DEFAULT NULL,
 created_at DATETIME(3) NOT NULL,
 updated_at DATETIME(3) NOT NULL,
 PRIMARY KEY (id),
 KEY idx_resources_status_category_id (status,category_code,id),
 KEY idx_resources_status_id (status,id),
 KEY idx_resources_updated_id (updated_at,id),
 KEY idx_resources_created_by (created_by),
 CONSTRAINT fk_resources_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT ck_resources_type CHECK (resource_type IN ('document','course','exercise')),
 CONSTRAINT ck_resources_status CHECK (status IN ('draft','published','offline','deleted')),
 CONSTRAINT ck_resources_difficulty CHECK (difficulty BETWEEN 1 AND 3),
 CONSTRAINT ck_resources_version CHECK (version_no >= 1),
 CONSTRAINT ck_resources_text CHECK (CHAR_LENGTH(TRIM(title)) > 0 AND CHAR_LENGTH(TRIM(summary)) > 0),
 CONSTRAINT ck_resources_time CHECK (updated_at >= created_at),
 CONSTRAINT ck_resources_published CHECK (status <> 'published' OR (published_at IS NOT NULL AND JSON_TYPE(tags) = 'ARRAY' AND JSON_LENGTH(tags) > 0 AND (COALESCE(CHAR_LENGTH(TRIM(content)),0) > 0 OR COALESCE(CHAR_LENGTH(TRIM(content_url)),0) > 0)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE learning_progress (
 user_id BIGINT UNSIGNED NOT NULL,
 resource_id BIGINT UNSIGNED NOT NULL,
 status VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'in_progress',
 first_started_at DATETIME(3) NOT NULL,
 completed_at DATETIME(3) DEFAULT NULL,
 updated_at DATETIME(3) NOT NULL,
 PRIMARY KEY (user_id,resource_id),
 KEY idx_progress_user_status_updated (user_id,status,updated_at,resource_id),
 KEY idx_progress_resource_user (resource_id,user_id),
 CONSTRAINT fk_progress_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_progress_resource FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT ck_progress_status CHECK (status IN ('in_progress','completed')),
 CONSTRAINT ck_progress_completion CHECK ((status = 'in_progress' AND completed_at IS NULL) OR (status = 'completed' AND completed_at IS NOT NULL AND completed_at >= first_started_at)),
 CONSTRAINT ck_progress_time CHECK (updated_at >= first_started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE favorites (
 user_id BIGINT UNSIGNED NOT NULL,
 resource_id BIGINT UNSIGNED NOT NULL,
 created_at DATETIME(3) NOT NULL,
 PRIMARY KEY (user_id,resource_id),
 KEY idx_favorites_user_created (user_id,created_at,resource_id),
 KEY idx_favorites_resource_user (resource_id,user_id),
 CONSTRAINT fk_favorites_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_favorites_resource FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE learning_events (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
 event_uuid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 user_id BIGINT UNSIGNED NOT NULL,
 resource_id BIGINT UNSIGNED NOT NULL,
 event_type VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 event_source VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 schema_version SMALLINT UNSIGNED NOT NULL DEFAULT 1,
 resource_version INT UNSIGNED NOT NULL,
 session_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
 occurred_at DATETIME(3) NOT NULL,
 received_at DATETIME(3) NOT NULL,
 client_occurred_at DATETIME(3) DEFAULT NULL,
 is_effective TINYINT UNSIGNED NOT NULL,
 state_before VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
 state_after VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
 request_fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 PRIMARY KEY (id),
 UNIQUE KEY uk_events_uuid (event_uuid),
 KEY idx_events_user_resource_time (user_id,resource_id,occurred_at,id),
 KEY idx_events_user_time (user_id,occurred_at,id),
 KEY idx_events_resource_time (resource_id,occurred_at,id),
 KEY idx_events_received_id (received_at,id),
 CONSTRAINT fk_events_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_events_resource FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT ck_events_type CHECK (event_type IN ('resource_view','learning_start','learning_complete','favorite_add','favorite_remove')),
 CONSTRAINT ck_events_source CHECK (event_source IN ('client','server')),
 CONSTRAINT ck_events_versions CHECK (schema_version >= 1 AND resource_version >= 1),
 CONSTRAINT ck_events_effective CHECK (is_effective IN (0,1)),
 CONSTRAINT ck_events_time CHECK (occurred_at >= received_at),
 CONSTRAINT ck_events_semantics CHECK (
  (event_type = 'resource_view' AND event_source = 'client' AND is_effective = 1 AND session_id IS NOT NULL AND state_before IS NULL AND state_after IS NULL)
  OR
  (event_source = 'server' AND client_occurred_at IS NULL AND state_before IS NOT NULL AND state_after IS NOT NULL AND (
   (event_type = 'learning_start' AND ((is_effective = 1 AND state_before = 'not_started' AND state_after = 'in_progress') OR (is_effective = 0 AND state_before = state_after AND state_before IN ('in_progress','completed'))))
   OR (event_type = 'learning_complete' AND ((is_effective = 1 AND state_before = 'in_progress' AND state_after = 'completed') OR (is_effective = 0 AND state_before = 'completed' AND state_after = 'completed')))
   OR (event_type = 'favorite_add' AND ((is_effective = 1 AND state_before = 'not_favorited' AND state_after = 'favorited') OR (is_effective = 0 AND state_before = 'favorited' AND state_after = 'favorited')))
   OR (event_type = 'favorite_remove' AND ((is_effective = 1 AND state_before = 'favorited' AND state_after = 'not_favorited') OR (is_effective = 0 AND state_before = 'not_favorited' AND state_after = 'not_favorited')))
  ))
 )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
