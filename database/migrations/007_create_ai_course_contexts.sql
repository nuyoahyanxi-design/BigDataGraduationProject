CREATE TABLE ai_course_contexts (
 qa_record_id BIGINT UNSIGNED NOT NULL,
 course_title VARCHAR(200) NOT NULL,
 `references` JSON NOT NULL,
 context_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 retrieval_version VARCHAR(30) NOT NULL,
 created_at DATETIME(3) NOT NULL,
 PRIMARY KEY (qa_record_id),
 CONSTRAINT fk_ai_course_qa FOREIGN KEY (qa_record_id) REFERENCES ai_qa_records(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT ck_ai_course_references CHECK (JSON_TYPE(`references`) = 'ARRAY' AND JSON_LENGTH(`references`) <= 3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
