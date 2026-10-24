"""Explainable Spark popularity and sparse binary-tag cosine Top-N."""
from pyspark.sql import functions as F, Window
from pathlib import Path

SOURCE_BYTES = Path(__file__).read_bytes()

ALGORITHMS=['popular_v1','content_v1']


def canonical_tag(column):
    return (F.when(column.isin('sql','mysql','数据库'),F.lit('database'))
            .when(column.isin('spark','pyspark','rdd'),F.lit('spark'))
            .when(column.isin('ml','machine-learning'),F.lit('machine-learning'))
            .when(column.isin('大数据','big-data'),F.lit('big-data')).otherwise(column))


def eligible_resources(resources):
    from spark.utils.resource_scope import eligible
    return eligible(resources)

def validate_parameters(parameters):
    expected={'version','top_n','weights','business_timezone','max_candidate_pairs','max_output_rows'}
    if set(parameters)!=expected or parameters['version']!='v1' or parameters['business_timezone']!='Asia/Shanghai':
        raise ValueError('Unsupported recommendation parameters')
    for key,limit in [('top_n',100),('max_candidate_pairs',2000000),('max_output_rows',50000)]:
        value=parameters[key]
        if type(value) is not int or not 1<=value<=limit:
            raise ValueError('Invalid parameter: '+key)
    weights=parameters['weights']
    if set(weights)!={'view','start','complete','favorite'} or any(type(v) is not int or not 1<=v<=100 for v in weights.values()):
        raise ValueError('Invalid popularity weights')

