"""Read only the dedicated external-data publication; never query analytics tables."""
import json
from pathlib import Path
from fastapi import HTTPException
from pydantic import ValidationError
from app.schemas.public_education import PublicEducationSummary
BASE=Path(__file__).resolve().parents[3]/'data/external/oulad'

def published_education():
    latest=BASE/'analysis/latest.json'
    if not latest.exists():return {'available':False,'data':None,'message':'公开教育数据尚未发布'}
    try:
        if latest.stat().st_size>4096:raise ValueError()
        pointer=json.loads(latest.read_text(encoding='utf-8'))
        target=(BASE/pointer['summary']).resolve()
        if not target.is_relative_to((BASE/'analysis').resolve()) or target.name!='summary.json':raise ValueError()
        if target.stat().st_size>2*1024*1024:raise ValueError()
        data=PublicEducationSummary.model_validate_json(target.read_text(encoding='utf-8'))
        if data.source_dataset!='OULAD' or data.source_kind!='external_anonymised_education_data' or data.batch_id!=pointer['batch_id'] or data.spark_master!='local[2]':raise ValueError()
        return {'available':True,'data':data,'message':None}
    except (OSError,ValueError,KeyError,TypeError,ValidationError):
        raise HTTPException(503,'Published public education data unavailable') from None
