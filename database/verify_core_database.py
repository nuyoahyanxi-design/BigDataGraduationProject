"""Database-stage verification only; no web service or Spark application."""
import argparse
import hashlib
import json
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'environments' / 'mysql-admin-tools'))
import pymysql
from keyring.backends.Windows import WinVaultKeyring

TABLES = ['users', 'resources', 'learning_progress', 'favorites', 'learning_events']
INDEXES = {
 'users': {'PRIMARY': ['id'], 'uk_users_username': ['username'], 'idx_users_status_role_id': ['status','role','id']},
 'resources': {'PRIMARY':['id'], 'idx_resources_status_category_id':['status','category_code','id'], 'idx_resources_status_id':['status','id'], 'idx_resources_updated_id':['updated_at','id'], 'idx_resources_created_by':['created_by']},
 'learning_progress': {'PRIMARY':['user_id','resource_id'], 'idx_progress_user_status_updated':['user_id','status','updated_at','resource_id'], 'idx_progress_resource_user':['resource_id','user_id']},
 'favorites': {'PRIMARY':['user_id','resource_id'], 'idx_favorites_user_created':['user_id','created_at','resource_id'], 'idx_favorites_resource_user':['resource_id','user_id']},
 'learning_events': {'PRIMARY':['id'], 'uk_events_uuid':['event_uuid'], 'idx_events_user_resource_time':['user_id','resource_id','occurred_at','id'], 'idx_events_user_time':['user_id','occurred_at','id'], 'idx_events_resource_time':['resource_id','occurred_at','id'], 'idx_events_received_id':['received_at','id']}}

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--migrate', action='store_true')
    parser.add_argument('--seed', action='store_true')
    args = parser.parse_args()
    password = WinVaultKeyring().get_password('BigDataGraduationProject/MySQL','bigdata_dev')
    if not password:
        raise RuntimeError('MySQL credential missing from Windows Credential Manager')
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='bigdata_dev', password=password,
        charset='utf8mb4', autocommit=False, cursorclass=pymysql.cursors.DictCursor)
    password = None
    evidence = {'stage':'database-implementation','date':'2026-10-04','checks':[]}
    def check(name, condition):
        evidence['checks'].append({'name':name,'passed':bool(condition)})
        if not condition:
            raise AssertionError(name)
    q = conn.cursor()
    q.execute("SET time_zone='+00:00'")
    q.execute('SELECT VERSION() AS version, @@session.time_zone AS time_zone')
    evidence['server'] = q.fetchone()
    if args.migrate:
        q.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='bigdata_graduation'")
        check('migration target has no tables', not q.fetchall())
        migration = ROOT / 'database/migrations/001_create_core_tables.sql'
        sql = migration.read_text(encoding='utf-8')
        evidence['migration_sha256'] = hashlib.sha256(migration.read_bytes()).hexdigest()
        count = 0
        for statement in sql.split(';'):
            if statement.strip():
                q.execute(statement)
                count += 1
        evidence['migration_statements_executed'] = count
        conn.commit()
    q.execute('USE bigdata_graduation')
    q.execute("SELECT DEFAULT_CHARACTER_SET_NAME,DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=DATABASE()")
    evidence['database'] = q.fetchone()
    check('database charset/collation', evidence['database'] == {'DEFAULT_CHARACTER_SET_NAME':'utf8mb4','DEFAULT_COLLATION_NAME':'utf8mb4_unicode_ci'})
    q.execute("SELECT TABLE_NAME,ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME")
    evidence['tables'] = q.fetchall()
    check('exactly five tables', {t['TABLE_NAME'] for t in evidence['tables']} == set(TABLES))
    check('InnoDB and table utf8mb4', all(t['ENGINE']=='InnoDB' and t['TABLE_COLLATION']=='utf8mb4_unicode_ci' for t in evidence['tables']))
    evidence['columns'] = {}
    evidence['indexes'] = {}
    design = (ROOT/'docs/database-design.md').read_text(encoding='utf-8')
    for table in TABLES:
        section = design.split(f'## {TABLES.index(table)+3}. {table}',1)[1].split('\n## ',1)[0]
        field_rows = [line.split('|')[1:-1] for line in section.splitlines() if line.startswith('| ') and len(line.split('|'))==7]
        fields = [r for r in field_rows if r[0].strip() not in ('字段','名称') and r[1].strip().split('(')[0].split()[0] in ('BIGINT','VARCHAR','JSON','DATETIME','TINYINT','LONGTEXT','INT','CHAR','SMALLINT')]
        q.execute('SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,EXTRA,COLLATION_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION',(table,))
        columns = q.fetchall()
        evidence['columns'][table] = columns
        check(table+' exact field names/order', [r[0].strip() for r in fields]==[c['COLUMN_NAME'] for c in columns])
        for row, col in zip(fields,columns):
            expected_type=row[1].strip().lower()
            check(table+'.'+col['COLUMN_NAME']+' type/nullability', col['COLUMN_TYPE']==expected_type and col['IS_NULLABLE']==('YES' if row[2].strip()=='是' else 'NO'))
            default=row[3].strip()
            check(table+'.'+col['COLUMN_NAME']+' default', (col['COLUMN_DEFAULT'] is None if default in ('无','NULL','自增') else str(col['COLUMN_DEFAULT'])==default))
            check(table+'.'+col['COLUMN_NAME']+' auto_increment', ('auto_increment' in col['EXTRA']) == (default=='自增'))
        q.execute('SHOW INDEX FROM '+table)
        indexes = q.fetchall()
        actual={}
        for idx in indexes:
            actual.setdefault(idx['Key_name'],[]).append(idx['Column_name'])
        evidence['indexes'][table]=actual
        check(table+' exact primary/index definitions', actual==INDEXES[table])
        check(table+' index uniqueness', all(i['Non_unique']==(0 if i['Key_name']=='PRIMARY' or i['Key_name'].startswith('uk_') else 1) for i in indexes))
    q.execute("SELECT k.TABLE_NAME,k.COLUMN_NAME,k.REFERENCED_TABLE_NAME,k.REFERENCED_COLUMN_NAME,r.UPDATE_RULE,r.DELETE_RULE FROM information_schema.KEY_COLUMN_USAGE k JOIN information_schema.REFERENTIAL_CONSTRAINTS r ON k.CONSTRAINT_SCHEMA=r.CONSTRAINT_SCHEMA AND k.CONSTRAINT_NAME=r.CONSTRAINT_NAME WHERE k.TABLE_SCHEMA=DATABASE() AND k.REFERENCED_TABLE_NAME IS NOT NULL ORDER BY k.TABLE_NAME,k.COLUMN_NAME")
    evidence['foreign_keys']=q.fetchall()
    expected_fk={('resources','created_by','users'),('learning_progress','user_id','users'),('learning_progress','resource_id','resources'),('favorites','user_id','users'),('favorites','resource_id','resources'),('learning_events','user_id','users'),('learning_events','resource_id','resources')}
    check('seven exact RESTRICT foreign keys', {(r['TABLE_NAME'],r['COLUMN_NAME'],r['REFERENCED_TABLE_NAME']) for r in evidence['foreign_keys']}==expected_fk and all(r['REFERENCED_COLUMN_NAME']=='id' and r['UPDATE_RULE']==r['DELETE_RULE']=='RESTRICT' for r in evidence['foreign_keys']))
    q.execute("SELECT TABLE_NAME,CONSTRAINT_NAME,ENFORCED FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() AND CONSTRAINT_TYPE='CHECK'")
    evidence['check_constraints']=q.fetchall()
    check('all 20 CHECK constraints enforced', len(evidence['check_constraints'])==20 and all(c['ENFORCED']=='YES' for c in evidence['check_constraints']))
    conn.commit()
    if args.seed:
        q.execute("SELECT COUNT(*) AS n FROM users WHERE username LIKE 'dbstage_%'")
        check('test fixture prefix unused', q.fetchone()['n']==0)
        ts=now()
        ids=[]
        for i in range(4):
            salt=secrets.token_bytes(16)
            digest=hashlib.scrypt(secrets.token_bytes(32),salt=salt,n=16384,r=8,p=1).hex()
            password_hash='scrypt:16384:8:1$'+salt.hex()+'$'+digest
            q.execute('INSERT INTO users (username,password_hash,nickname,role,interest_tags,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)',(f'dbstage_user_{i}',password_hash,f'数据库验收用户{i}','admin' if i==0 else 'learner',json.dumps(['python','spark']),ts,ts))
            ids.append(q.lastrowid)
        resources=[]
        for i in range(6):
            q.execute('INSERT INTO resources (title,resource_type,category_code,tags,summary,content,source_name,license_note,status,created_by,published_at,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(f'数据库验收资源{i+1}', ['document','course','exercise'][i%3], 'data-engineering',json.dumps(['python','spark']),'仅供数据库结构与事务验收','自编测试说明，不包含业务教程','本项目测试','仅供开发验收','published',ids[0],ts,ts,ts))
            resources.append(q.lastrowid)
        user,resource=ids[1],resources[0]
        event_ids=[]
        uuids=[]
        def event(kind,before=None,after=None,effective=1):
            stamp=now()
            token=str(uuid.uuid4())
            fingerprint=hashlib.sha256(json.dumps([1,user,resource,kind],separators=(',',':')).encode()).hexdigest()
            q.execute('INSERT INTO learning_events (event_uuid,user_id,resource_id,event_type,event_source,resource_version,session_id,occurred_at,received_at,is_effective,state_before,state_after,request_fingerprint) VALUES (%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s)',(token,user,resource,kind,'client' if kind=='resource_view' else 'server',str(uuid.uuid4()) if kind=='resource_view' else None,stamp,stamp,effective,before,after,fingerprint))
            event_ids.append(q.lastrowid)
            uuids.append(token)
        event('resource_view')
        conn.commit()
        q.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(user,))
        stamp=now()
        q.execute('INSERT INTO learning_progress (user_id,resource_id,first_started_at,updated_at) VALUES (%s,%s,%s,%s)',(user,resource,stamp,stamp))
        event('learning_start','not_started','in_progress')
        conn.commit()
        q.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(user,))
        stamp=now()
        q.execute("UPDATE learning_progress SET status='completed',completed_at=%s,updated_at=%s WHERE user_id=%s AND resource_id=%s",(stamp,stamp,user,resource))
        event('learning_complete','in_progress','completed')
        conn.commit()
        q.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(user,))
        q.execute('INSERT INTO favorites VALUES (%s,%s,%s)',(user,resource,now()))
        event('favorite_add','not_favorited','favorited')
        conn.commit()
        q.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(user,))
        q.execute('DELETE FROM favorites WHERE user_id=%s AND resource_id=%s',(user,resource))
        event('favorite_remove','favorited','not_favorited')
        conn.commit()
        event('learning_complete','completed','completed',0)
        conn.commit()
        def reject(name,sql,params,code):
            try:
                q.execute(sql,params)
            except pymysql.MySQLError as exc:
                conn.rollback()
                check(name,exc.args[0]==code)
                return
            conn.rollback()
            check(name,False)
        reject('UUID duplicate rejected', 'INSERT INTO learning_events SELECT NULL,event_uuid,user_id,resource_id,event_type,event_source,schema_version,resource_version,session_id,occurred_at,received_at,client_occurred_at,is_effective,state_before,state_after,request_fingerprint FROM learning_events WHERE id=%s',(event_ids[0],),1062)
        reject('foreign key orphan rejected','INSERT INTO favorites VALUES (%s,%s,%s)',(18446744073709551615,resource,now()),1452)
        reject('invalid learning status rejected',"UPDATE learning_progress SET status='invalid' WHERE user_id=%s AND resource_id=%s",(user,resource),3819)
        reject('invalid event state combination rejected',"UPDATE learning_events SET state_after='not_started' WHERE id=%s",(event_ids[2],),3819)
        reject('RESTRICT prevents historical user deletion','DELETE FROM users WHERE id=%s',(user,),1451)
        # State change followed by an event UUID failure must roll back as a unit.
        q.execute('INSERT INTO favorites VALUES (%s,%s,%s)',(user,resource,now()))
        reject('event failure raises duplicate error', 'INSERT INTO learning_events SELECT NULL,event_uuid,user_id,resource_id,event_type,event_source,schema_version,resource_version,session_id,occurred_at,received_at,client_occurred_at,is_effective,state_before,state_after,request_fingerprint FROM learning_events WHERE id=%s',(event_ids[0],),1062)
        q.execute('SELECT COUNT(*) AS n FROM favorites WHERE user_id=%s AND resource_id=%s',(user,resource))
        check('state mutation rolled back after event failure',q.fetchone()['n']==0)
        q.execute('SELECT event_type,is_effective,COUNT(*) AS n FROM learning_events WHERE user_id=%s GROUP BY event_type,is_effective ORDER BY event_type,is_effective',(user,))
        evidence['test_events']=q.fetchall()
        check('five effective event types and one noop receipt',len(evidence['test_events'])==6 and sum(r['n'] for r in evidence['test_events'])==6)
        q.execute('SELECT status,completed_at IS NOT NULL AS has_completion FROM learning_progress WHERE user_id=%s AND resource_id=%s',(user,resource))
        check('learning completed persisted',q.fetchone()=={'status':'completed','has_completion':1})
        evidence['fixtures']={'user_ids':ids,'resource_ids':resources,'event_ids':event_ids,'users':4,'resources':6,'events':6,'progress':1,'favorites':0,'prefix':'dbstage_'}
        conn.commit()
    evidence['row_counts']={}
    for table in TABLES:
        q.execute('SELECT COUNT(*) AS n FROM '+table)
        evidence['row_counts'][table]=q.fetchone()['n']
    conn.close()
    evidence['passed_checks']=sum(c['passed'] for c in evidence['checks'])
    path=ROOT/'outputs/database-implementation-verification.json'
    path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'passed_checks':evidence['passed_checks'],'row_counts':evidence['row_counts'],'evidence':str(path)},ensure_ascii=False))

if __name__=='__main__':
    main()
