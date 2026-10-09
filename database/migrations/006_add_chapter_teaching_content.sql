-- Add teaching content only; retain all chapter identities and learning records.
ALTER TABLE course_chapters
 ADD COLUMN learning_objectives JSON NULL,
 ADD COLUMN example_code LONGTEXT NULL,
 ADD COLUMN exercises JSON NULL,
 ADD CONSTRAINT ck_chapter_objectives CHECK(learning_objectives IS NULL OR JSON_TYPE(learning_objectives)='ARRAY'),
 ADD CONSTRAINT ck_chapter_exercises CHECK(exercises IS NULL OR JSON_TYPE(exercises)='ARRAY');
