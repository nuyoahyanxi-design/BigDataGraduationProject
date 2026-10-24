from pydantic import BaseModel, Field

class PublicMetrics(BaseModel):
    unique_students:int=Field(ge=0)
    enrolments:int=Field(ge=0)
    modules:int=Field(ge=0)
    presentations:int=Field(ge=0)
    interaction_rows:int=Field(ge=0)
    total_clicks:int=Field(ge=0)
class DailyClicks(BaseModel):
    date:int
    clicks:int=Field(ge=0)
class Outcome(BaseModel):
    final_result:str
    count:int=Field(ge=0)
class Activity(BaseModel):
    activity_type:str
    clicks:int=Field(ge=0)
class ModuleClicks(BaseModel):
    code_module:str
    clicks:int=Field(ge=0)
class PublicQuality(BaseModel):
    input_rows:int=Field(ge=0)
    output_rows:int=Field(ge=0)
    invalid_rows:int=Field(ge=0)
    orphan_interactions:int=Field(ge=0)
    audit_reconciled:bool
    source_counts:dict[str,int]
class PublicEducationSummary(BaseModel):
    schema_version:int
    source_dataset:str
    source_kind:str
    source_doi:str
    source_url:str
    license:str
    citation:str
    source_period:str
    generated_at:str
    batch_id:str
    archive_sha256:str
    spark_version:str
    spark_master:str
    metrics:PublicMetrics
    daily_clicks:list[DailyClicks]=Field(max_length=2000)
    outcomes:list[Outcome]=Field(max_length=20)
    activity_clicks:list[Activity]=Field(max_length=100)
    module_clicks:list[ModuleClicks]=Field(max_length=100)
    quality:PublicQuality
    definitions:dict[str,str]
class PublicEducationResponse(BaseModel):
    available:bool
    data:PublicEducationSummary|None=None
    message:str|None=None
