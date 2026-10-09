CREATE TABLE user_profiles (
 user_id BIGINT UNSIGNED NOT NULL,
 batch_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 generated_at DATETIME(3) NOT NULL,
 interest_profile JSON NOT NULL,
 activity_profile JSON NOT NULL,
 learning_preference JSON NOT NULL,
 metric_explanations JSON NOT NULL,
 PRIMARY KEY (user_id,batch_id),
 KEY idx_profiles_batch (batch_id),
 CONSTRAINT fk_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT chk_profiles_interest CHECK (JSON_TYPE(interest_profile)='OBJECT'),
 CONSTRAINT chk_profiles_activity CHECK (JSON_TYPE(activity_profile)='OBJECT'),
 CONSTRAINT chk_profiles_preference CHECK (JSON_TYPE(learning_preference)='OBJECT'),
 CONSTRAINT chk_profiles_explanations CHECK (JSON_TYPE(metric_explanations)='OBJECT')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
