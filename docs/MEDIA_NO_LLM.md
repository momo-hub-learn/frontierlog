# AI坐标｜零模型调用的媒体和创作者追踪

新增一个独立的二级信源队列：数据文件 data/media-sources.json、候选 data/media-inbox.json、手动微信原文输入 data/media-original-links.json。代码 scripts/media_sources.py，在现有 scripts/ai_coordinate_auto.py 和 .github/workflows/ai-coordinate-auto.yml 的两小时调度内运行。纯 Python 标准库，不使用 ChatGPT、OpenAI API、其他大模型 API 或付费网页转写服务。

## 已接入源

| 来源 | 获取方法 | 能代表什么 | 不能代表什么 |
| --- | --- | --- | --- |
| 量子位 | 自有 RSS https://www.qbitai.com/feed | 量子位自己发布的媒体报道、标题、文章链接和 RSS 时间 | 所报道厂商公告已获一手核验；模型或 benchmark 实测 |
| 数字生命卡兹克 | 本人项目 https://aihot.news/changelog 的标题变化指纹 | 本人制作的 AIHOT 项目更新/页面变化线索 | 其个人微信公众号当日原创文章、公众号发文时间、第三方热点事实 |
| 数字生命卡兹克公众号 | 仅接收人工给出的 mp.weixin.qq.com/s/... 原文链接 | 有这样一个候选原文 URL | 发文账号身份、全文、发布日期已经核验 |

**不把 AIHOT 的聚合新闻 RSS/API 当本站的新闻采集原料。** AIHOT 公示的公开使用条款限制搭建公开镜像或商业化复用；即便有公开 RSS，也不能把它当作卡兹克本人逐篇创作的文章。

量子位是媒体/二级发现源，作者项目更新仅在自己的项目范围内是一手信息。媒体新闻如影响模型榜、热点或医药制造行业结论，需要回到原始公告、论文、GitHub Release 或官方评测再核验。

## 内容语义和节流

- media inbox 中每条有效文章拥有稳定 SHA256 ID、媒体网站 URL、来源 RSS、原始带时区 published_at（缺失写 null）、first_seen_at、只依赖标题的可解释关键词标签。
- 去重靠 source_id + 规范化链接；重复抓取不会冒充新内容。1/10/12/17 条输入和新增/删除/合并已做合约回归。
- 仅从确切允许的 HTTPS 域名抓取。网页响应限制 2MB、超时 25 秒；重定向不得越过信源域名。不抓微信历史列表，不使用逆向 API、访问令牌或第三方全文镜像，不转存媒体正文。
- 微信文章链接仅从 data/media-original-links.json 接收。例如：{"version":1,"items":[{"source_id":"khazix-wechat","url":"https://mp.weixin.qq.com/s/实际原文ID","title":"你确认的文章标题"}]}。不要提交伪造的示例链接。
- 人工已审核的候选及其备注不可被自动采集覆盖。
- 来源状态按源记录 last_attempt_at / last_success_at / last_error；无法抓取是 failed 而不是未变。作者项目日志只保存最近标题的哈希，实际变动记录 changed_unreviewed_at，不自动生成新闻。
- 如果来源只成功更新检查时间，不能宣称新增新闻；发布回执和队列差异分开汇报。
- 收集失败不阻止其他独立来源成功更新；若所有来源失败，该模块非零退出码，工作流据此保留失败/局部状态。
- GitHub Actions 的运行分钟/额度与 ChatGPT Pro 模型使用限制无关。此程序的模型调用次数是 0。

## 本地和 Actions

~~~bash
python -m unittest tests.test_media_sources
python scripts/media_sources.py --offline-check
python scripts/media_sources.py
python scripts/ai_coordinate_auto.py --modules media --report /tmp/media-sync.json
~~~

自动运行见 Actions：AI coordinate source autopilot (no LLM)。先离线测试，再在最新 main 上分别抓取，构建并运行全套 CI 对应测试，通过才尝试非强推提交。产物需核对 data/media-inbox.json 和对应发布 SHA；机器线索不会进入 hot.json、industry.json、模型榜或深读正文。

## 扩展其他媒体

在 data/media-sources.json 的 sources 添加声明的 HTTPS RSS/Atom：id、publisher_id、publisher、publisher_kind=media、source_role=media_original_publication、mode=rss、url、hosts、article_hosts、max_items、enabled。不要用第三方镜像补造原始榜位、发布时间或媒体发布身份。

后续如果取得卡兹克本人授权/确认的可机读原文 Feed，可作为另一个独立 source 并保留授权证明；当前没有这种授权，不能声称公众号已实现自动全文采集。
