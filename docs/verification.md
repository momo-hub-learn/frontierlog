# v0.6 验收记录

本次在本地构建并检查，不代表线上已发布。

## 已完成

127 项离线单元测试通过。浏览器回归报告共记录 61 组检查：原有任务 14 组、行业主题 13 组、模型/重置 13 组、Benchmark 13 组、新热点榜 8 组。浏览器报告均未记录页面 JavaScript 错误。

v0.6 新增热点榜，覆盖排行、分类/搜索、证据抽屉、数据状态、JSON/RSS、首页热点摘要、移动端，以及 Benchmark 收进模型中心后的导航关系。热点分数明确为 FrontierLog 站内编辑信号，不宣称来自 AIHOT 或任何外部平台的浏览量/点赞量。

Benchmark 继续保留 20 条协议/数据集记录，并从侧栏独立入口调整为「模型榜 → Benchmark」页签；旧 `#/benchmarks` 深链接继续兼容，左侧模型导航保持激活。

这些是网站软件功能和数据约束测试，不是执行了 127 个 AI Benchmark。第三方 Benchmark 实际运行次数为 0，热点上游自动抓取实际运行次数也为 0。

## 未完成的环境验收

浏览器主要通过 Playwright `set_content` 内存渲染。环境策略阻止真实 HTTP/file 页面导航，因此没有在本次环境完成真实来源下的跨刷新持久化验证；没有绕过该限制。

真实 GitHub Pages v0.6 部署、线上自动采集、外部官方页面跳转、第三方基准复现，以及 AIHOT 数据接口均未在本次完成验证。热点榜使用本站独立整理的公开来源快照，不抓取或复制 AIHOT 的热度分数。

## 报告

`unit-tests.txt`、`test-summary.json`、`legacy-ui-tests.json`、`topic-ui-tests.json`、`model-ui-tests.json`、`benchmark-ui-tests.json`、`hot-ui-tests.json`、`origin-test-status.json`。来源与范围见 `HOTLIST.md`、`BENCHMARKS.md`、`benchmark-sources.md`。
