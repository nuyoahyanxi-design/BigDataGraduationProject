# Source this file; credentials remain in process memory and Windows Credential Manager.
export PYTHONDONTWRITEBYTECODE=1
source /home/nuyoah/.bigdata-env.sh
source /home/nuyoah/.venvs/bigdata-graduation-env/bin/activate
if ! _bigdata_db_assignments="$(python /mnt/d/BigDataGraduationProject/environments/export-db-environment.py)"; then
    printf '%s\n' 'Database credential loading failed; check Windows Credential Manager.' >&2
    return 1
fi
eval "$_bigdata_db_assignments"
unset _bigdata_db_assignments
