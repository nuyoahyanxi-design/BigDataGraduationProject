CREATE TABLE auth_recovery_codes (
 user_id BIGINT UNSIGNED NOT NULL,
 code_hash VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 PRIMARY KEY (user_id),
 CONSTRAINT fk_auth_recovery_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
