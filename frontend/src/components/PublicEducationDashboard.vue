<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElAlert, ElButton, ElCard, ElEmpty } from 'element-plus'
import EChart from './EChart.vue'
import { getPublicEducationDashboard } from '@/api/dashboard'
import { resourceError } from '@/services/resource-learning'
import type { PublicEducationResponse } from '@/types/public-education'
import type { EChartsOption } from 'echarts'
const response=ref<PublicEducationResponse>(),busy=ref(false),error=ref('')
const data=computed(()=>response.value?.data)
async function load(){if(busy.value)return;busy.value=true;error.value='';try{response.value=await getPublicEducationDashboard()}catch(e){error.value=resourceError(e)}finally{busy.value=false}}
const number=(value:number)=>new Intl.NumberFormat('zh-CN').format(value)
const outcomes:Record<string,string>={Pass:'通过',Distinction:'优秀',Fail:'未通过',Withdrawn:'退选'}
const activities:Record<string,string>={resource:'学习资源',forumng:'论坛',oucontent:'课程内容',subpage:'子页面',homepage:'首页',quiz:'测验',url:'外部链接',page:'页面',oucollaborate:'协作活动',ouwiki:'维基',questionnaire:'问卷',glossary:'词汇表',dataplus:'数据活动',dualpane:'双栏内容',externalquiz:'外部测验',folder:'文件夹',htmlactivity:'网页活动',ouelluminate:'在线研讨',repeatactivity:'重复活动',sharedsubpage:'共享子页面'}
const theme={color:['#ad7356','#66867c','#8b7c9e','#b09a5a','#6c8ca4'],animation:false,textStyle:{color:'#77736b',fontFamily:'system-ui, Microsoft YaHei, sans-serif'}}
const charts=computed(()=>{
 const d=data.value
 const trend:EChartsOption={...theme,tooltip:{trigger:'axis',renderMode:'richText'},grid:{left:65,right:20,bottom:60,top:20},xAxis:{type:'category',name:'相对日',data:d?.daily_clicks.map(x=>x.date)??[]},yAxis:{type:'value',name:'点击量',splitLine:{lineStyle:{color:'#ece6df',type:'dashed'}}},series:[{type:'line',name:'总点击量',showSymbol:false,data:d?.daily_clicks.map(x=>x.clicks)??[]}]}
 const outcome:EChartsOption={...theme,tooltip:{trigger:'item',renderMode:'richText'},legend:{bottom:0},series:[{type:'pie',radius:['35%','63%'],center:['50%','43%'],data:d?.outcomes.map(x=>({name:outcomes[x.final_result]??x.final_result,value:x.count}))??[]}]}
 const activity:EChartsOption={...theme,tooltip:{trigger:'axis',renderMode:'richText'},grid:{left:110,right:30,bottom:35,top:15},xAxis:{type:'value',name:'点击量'},yAxis:{type:'category',inverse:true,data:d?.activity_clicks.slice(0,8).map(x=>activities[x.activity_type]??x.activity_type)??[]},series:[{type:'bar',name:'点击量',barMaxWidth:20,data:d?.activity_clicks.slice(0,8).map(x=>x.clicks)??[]}]}
 const module:EChartsOption={...theme,tooltip:{trigger:'axis',renderMode:'richText'},grid:{left:65,right:20,bottom:40,top:20},xAxis:{type:'category',data:d?.module_clicks.map(x=>x.code_module)??[]},yAxis:{type:'value',name:'点击量'},series:[{type:'bar',name:'点击量',barMaxWidth:35,data:d?.module_clicks.map(x=>x.clicks)??[]}]}
 return {trend,outcome,activity,module}
})
onMounted(load)
</script>
<template>
 <section class="public-education">
  <header class="public-hero"><div><p class="public-eyebrow">OPEN EDUCATION DATA</p><h1>公开教育数据分析</h1><p>OULAD · 英国开放大学匿名学习数据</p></div><ElButton :loading="busy" @click="load">刷新展示</ElButton></header>
  <p class="public-scope">外部历史数据，采集于 2013–2014 年，不是本平台账号或学习记录。刷新页面不会运行分析任务。</p>
  <p v-if="busy" role="status">正在读取公开教育数据…</p><ElAlert v-else-if="error" :title="error" type="error" :closable="false"/><ElEmpty v-else-if="!data || !response?.available" :description="response?.message || '尚无已发布结果'"/>
  <template v-else>
   <div class="dashboard-counters public-counters"><ElCard shadow="never"><span>匿名学生数</span><strong>{{number(data.metrics.unique_students)}}</strong><small>按原始学生标识去重</small></ElCard><ElCard shadow="never"><span>选课记录数</span><strong>{{number(data.metrics.enrolments)}}</strong><small>同一学生可参加多个开课批次</small></ElCard><ElCard shadow="never"><span>匿名课程模块</span><strong>{{number(data.metrics.modules)}}</strong><small>{{data.metrics.presentations}} 个开课批次</small></ElCard><ElCard shadow="never"><span>聚合交互记录</span><strong>{{number(data.metrics.interaction_rows)}}</strong><small>学生 × 资源 × 相对日，不是单次播放</small></ElCard></div>
   <p class="public-total">总点击量 <strong>{{number(data.metrics.total_clicks)}}</strong> · 原始 sum_click 汇总</p>
   <div class="dashboard-panels"><ElCard shadow="never"><h2>学习交互趋势</h2><p class="chart-source">按各课程开课相对日对齐汇总；负数表示开课前，不是自然日期。</p><EChart :option="charts.trend" label="公开数据相对日点击趋势"/></ElCard><ElCard shadow="never"><h2>原始选课结果分布</h2><p class="chart-source">按选课记录统计原始最终结果，不等于平台章节完成率。</p><EChart :option="charts.outcome" label="公开数据选课结果分布"/></ElCard><ElCard shadow="never"><h2>学习活动点击量</h2><p class="chart-source">点击量最高的 8 类原始活动；其余分类可在数据说明中查看。</p><EChart :option="charts.activity" label="公开数据活动点击量"/></ElCard><ElCard shadow="never"><h2>课程模块交互量</h2><p class="chart-source">原始匿名课程代码，未映射为本平台五门课程。</p><EChart :option="charts.module" label="公开数据课程模块点击量"/></ElCard></div>
   <details class="public-notes"><summary>来源、批次与数据质量</summary><dl class="user-details"><dt>来源</dt><dd><a :href="data.source_url" target="_blank" rel="noopener noreferrer">UCI 官方 OULAD 数据集</a> · {{data.source_doi}}</dd><dt>引用</dt><dd>{{data.citation}}</dd><dt>许可</dt><dd>{{data.license}}</dd><dt>数据年代</dt><dd>{{data.source_period}}</dd><dt>处理时间</dt><dd>{{data.generated_at}}</dd><dt>运行环境</dt><dd>Spark {{data.spark_version}} · {{data.spark_master}}</dd><dt>批次</dt><dd>{{data.batch_id}}</dd><dt>输入／输出</dt><dd>{{number(data.quality.input_rows)}} / {{number(data.quality.output_rows)}}；异常 {{data.quality.invalid_rows}}，关联缺失 {{data.quality.orphan_interactions}}</dd><dt>原件校验</dt><dd>{{data.archive_sha256}}</dd></dl><p>ODS 保留原始字段，DWD 规范缺失值和交互字段；DWS 为任务内逻辑聚合，ADS 为本页汇总。未生成本平台用户画像、收藏、视频完成或推荐效果指标。</p><ul><li v-for="row in data.activity_clicks" :key="row.activity_type">{{activities[row.activity_type]??row.activity_type}}（{{row.activity_type}}）：{{number(row.clicks)}}</li></ul></details>
  </template>
 </section>
