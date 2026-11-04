# AI坐标 · 零模型调用定时采集

目标：让高频、确定性工作由 GitHub Actions + Python 标准库完成，不必让 ChatGPT 每两小时完整执行大规模研究与部署任务。

## 覆盖与边界

- 新工作流每两小时（UTC 偶数小时第 07 分）运行；定时触发并非精确实时保证。
- scripts/ai_coordinate_auto.py 调度三个相互独立的来源：Hugging Face Models Trending 网页/API、GitHub 上游 Releases 和 OpenAI/NVIDIA 官方 RSS/Atom 公告候选。GitHub Trending、主题、活动、研究已经有单独的调度，不会重复调用。
- HF 的网页顺序与 API trendingScore、Likes、Downloads 分开保存；Release 元数据仍是未审核资料。
- 官方公告只进 data/official-news-inbox.json 的 unreviewed 队列；程序绝不把标题升级为热点、疗效、良率、Benchmark 或深读正文，必须经人工审核。
- AA API 采集原先未配置，程序不私自启用；Tibo X 没有可读原帖时保留 pending。
- 这里不调用 ChatGPT 或 LLM API。GitHub Actions 的运行资源、限额由 GitHub 单独管理。

## 时间与失败

published_at 只接受源 RSS/Atom 带时区的精确时间；缺失填 null，真实未来时间拒收。first_seen_at 只在首次发现写入；last_ingested_at 仅在队列新增时更新。各来源分别保存 last_attempt_at / last_success_at / last_error。失败保留旧成功时间。HF/Release 原有独立时间记录不被覆盖。

源资料发现 ≠ 编辑核验 ≠ 正文入库 ≠ 主分支提交 ≠ Pages 部署。机器候选不会自动转为已证实新闻。

## 本地命令

~~~bash
python -m unittest tests.test_ai_coordinate_auto tests.test_huggingface_trending_sync tests.test_collect
python scripts/ai_coordinate_auto.py --offline-check
python scripts/ai_coordinate_auto.py --modules official,hf --report /tmp/ai-coordinate-report.json
python scripts/ai_coordinate_auto.py --report /tmp/ai-coordinate-report.json
~~~

offline-check 不联网、不改正文。返回 0 表示至少一个来源成功；必须查看回执中每一来源的 success/partial/failed。返回 2 表示所有选中来源失败。自动运行的回执作为 Actions artifact 保存 14 天。

提交前重新从最新 main 采集、运行回归、构建并检查输出；并发拒绝时重新基于最新 main 工作，不强推。工作流成功不等于 Pages 真实上线。

## 迁移步骤

1. 合并后查看 Actions 首次运行与实际两小时运行的逐源回执，再核对线上 API 和 Pages。
2. 人工新闻编辑、全站 UX 检查继续按需或低频做，不能把未经核验的采集资料直接公开为事实。
3. 原 ChatGPT 自动任务是独立系统。只有新工作流经验证且用户同意后才暂停旧任务。本次代码不修改该任务、调度或 WELCOME 2027。
