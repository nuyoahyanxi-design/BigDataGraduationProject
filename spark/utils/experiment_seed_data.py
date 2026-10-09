"""Explicit offline synthetic records, never database writes or API receipts."""
import copy
from datetime import datetime,timedelta
import hashlib
import json
import random
from uuid import UUID

THEMES=[
 ('python','Python','python-basics',['python'],['变量与类型','条件分支','循环','函数','列表与字典','文件读写','异常处理','模块','数据清洗','迭代器']),
 ('spark','Spark','data-engineering',['spark','big-data'],['运行机制','DataFrame','Spark SQL','转换与行动','分区','聚合','连接','Parquet','缓存','批处理']),
 ('machine-learning','机器学习','machine-learning',['machine-learning'],['训练测试划分','特征处理','线性回归','分类','决策树','过拟合','交叉验证','评价指标','聚类','模型解释']),
 ('database','数据库','databases',['sql','mysql'],['关系模型','主键外键','查询','连接查询','索引','事务','约束','分组聚合','规范化','字符集']),
 ('analysis','大数据分析','data-engineering',['data-analysis','big-data'],['数据质量','探索分析','缺失值','异常值','统计汇总','时间分析','分层存储','用户行为','可视化解读','结果复现'])]
ALLOWED_TAGS={'python','java','sql','mysql','spark','big-data','data-analysis','machine-learning','web-development','algorithms'}

def stamp(value):
    return value.isoformat(sep=' ',timespec='milliseconds')

class Simulator:
    def __init__(self,users,resources,seed):
        self.users={u['id']:u for u in users};self.resources={r['id']:r for r in resources}
        self.random=random.Random(seed);self.events=[];self.progress={};self.favorites={}

    def uuid(self):
        return str(UUID(int=self.random.getrandbits(128),version=4))

    def act(self,uid,rid,kind,when):
        if self.users[uid]['role']!='learner' or self.users[uid]['status']!='active' or self.resources[rid]['status']!='published':
            raise ValueError('Actor/resource unavailable')
        pair=(uid,rid);time=stamp(when);before=after=None;effective=1
        if kind=='learning_start':
            before=self.progress.get(pair,{}).get('status','not_started')
            after='in_progress' if before=='not_started' else before
            if before=='not_started':
                self.progress[pair]={'user_id':uid,'resource_id':rid,'status':after,'first_started_at':time,'completed_at':None,'updated_at':time}
            else:
                effective=0
        elif kind=='learning_complete':
            if pair not in self.progress:
                raise ValueError('Start before complete')
            before=self.progress[pair]['status'];after='completed'
            if before=='completed':
                effective=0
            else:
                self.progress[pair].update(status=after,completed_at=time,updated_at=time)
        elif kind=='favorite_add':
            before='favorited' if pair in self.favorites else 'not_favorited';after='favorited'
            if pair in self.favorites:
                effective=0
            else:
                self.favorites[pair]={'user_id':uid,'resource_id':rid,'created_at':time}
        elif kind=='favorite_remove':
            before='favorited' if pair in self.favorites else 'not_favorited';after='not_favorited'
            if pair in self.favorites:
                del self.favorites[pair]
            else:
                effective=0
        elif kind!='resource_view':
            raise ValueError('Unsupported behavior')
        event={'id':len(self.events)+1,'event_uuid':self.uuid(),'user_id':uid,'resource_id':rid,'event_type':kind,'event_source':'client' if kind=='resource_view' else 'server','schema_version':1,'resource_version':1,'session_id':self.uuid() if kind=='resource_view' else None,'occurred_at':time,'received_at':time,'client_occurred_at':None,'is_effective':effective,'state_before':before,'state_after':after,'request_fingerprint':hashlib.sha256(json.dumps([1,uid,rid,kind],separators=(',',':')).encode()).hexdigest()}
        self.events.append(event)
        return event

    def snapshot(self):
        return {'users':copy.deepcopy(list(self.users.values())),'resources':copy.deepcopy(list(self.resources.values())),'learning_progress':copy.deepcopy(list(self.progress.values())),'favorites':copy.deepcopy(list(self.favorites.values())),'learning_events':copy.deepcopy(self.events)}

