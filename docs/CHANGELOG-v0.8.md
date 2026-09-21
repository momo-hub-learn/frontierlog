# v0.8 · Typography & Icon System

- 建立 Noto Sans SC / PingFang SC 正文、Manrope 展示、JetBrains Mono 数据字体层级。
- 远程字体在首屏加载后异步请求，失败自动回退系统字体。
- 增加 sparkles、zap、history、wrench、layers、pill、factory、cpu、gauge、radar、newspaper、flask 等内联 SVG。
- 重绘侧栏导航图标容器，并将热点分类、模型 / Benchmark、垂类内容类型、任务状态接入图标体系。
- 不改变内容数据、评分口径和采集状态。

验证：127 项单元测试通过；任务、热点、模型、Benchmark、行业专题浏览器回归通过。
