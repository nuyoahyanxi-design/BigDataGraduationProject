"""Temporal audit and binary ranking evaluation, not a recommendation algorithm."""
import math
from pyspark.sql import functions as F

def time_partition(training_events,end_events,train_cutoff,test_cutoff):
    training=training_events.filter((F.col('occurred_at')<=F.to_timestamp(F.lit(train_cutoff))) & (F.col('received_at')<=F.to_timestamp(F.lit(train_cutoff))))
    test=end_events.filter((F.col('occurred_at')>F.to_timestamp(F.lit(train_cutoff))) & (F.col('occurred_at')<=F.to_timestamp(F.lit(test_cutoff))) & (F.col('received_at')<=F.to_timestamp(F.lit(test_cutoff))))
    late=end_events.filter((F.col('occurred_at')<=F.to_timestamp(F.lit(train_cutoff))) & (F.col('received_at')>F.to_timestamp(F.lit(train_cutoff))) & (F.col('received_at')<=F.to_timestamp(F.lit(test_cutoff))))
    if training.select('event_uuid').join(test.select('event_uuid'),'event_uuid').limit(1).count():
        raise ValueError('Train/test UUID overlap')
    return training,test,late

def evaluate(recommendations,positives,user_ids,catalog_ids,k=10):
    if type(k) is not int or k<=0:
        raise ValueError('k must be positive')
    users=set(user_ids);catalog=set(catalog_ids)
    truth={uid:set() for uid in users}
    for uid,rid in positives:
        if uid not in users or rid not in catalog:
            raise ValueError('Ground truth outside evaluation population/catalog')
        truth[uid].add(rid)
    output={}
    per_user=[]
    for algorithm in ['popular_v1','content_v1']:
        lists={uid:[] for uid in users}
        for row in recommendations:
            if row['algorithm'] not in ['popular_v1','content_v1']:
                raise ValueError('Unknown algorithm')
            if row['algorithm']!=algorithm:
                continue
            if row['user_id'] not in users or row['resource_id'] not in catalog or not 1<=row['rank']<=k:
                raise ValueError('Invalid recommendation identity/rank')
            lists[row['user_id']].append(row)
        coverage=set();evaluated_coverage=set();recalls=[];ndcgs=[]
        for uid in sorted(users):
            rows=sorted(lists[uid],key=lambda row:row['rank'])
            if [row['rank'] for row in rows]!=list(range(1,len(rows)+1)) or len({row['resource_id'] for row in rows})!=len(rows):
                raise ValueError('Duplicate resource or invalid rank sequence')
            prediction=[row['resource_id'] for row in rows];coverage.update(prediction)
            relevant=truth[uid]
            if relevant:
                recall=len(set(prediction)&relevant)/len(relevant)
                dcg=sum(1/math.log2(i+1) for i,rid in enumerate(prediction,1) if rid in relevant)
                idcg=sum(1/math.log2(i+1) for i in range(1,min(k,len(relevant))+1))
                ndcg=dcg/idcg
                recalls.append(recall);ndcgs.append(ndcg);evaluated_coverage.update(prediction)
            else:
                recall=ndcg=None
            per_user.append({'algorithm':algorithm,'user_id':uid,'positive_resources':sorted(relevant),'recommendation_count':len(prediction),'recall_at_10':recall,'ndcg_at_10':ndcg,'included_in_accuracy_mean':bool(relevant)})
        output[algorithm]={'recall_at_10':sum(recalls)/len(recalls) if recalls else None,'ndcg_at_10':sum(ndcgs)/len(ndcgs) if ndcgs else None,'coverage':len(coverage)/len(catalog) if catalog and users else None,'coverage_numerator':len(coverage),'coverage_denominator':len(catalog),'coverage_on_labeled_users':len(evaluated_coverage)/len(catalog) if catalog and recalls else None,'eligible_users':len(users),'evaluated_users':len(recalls),'users_without_labels':len(users)-len(recalls),'positive_pairs':sum(len(v) for v in truth.values())}
    comparable=output['popular_v1']['evaluated_users']>0
    return {'k':k,'accuracy_computable':comparable,'algorithms':output,'content_minus_popular':{'recall_at_10':output['content_v1']['recall_at_10']-output['popular_v1']['recall_at_10'] if comparable else None,'ndcg_at_10':output['content_v1']['ndcg_at_10']-output['popular_v1']['ndcg_at_10'] if comparable else None,'coverage':output['content_v1']['coverage']-output['popular_v1']['coverage'] if catalog and users else None},'per_user':per_user}