def build_seed_data(config,on_training_snapshot=None):
    if config['version']!='v1' or config['learners']!=30 or config['resources_per_theme']!=10:
        raise ValueError('Unsupported v1 seed dimensions')
    rng=random.Random(config['random_seed']);created='2026-10-01 08:00:00.000'
    users=[];groups=[];resources=[];payloads=[]
    for index in range(30):
        primary=index%5;secondary=(primary+1+(index//5)%4)%5
        behavior_only=20<=index<25;cold=index>=25
        interests=[] if behavior_only else sorted(set(THEMES[primary][3]+THEMES[secondary][3]))
        uid=index+1
        users.append({'id':uid,'role':'learner','status':'active','interest_tags':json.dumps(interests),'created_at':created,'updated_at':created})
        groups.append({'user_id':uid,'simulated_username':f'sim_exp_{uid:02d}','primary_theme':THEMES[primary][0],'secondary_theme':THEMES[secondary][0],'group':'explicit_cold_start' if cold else ('behavior_only' if behavior_only else 'explicit_and_behavior'),'interest_tags':interests})
    users.append({'id':31,'role':'admin','status':'active','interest_tags':'[]','created_at':created,'updated_at':created})
    for theme,(_,name,category,tags,topics) in enumerate(THEMES):
        for offset,topic in enumerate(topics):
            rid=theme*10+offset+1
            resource={'id':rid,'title':f'[模拟种子] {name}：{topic}','resource_type':['document','course','exercise'][offset%3],'category_code':category,'tags':json.dumps(tags),'difficulty':offset%3+1,'summary':f'自编实验种子，主题为{name}的{topic}；用于受控标签推荐验证，不代表真实课程质量。','source_name':'synthetic experiment seed','license_note':'本项目自编模拟材料，仅用于开发和实验演示','status':'published','version_no':1,'created_by':31,'published_at':'2026-10-01 08:01:00.000','created_at':created,'updated_at':'2026-10-01 08:01:00.000'}
            resources.append(resource)
            payloads.append({'simulated_resource_id':rid,'theme':THEMES[theme][0],**{k:resource[k] for k in ['title','resource_type','category_code','difficulty','summary','source_name','license_note']},'tags':tags,'content':f'模拟学习材料：围绕{topic}记录一个基础概念、一个应用场景和一个自测问题。学习时描述该概念的输入与输出，并检查自己的解释是否一致。此内容为实验种子占位教学材料，不是完整课程。'})
    sim=Simulator(users,resources,config['random_seed']+1)
    def choose(group,count,excluded):
        primary=next(i for i,t in enumerate(THEMES) if t[0]==group['primary_theme'])
        secondary=next(i for i,t in enumerate(THEMES) if t[0]==group['secondary_theme'])
        selected=[]
        for _ in range(count):
            draw=rng.random()
            theme=primary if draw<0.65 else secondary if draw<0.9 else rng.choice([i for i in range(5) if i not in [primary,secondary]])
            available=[theme*10+j+1 for j in range(10) if theme*10+j+1 not in excluded and theme*10+j+1 not in selected]
            if not available:
                available=[r['id'] for r in resources if r['id'] not in excluded and r['id'] not in selected]
            selected.append(rng.choice(available))
        return selected
    sequence=0
    for group in groups:
        if group['group']=='explicit_cold_start':
            continue
        uid=group['user_id'];day=1 if uid<=15 else 2
        for index,rid in enumerate(choose(group,config['train_interactions_per_user'],set())):
            base=datetime(2026,10,day,9)+timedelta(seconds=sequence*10);sequence+=1
            sim.act(uid,rid,'resource_view',base)
            started=index==0 or rng.random()<0.85
            if started:
                sim.act(uid,rid,'learning_start',base+timedelta(seconds=1))
                if index==0 or rng.random()<0.5:
                    sim.act(uid,rid,'learning_complete',base+timedelta(seconds=2))
            if index==0 or rng.random()<0.35:
                sim.act(uid,rid,'favorite_add',base+timedelta(seconds=3))
    train=sim.snapshot()
    if on_training_snapshot is not None:
        on_training_snapshot(copy.deepcopy(train))
    for group in groups:
        uid=group['user_id']
        already_started={rid for (user,rid) in sim.progress if user==uid}
        for index,rid in enumerate(choose(group,config['test_interactions_per_user'],already_started)):
            base=datetime(2026,10,3,9)+timedelta(seconds=sequence*10);sequence+=1
            sim.act(uid,rid,'resource_view',base)
            sim.act(uid,rid,'learning_start',base+timedelta(seconds=1))
            if index==0 or rng.random()<0.6:
                sim.act(uid,rid,'learning_complete',base+timedelta(seconds=2))
            if rng.random()<0.4:
                sim.act(uid,rid,'favorite_add',base+timedelta(seconds=3))
    return {'train':train,'test_end':sim.snapshot(),'resource_payloads':payloads,'user_groups':groups,'origin':'synthetic_state_machine_v1','seed':config['random_seed']}
