export interface PublicEducationData {
 source_dataset:string; source_kind:string; source_doi:string; source_url:string; license:string; citation:string; source_period:string; generated_at:string; batch_id:string; archive_sha256:string; spark_version:string; spark_master:string
 metrics:{unique_students:number; enrolments:number; modules:number; presentations:number; interaction_rows:number; total_clicks:number}
 daily_clicks:{date:number;clicks:number}[]
 outcomes:{final_result:string;count:number}[]
 activity_clicks:{activity_type:string;clicks:number}[]
 module_clicks:{code_module:string;clicks:number}[]
 quality:{input_rows:number;output_rows:number;invalid_rows:number;orphan_interactions:number;audit_reconciled:boolean}
}
export interface PublicEducationResponse {available:boolean;data:PublicEducationData|null;message:string|null}