def compute_recommendations(profiles,users,resources,events,progress,cutoff,parameters,chapter_events=None,progress_is_canonical=False):
    validate_parameters(parameters)
    people=users.filter((F.col('role')=='learner') & (F.col('status')=='active')).select(F.col('id').alias('user_id')).distinct()
    p=profiles.select('user_id',F.from_json('interest_profile','struct<weights:map<string,double>,evidence:string>').alias('ip')).select('user_id','ip.*')
    if p.groupBy('user_id').count().filter('count > 1').limit(1).count():
        raise ValueError('Duplicate user profile')
    if p.select('user_id').exceptAll(people).limit(1).count() or people.exceptAll(p.select('user_id')).limit(1).count():
        raise ValueError('Profiles do not cover active snapshot learners exactly')
    if p.filter(F.col('weights').isNull() | F.col('evidence').isNull() | ~F.col('evidence').isin('observed','explicit_only','no_evidence') | F.expr("exists(map_values(weights), x -> x is null or isnan(x) or x < 0 or x > 1)") | F.expr("exists(map_keys(weights), x -> length(trim(x)) = 0)")).limit(1).count():
        raise ValueError('Invalid interest vector')
    p=p.withColumn('norm',F.sqrt(F.expr('aggregate(map_values(weights), cast(0 as double), (a,x) -> a+x*x)')))
    if 'interest_tags' in users.columns:
        explicit=users.select(F.col('id').alias('user_id'),F.array_distinct(F.from_json('interest_tags','array<string>')).alias('explicit'))
        p=p.join(explicit,'user_id').withColumn('weights',F.when(F.size('explicit')>0,
            F.expr('map_from_arrays(explicit, transform(explicit, x -> cast(1 as double)))')).otherwise(F.col('weights')))
        p=p.withColumn('norm',F.sqrt(F.expr('aggregate(map_values(weights), cast(0 as double), (a,x) -> a+x*x)')))
    eligible=eligible_resources(resources)
    r=eligible.select(F.col('id').alias('resource_id'),'status',F.array_sort(F.array_distinct(F.from_json('tags','array<string>'))).alias('tags')).distinct()
    if r.groupBy('resource_id').count().filter('count > 1').limit(1).count():
        raise ValueError('Conflicting resource snapshots')
    r=r.filter(F.col('status')=='published')
    if r.filter(F.col('tags').isNull() | F.expr("exists(tags, x -> x is null or length(trim(x)) = 0)")).limit(1).count():
        raise ValueError('Invalid published resource tags')
    # Synonyms broaden the topic match without changing stored business tags.
    r=r.withColumn('tags',F.array_sort(F.array_distinct(F.transform('tags',canonical_tag))))
    weights=p.select('user_id',F.explode('weights').alias('tag','weight')).withColumn('tag',canonical_tag(F.col('tag')))
    weights=weights.groupBy('user_id','tag').agg(F.sum('weight').alias('weight')).groupBy('user_id').agg(F.map_from_entries(F.collect_list(F.struct('tag','weight'))).alias('normalized_weights'))
    p=p.join(weights,'user_id','left').withColumn('weights',F.coalesce('normalized_weights',F.col('weights'))).drop('normalized_weights')
    p=p.withColumn('norm',F.sqrt(F.expr('aggregate(map_values(weights), cast(0 as double), (a,x) -> a+x*x)')))
    user_count=people.count();resource_count=r.count()
    if user_count*resource_count>parameters['max_candidate_pairs']:
        raise ValueError('Candidate pair limit exceeded; no truncation performed')
    e=events.filter((F.col('is_effective')==1)&(F.col('occurred_at')<=F.to_timestamp(F.lit(cutoff)))).join(people,'user_id')
    e=e.withColumn('day',F.to_date(F.from_utc_timestamp('occurred_at',parameters['business_timezone'])))
    v=e.filter(F.col('event_type')=='resource_view').select('user_id','resource_id','day').distinct().groupBy('resource_id').count().withColumnRenamed('count','views')
    s=e.filter(F.col('event_type')=='learning_start').select('user_id','resource_id').distinct().groupBy('resource_id').count().withColumnRenamed('count','starts')
    c=e.filter(F.col('event_type')=='learning_complete').select('user_id','resource_id').distinct().groupBy('resource_id').count().withColumnRenamed('count','completes')
    latest=Window.partitionBy('user_id','resource_id').orderBy(F.col('occurred_at').desc(),F.col('id').desc())
    f=e.filter(F.col('event_type').isin('favorite_add','favorite_remove')).withColumn('_latest',F.row_number().over(latest)).filter((F.col('_latest')==1)&(F.col('event_type')=='favorite_add')).groupBy('resource_id').count().withColumnRenamed('count','favorites')
    w=parameters['weights']
    personal_views=e.filter(F.col('event_type')=='resource_view').select('user_id','resource_id','day').distinct().select('user_id','resource_id',F.lit(w['view']).alias('value'))
    personal_other=e.filter(F.col('event_type').isin('learning_start','learning_complete')).select('user_id','resource_id','event_type').distinct().select('user_id','resource_id',F.when(F.col('event_type')=='learning_start',w['start']).otherwise(w['complete']).alias('value'))
    personal_favorites=e.filter(F.col('event_type').isin('favorite_add','favorite_remove')).withColumn('_latest',F.row_number().over(latest)).filter((F.col('_latest')==1)&(F.col('event_type')=='favorite_add')).select('user_id','resource_id',F.lit(w['favorite']).alias('value'))
    if progress_is_canonical:
        current=progress.join(people,'user_id')
        s=current.filter(F.col('status').isin('in_progress','completed')).select('user_id','resource_id').distinct().groupBy('resource_id').count().withColumnRenamed('count','starts')
        c=current.filter("status='completed'").select('user_id','resource_id').distinct().groupBy('resource_id').count().withColumnRenamed('count','completes')
        personal_other=current.filter(F.col('status').isin('in_progress','completed')).select('user_id','resource_id',F.lit(w['start']).alias('value')).unionByName(current.filter("status='completed'").select('user_id','resource_id',F.lit(w['complete']).alias('value')))
    chapter_heat=None
    if chapter_events is not None:
        from spark.utils.chapter_analytics import learner_events,signals
        ce=learner_events(chapter_events,users,cutoff)
        chapter_heat=signals(ce).groupBy('user_id','resource_id').agg(F.sum('weight').alias('value'))
        personal_views=personal_views.unionByName(chapter_heat)
    personal=personal_views.unionByName(personal_other).unionByName(personal_favorites).groupBy('user_id','resource_id').agg(F.sum('value').alias('personal_heat'))
    personal=personal.withColumn('behavior_score',F.col('personal_heat')/F.max('personal_heat').over(Window.partitionBy('user_id'))).select('user_id','resource_id','behavior_score')
    history=e.select('user_id').distinct().withColumn('has_history',F.lit(True))
    if progress_is_canonical:
        history=history.select('user_id').unionByName(current.filter(F.col('status').isin('in_progress','completed')).select('user_id')).distinct().withColumn('has_history',F.lit(True))
    heat=r.join(v,'resource_id','left').join(s,'resource_id','left').join(c,'resource_id','left').join(f,'resource_id','left').fillna({k:0 for k in ['views','starts','completes','favorites']}).withColumn('heat',F.col('views')*w['view']+F.col('starts')*w['start']+F.col('completes')*w['complete']+F.col('favorites')*w['favorite'])
    if chapter_heat is not None:
        history=history.select('user_id').unionByName(ce.select('user_id')).distinct().withColumn('has_history',F.lit(True))
        heat=heat.join(chapter_heat.groupBy('resource_id').agg(F.sum('value').alias('chapter_heat')),'resource_id','left').fillna({'chapter_heat':0.0}).withColumn('heat',F.col('heat')+F.col('chapter_heat'))
    completed=progress.filter(F.col('status')=='completed').select('user_id','resource_id').unionByName(e.filter(F.col('event_type')=='learning_complete').select('user_id','resource_id')).distinct()
    if progress_is_canonical:
        completed=progress.filter("status='completed'").select('user_id','resource_id').distinct()
    max_heat=heat.agg(F.max('heat').alias('maximum'))
    heat=heat.crossJoin(max_heat).withColumn('popularity_score',F.when(F.col('maximum')>0,F.col('heat')/F.col('maximum')).otherwise(0.0)).drop('maximum')
    candidates=(p.crossJoin(heat).join(completed,['user_id','resource_id'],'left_anti').join(personal,['user_id','resource_id'],'left').join(history,'user_id','left').fillna({'behavior_score':0.0,'has_history':False})
        .withColumn('dot',F.expr('aggregate(tags, cast(0 as double), (a,t) -> a+coalesce(element_at(weights,t),cast(0 as double)))'))
        .withColumn('similarity',F.when((F.col('norm')>0)&(F.size('tags')>0),F.round(F.least(F.lit(1.0),F.col('dot')/(F.col('norm')*F.sqrt(F.size('tags')))),12)).otherwise(0.0))
        .withColumn('matched',F.expr('filter(tags, t -> coalesce(element_at(weights,t),cast(0 as double)) > 0)'))
        .withColumn('recommend_score',F.round(F.when(F.col('has_history'),F.col('similarity')*0.6+F.col('behavior_score')*0.25+F.col('popularity_score')*0.15).otherwise(F.col('popularity_score')),12))).cache()
    try:
        popularity_reason=F.when(F.col('heat')>0,F.lit('热门资源推荐')).otherwise(F.lit('热门资源推荐：暂无历史热度，作为候选资源补充'))
        fallback_reason=F.concat(F.when(F.col('norm')==0,F.lit('无可用兴趣向量，热门回退：')).otherwise(F.lit('无标签匹配，热门回退：')),popularity_reason)
        match_reason=F.concat(F.lit('与你的学习兴趣匹配：'),F.concat_ws('、',F.slice(F.transform('matched',lambda t: F.when(t=='spark','Spark').when(t=='database','数据库').otherwise(t)),1,5)))
        frames=[]
        for algorithm in ALGORITHMS:
            is_popular=algorithm=='popular_v1'
            order=[F.col('heat').desc(),F.col('resource_id').asc()] if is_popular else [F.col('recommend_score').desc(),F.col('heat').desc(),F.col('resource_id').asc()]
            frame=candidates.withColumn('rank',F.row_number().over(Window.partitionBy('user_id').orderBy(*order))).filter(F.col('rank')<=parameters['top_n'])
            frames.append(frame.select('user_id','resource_id',F.lit(algorithm).alias('algorithm'),(F.col('heat') if is_popular else F.col('recommend_score')).cast('decimal(24,12)').alias('score'),'rank',(popularity_reason if is_popular else F.when(~F.col('has_history'),F.concat(F.lit('无历史行为，热门回退：'),popularity_reason)).when(F.col('similarity')>0,match_reason).when(F.col('behavior_score')>0,F.lit('基于你的浏览、学习和收藏记录推荐')).otherwise(fallback_reason)).alias('reason')))
        rows=frames[0].unionByName(frames[1]).orderBy('user_id','algorithm','rank').limit(parameters['max_output_rows']+1).collect()
        if len(rows)>parameters['max_output_rows']:
            raise ValueError('Recommendation output limit exceeded; no truncation performed')
        result=[dict(row.asDict(),score=format(row.score,'.12f')) for row in rows]
        zero_users=user_count-len({row['user_id'] for row in result})
        return result,{'users':user_count,'published_resources':resource_count,'candidate_pairs_before_completion_filter':user_count*resource_count,'zero_result_users':zero_users,'output_rows':len(result)}
    finally:
        candidates.unpersist()
