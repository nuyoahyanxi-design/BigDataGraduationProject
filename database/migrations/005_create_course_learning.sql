-- Additive migration; existing tables and records remain unchanged.
CREATE TABLE course_chapters (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
 resource_id BIGINT UNSIGNED NOT NULL,
 title VARCHAR(200) NOT NULL,
 position INT UNSIGNED NOT NULL,
 content LONGTEXT NOT NULL,
 knowledge_tags JSON NOT NULL,
 video_name VARCHAR(200) NULL,
 video_url VARCHAR(500) NULL,
 video_cover VARCHAR(500) NULL,
 video_duration_seconds INT UNSIGNED NULL,
 video_position INT UNSIGNED NOT NULL DEFAULT 1,
 created_at DATETIME(3) NOT NULL,
 PRIMARY KEY(id), UNIQUE KEY uk_chapter_position(resource_id,position),
 UNIQUE KEY uk_chapter_resource(id,resource_id),
 CONSTRAINT fk_chapter_resource FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE RESTRICT,
 CONSTRAINT ck_chapter_position CHECK(position>0 AND video_position>0),
 CONSTRAINT ck_chapter_text CHECK(CHAR_LENGTH(TRIM(title))>0 AND CHAR_LENGTH(TRIM(content))>0),
 CONSTRAINT ck_chapter_tags CHECK(JSON_TYPE(knowledge_tags)='ARRAY')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE chapter_progress (
 user_id BIGINT UNSIGNED NOT NULL,
 chapter_id BIGINT UNSIGNED NOT NULL,
 first_started_at DATETIME(3) NOT NULL,
 completed_at DATETIME(3) NULL,
 PRIMARY KEY(user_id,chapter_id), KEY idx_chapter_progress_chapter(chapter_id),
 CONSTRAINT fk_chapter_progress_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT,
 CONSTRAINT fk_chapter_progress_chapter FOREIGN KEY(chapter_id) REFERENCES course_chapters(id) ON DELETE RESTRICT,
 CONSTRAINT ck_chapter_progress_time CHECK(completed_at IS NULL OR completed_at>=first_started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE chapter_events (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
 event_uuid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 user_id BIGINT UNSIGNED NOT NULL,
 resource_id BIGINT UNSIGNED NOT NULL,
 chapter_id BIGINT UNSIGNED NOT NULL,
 event_type VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 occurred_at DATETIME(3) NOT NULL,
 playback_seconds DECIMAL(10,3) NULL,
 is_effective TINYINT UNSIGNED NOT NULL,
 request_fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 result JSON NOT NULL,
 PRIMARY KEY(id), UNIQUE KEY uk_chapter_event_uuid(event_uuid),
 KEY idx_chapter_events_user_time(user_id,occurred_at,id),
 KEY idx_chapter_events_resource(resource_id,chapter_id),
 CONSTRAINT fk_chapter_event_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT,
 CONSTRAINT fk_chapter_event_chapter FOREIGN KEY(chapter_id,resource_id) REFERENCES course_chapters(id,resource_id) ON DELETE RESTRICT,
 CONSTRAINT ck_chapter_event_type CHECK(event_type IN ('chapter_view','video_play','chapter_complete')),
 CONSTRAINT ck_chapter_event_effective CHECK(is_effective IN (0,1)),
 CONSTRAINT ck_chapter_event_playback CHECK(playback_seconds IS NULL OR playback_seconds>=0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
