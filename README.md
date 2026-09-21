# AI 到哪了

以任务为索引，追踪 AI 的真实进展。灰白底、墨绿与青柠色版本 v0.2.1。

## 本包用途

这是可直接上传到 GitHub Pages 的静态发布包，已经包含构建后的网页、RSS 和 JSON 数据。不需要安装 Python、Node 或 GitHub CLI，不需要运行 publish.py。

目标仓库：`momo-hub-learn/ai-progress`。
目标站点：`https://momo-hub-learn.github.io/ai-progress/`。
该地址是部署目标；只有 GitHub 部署成功后才能访问。

## 用浏览器发布

1. 在 GitHub 创建公开仓库 `ai-progress`，Owner 选择 `momo-hub-learn`，开启 Add README。
2. 在仓库 Code 页，选择 Add file → Upload files。
3. 打开本包解压后的文件夹，将里面的文件与 `api` 文件夹拖到上传页；不要上传 ZIP，也不要在仓库中多套一层 `ai-progress-upload` 文件夹。保留 `.nojekyll` 文件（系统显示它时一并上传），不要将任何文件重命名。
4. 选择直接提交到 `main`，填写提交说明如 `Publish AI Progress website`，提交更改。
5. 打开 Settings → Pages，将 Source 设为 Deploy from a branch，Branch 选 main，Folder 选 /(root)，点击 Save。
6. 在 Actions 检查 Pages 构建与部署记录；成功后从 Settings → Pages → Visit site 打开网站。首次部署不要把等待期间的 404 当成永久失败。

仓库根目录应直接出现：

```text
index.html
404.html
api/
feed.xml
robots.txt
sitemap.xml
README.md
LICENSE
.nojekyll
```

`index.html` 必须位于仓库根目录，不能是 `dist/index.html`、`ai-progress-upload/index.html` 或 `index.html.txt`。

## 范围与限制

本包保留现有前端交互、浅色默认主题、公开数据和 RSS 快照。关注与验收清单保存在各访问者自己的浏览器，不是跨设备账号服务。RSS 地址已按目标网站配置。

本次手动发布不包含采集或定时更新工作流，不会自动同步最新新闻或模型能力。内容仍是既有资料快照；站点上线不代表第三方工具已经被实测。GitHub 自动部署和内容自动更新是两件不同的事。

后续更新时，用相同目录结构上传新版本并提交到 main。源码和数据采集脚本另见之前的完整源码包，本包只负责网站首次公开访问。

本包没有密码、Cookie、GitHub Token 或模型 API Key。不要将私人材料和访问密钥上传公开仓库。

## 官方说明

- https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
