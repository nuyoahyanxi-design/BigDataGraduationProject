import copy
from datetime import datetime
import hashlib
import json
import sys
from uuid import UUID
import pytest
from spark.utils.config import ROOT
from spark.utils.experiment_seed_data import build_seed_data,Simulator,ALLOWED_TAGS

@pytest.fixture(scope='module')
def config():
    return json.loads((ROOT/'spark/configs/experiment-data-preparation.json').read_text())

@pytest.fixture(scope='module')
def data(config):
    return build_seed_data(config)

def test_resource_count_topics_and_formal_payload_validation(data):
    sys.path.insert(0,str(ROOT/'backend'))
    from app.schemas.resources import ResourceWrite
    assert len(data['resource_payloads'])==50
    assert len({row['theme'] for row in data['resource_payloads']})==5
    for row in data['resource_payloads']:
        assert set(row['tags'])<=ALLOWED_TAGS
        ResourceWrite.model_validate({k:v for k,v in row.items() if k not in ['simulated_resource_id','theme']})

def test_users_interest_groups_and_references(data):
    assert len(data['user_groups'])==30
    assert sum(u['role']=='learner' for u in data['train']['users'])==30
    interests={u['interest_tags'] for u in data['train']['users'] if u['role']=='learner'}
    assert len(interests)>5
    assert sum(g['group']=='explicit_cold_start' for g in data['user_groups'])==5
    ids={u['id'] for u in data['train']['users']}
    assert all(r['created_by'] in ids for r in data['train']['resources'])

def test_order_isolation_and_test_labels(data,config):
    train=data['train']['learning_events'];end=data['test_end']['learning_events']
    ids={e['event_uuid'] for e in train};test=[e for e in end if e['event_uuid'] not in ids]
    assert max(e['occurred_at'] for e in train)<config['train_cutoff_utc']<min(e['occurred_at'] for e in test)<config['test_cutoff_utc']
    starts={(e['user_id'],e['resource_id']) for e in test if e['event_type']=='learning_start' and e['is_effective']==1}
    assert len(starts)==90 and len({uid for uid,_ in starts})==30
    train_started={(p['user_id'],p['resource_id']) for p in data['train']['learning_progress']}
    assert not starts&train_started
    assert all(p['updated_at']<=config['train_cutoff_utc'] for p in data['train']['learning_progress'])
    assert all(e['user_id']<=25 for e in train)

def test_uuid_fingerprints_sources_and_effectiveness(data):
    events=data['test_end']['learning_events']
    assert len({e['event_uuid'] for e in events})==len(events)
    for e in events:
        assert UUID(e['event_uuid']).version==4
        assert e['request_fingerprint']==hashlib.sha256(json.dumps([1,e['user_id'],e['resource_id'],e['event_type']],separators=(',',':')).encode()).hexdigest()
        assert e['event_source']==('client' if e['event_type']=='resource_view' else 'server')
        assert e['received_at']<=e['occurred_at']

def test_state_machine_rejects_completion_and_handles_noop(data):
    sim=Simulator(data['train']['users'],data['train']['resources'],7)
    time=datetime(2026,10,1,9)
    with pytest.raises(ValueError,match='Start before complete'):
        sim.act(1,1,'learning_complete',time)
    assert sim.act(1,1,'learning_start',time)['is_effective']==1
    assert sim.act(1,1,'learning_start',time)['is_effective']==0
    assert sim.act(1,1,'learning_complete',time)['is_effective']==1
    assert sim.act(1,1,'learning_complete',time)['is_effective']==0
    assert sim.act(1,1,'favorite_add',time)['is_effective']==1
    assert sim.act(1,1,'favorite_remove',time)['is_effective']==1
    assert sim.act(1,1,'favorite_remove',time)['is_effective']==0

def test_deterministic_seed_and_training_callback_before_test(data,config):
    captures=[]
    def callback(snapshot):
        assert all(e['occurred_at']<=config['train_cutoff_utc'] for e in snapshot['learning_events'])
        captures.append(copy.deepcopy(snapshot))
    other=build_seed_data(config,callback)
    assert other==data and captures==[data['train']]
    other['test_end']['resources'][0]['tags']='["sql"]'
    assert data['train']['resources'][0]['tags']!='["sql"]'