</template>
<style scoped>
.public-hero{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:24px;background:linear-gradient(110deg,#edf2ee,#f5f1e9);border:1px solid #dfe5dd;border-radius:14px}.public-hero h1{font-size:28px;margin:8px 0;color:#292f29}.public-hero p{margin:0;font-size:13px}.public-eyebrow{font-size:10px!important;letter-spacing:2px;color:#738377}.public-scope{font-size:12px;margin:16px 0;color:#77736b}.public-counters .el-card{border-top:3px solid #8b9e8d}.public-counters span{font-size:12px}.public-counters strong{font-size:30px}.public-total{font-size:13px;background:#f5f0e8;padding:12px 16px;border-radius:8px}.public-total strong{color:#a9583e;font-variant-numeric:tabular-nums}.public-notes{border:1px solid #e6dfd8;border-radius:10px;background:#fff;padding:20px 24px;margin-top:24px;font-size:13px}.public-notes summary{cursor:pointer;font-weight:600;color:#8e624b}.public-notes p,.public-notes li{font-size:12px;line-height:1.8}.public-notes .user-details{grid-template-columns:80px minmax(0,1fr)}@media(max-width:600px){.public-hero{padding:20px;align-items:flex-start}.public-hero h1{font-size:23px}.public-notes{padding:18px}.public-counters strong{font-size:28px}}
</style>
