CREATE TABLE recommendation_results (
 user_id BIGINT UNSIGNED NOT NULL,
 resource_id BIGINT UNSIGNED NOT NULL,
 batch_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 algorithm VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 score DECIMAL(24,12) NOT NULL,
 `rank` INT UNSIGNED NOT NULL,
 reason VARCHAR(1000) NOT NULL,
 PRIMARY KEY (user_id,batch_id,algorithm,resource_id),
 UNIQUE KEY uq_recommendation_rank (user_id,batch_id,algorithm,`rank`),
 KEY idx_recommendation_batch (batch_id),
 CONSTRAINT fk_recommendation_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_recommendation_resource FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT chk_recommendation_algorithm CHECK (algorithm IN ('popular_v1','content_v1')),
 CONSTRAINT chk_recommendation_score CHECK (score >= 0 AND (algorithm <> 'content_v1' OR score <= 1)),
 CONSTRAINT chk_recommendation_rank CHECK (`rank` >= 1),
 CONSTRAINT chk_recommendation_reason CHECK (CHAR_LENGTH(TRIM(reason)) > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
