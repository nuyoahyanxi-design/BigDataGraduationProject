# First Git baseline plan — 2026-10-09

Repository: D:\BigDataGraduationProject. Existing main branch has no commits.
Create the first commit using the recovered WSL Git identity and the requested message:
restore: migrate graduation project environment to new machine

Keep business source unchanged. Include frontend/backend/Spark source, tests, dependency lockfiles, database schema/seeds and design documentation. Include only reviewed credential-loading and launcher source from environments/outputs; exclude all credential values, local env files, logs, data, installed dependencies, generated builds, virtual disks and backups. Template .env.example files may be included only with empty/placeholder secret values.

Verify candidate and staged files against ignore rules, known locally stored secrets and generic credential patterns. Review the staged summary before committing. The commit is local; no remote publication is authorized. Preserve recovery data and database contents.