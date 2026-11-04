# AI坐标｜中文 AI 官方信源与公众号接入

该扩展是 AI 坐标零模型调用采集流水线的一个模块，覆盖字节跳动 Seed、腾讯混元、DeepSeek、Kimi。

## 信源身份

信源配置：data/cn-official-sources.json。公众号名称与官方可证实网站分别标识，不能仅因公司名相似而自动认为是官方号。

- 字节跳动 Seed：以 seed.bytedance.com/zh/research 一手技术文章作为自动抓取源；微信公众号“字节跳动 Seed”名称需通过公众号认证页再次确认。
- 腾讯混元：微信公众号“腾讯混元”在腾讯云开发者社区的混元专区列明；官方 hunyuan.tencent.com 页属于可监测信源，但如其 HTML 没有可读公告链接，标记该来源失败或不可解析，不宣称公众号更新成功。
- DeepSeek：以 deepseek.com/news/ 和 api-docs.deepseek.com/zh-cn/updates/ 为官方信源；DeepSeek 2025 年发布过官方公众号身份说明，但原微信文章正文不可在当前环境直接核验。官方 API changelog 页面只监测变动指纹，不从缺乏文章级时间的页面伪造发布日期。
- Kimi：公众号“月之暗面Kimi”由 kimi.com/help/others/contact-support 直接确认；技术更新监测 platform.kimi.com/docs/llms.txt 的官方 Markdown 索引。

## 抓取范围

- 每次工作流运行，按固定域名、合法 HTTPS、指定路径筛选第一方官网文章/文档链接。
- 自动收录 data/cn-official-inbox.json，所有候选标记 review_status=unreviewed。
- 只能将官网文章标题、URL 记为“第一方官网索引线索”；没有源时间的 published_at 为 null，first_seen_at 是本站首次见到该 URL 的时间。
- HTML 页面动态渲染、来源反爬、安全拦截或索引解析失败，都在独立来源状态中记录错误，不能说“没有新闻”。
- page_watch 页面只能产生“页面变动待编辑检查”，**不是**新发布事实。
- 已被人工审核（approved/rejected）的候选，自动刷新不能覆盖其状态、批注、first_seen_at。
- 不抓取公众号历史列表，不使用 cookies、浏览器指纹、收费或未经授权的第三方聚合服务。不规避频控/验证码。

## 公众号原创链接入口

如从微信公众号官方发布的文章中取得可公开访问的原文链接，可添加到 data/wechat-original-links.json：

~~~json
{
  "version": 1,
  "items": [
    {"publisher_id": "deepseek", "url": "https://mp.weixin.qq.com/s/真实原文ID", "title": "待核验的官方发布"}
  ]
}
~~~

有效 publisher_id：bytedance-seed、tencent-hunyuan、deepseek、kimi。
程序只检验 URL 属于 mp.weixin.qq.com 正式文章路径；仍标记 publisher_unverified_share_link，不能仅凭域名确定账号身份、正文或发布时间。**不推荐填写示例 ID**，只有真的有原文链接再添加。

## 操作与检查

~~~bash
python -m unittest tests.test_cn_official_sources
python scripts/cn_official_sources.py
python scripts/ai_coordinate_auto.py --modules cn --report /tmp/cn-sources-report.json
python scripts/ai_coordinate_auto.py --offline-check
~~~

运行由 .github/workflows/ai-coordinate-auto.yml 每两小时调度，沿用其完整测试、构建和并发安全发布流程；GitHub 热榜、HF、原有 OpenAI/NVIDIA 源保持独立可继续执行。工作流/Pages 成功不是微信原帖核验成功，正文发布须另行编辑审核。代码不调用任何 ChatGPT 或付费大模型 API。

## 后续扩充

- 补充官方认证的公众号主体/原始 ID，有权限或合作时接入授权渠道。
- 公众号文章原文确认后做跨网站去重，按模型/产品/研究/医药/制造归类。
- 将审核队列做成网站内只读 UI，并在高价值候选上按需使用 AI 分析。
