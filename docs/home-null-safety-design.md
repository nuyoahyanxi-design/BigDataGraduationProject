# 首页空值渲染修复设计

目标：仅修复HomeView.vue缺少兴趣标签时访问length导致白屏，不改接口、数据库或业务逻辑。

检查：模板auth.user受v-if保护；字符串插值允许空值。唯一未保护的嵌套length是auth.user.interest_tags.length，接口字段缺失或null时抛出异常。标签循环使用同一字段，统一通过computed转换为空数组，维持正常标签及暂无兴趣标签的展示效果。

验证：用真实HomeView组件SSR渲染，模拟当前用户接口返回null、空对象、缺少兴趣字段、null标签、空标签和正常标签，检查页面及按钮正常输出；运行npm test与npm run build。
