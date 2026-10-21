"""Apply this round's editor-reviewed primary-source increment; no network or main writes."""
import json
from pathlib import Path
R=Path.cwd(); DAY='2026-10-21'; VERIFIED='2026-10-21T19:40:00+08:00'
O='https://openai.com/index/openai-to-acquire-orchestra-bio/'
P='https://openai.com/index/introducing-the-rosalind-academic-plan/'
T='https://mistral.ai/news/timestral/'
G='https://github.com/mistralai/timestral'
A='https://arxiv.org/abs/2610.28631'
def load(n):return json.loads((R/'data'/f'{n}.json').read_text())
def save(n,d):(R/'data'/f'{n}.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def add(rows,item):
 old=next((x for x in rows if x['id']==item['id']),None)
 if old is not None:
  if old!=item:raise ValueError('Conflicting editorial record: '+item['id'])
 else:rows.insert(0,item)
def source(id,title,publisher,url,published):
 return dict(id=id,title=title,publisher=publisher,url=url,published=published,checked=DAY,verified_at=VERIFIED,kind='官方一手来源')
def hot(id,category,title,published,summary,why,boundary,publisher,url,link,components,precise=None):
 return dict(id=id,category=category,title=title,published=published,published_at=precise,checked=DAY,verified_at=VERIFIED,first_seen_at=VERIFIED,heat=sum(components.values()),heat_components=components,heat_basis='本站编辑排序：影响0–35、可用性0–25、一手证据0–25、时效0–15；不是流量、用户热度或模型能力分。',trend='flat',summary=summary,why=why,boundary=boundary,source=publisher,source_kind='官方原文 / 本轮编辑核验',url=url,link=link,evidence_level='primary-source',access=[dict(label='阅读原始来源',note='保留原始发布日期；未做独立性能实测',url=url,kind='read')],related=[dict(source=publisher,title=title,url=url,date=published)])
h=load('hot')
new_hot=[
 hot('openai-orchestra-bio-20261020','industry','OpenAI 收购 Orchestra Bio：连接药物研发与项目协作','2026-10-20','OpenAI 宣布已收购 Orchestra Bio，并将其团队与技术结合到 Rosalind。重点是协助生物制药团队跟踪研究、依赖关系和项目进度。','生命科学 Agent 开始连接科学分析与研发流程；可关注证据追溯、权限和人工决策如何衔接。','收购与整合方向不等于新药已验证、已获批准或研发周期已被独立证实缩短；原文没有给出统一开放日期。','OpenAI',O,'#/pharma',dict(impact=35,availability=21,evidence=25,recency=15)),
 hot('rosalind-academic-plan-20261015','product','Rosalind 学术计划：美国高校实验室可申请赞助席位','2026-10-15','符合资格的美国高校实验室可申请最多30个 Business Standard 席位、最长12个月免费支持；GPT-Rosalind 仍需通过可信访问审核。','本次变化是学术访问渠道，不是新模型跑分；申请资格和实际可用权限比宣传标题更重要。','API 不包含在计划内；不是全球高校自动开放。已有学校 Enterprise 协议的团队应走学校流程；研究结果仍需实验验证。','OpenAI',P,'#/pharma',dict(impact=33,availability=24,evidence=25,recency=11)),
 hot('mistral-timestral-20261015','model','Timestral 开放：小型时序模型支持多变量概率预测','2026-10-15','Mistral 发布5M、28M、123M和209M四档时序模型，支持历史与已知未来协变量，并提供 CPU/GPU 推理代码。','可先用小样本检验设备传感器、产能与需求预测，减少从零训练的门槛；站内已补入可运行指南。','官方 Benchmark 排名不等于本站实测或真实工厂收益。预测不是因果诊断或自动控制；代码为 Apache-2.0，权重另有 Modified MIT 条款。','Mistral AI',T,'#/toolkit',dict(impact=34,availability=24,evidence=25,recency=11)),
 hot('aeon-world-model-20261020','research','AEON：把视频生成连接到可渲染的4D世界表示','2026-10-20','论文提出在视频潜空间生成，再通过域适配与4D解码器输出动态高斯表示和相机位姿，连接视频外观与三维一致性。','世界模型的输出开始从视频片段走向可换视角的持久场景；应继续跟踪复现与长期一致性。','研究结果及领先性能为作者报告，本站未复现；可渲染不代表物理定律、可控交互或工业数字孪生已经可靠。','AEON 作者 / arXiv',A,'#/progress?view=research',dict(impact=35,availability=16,evidence=25,recency=15),'2026-10-20T17:59:51Z')]
for x in reversed(new_hot):add(h['items'],x)
h['checked']=DAY;save('hot',h)
c=load('catalog')
add(c['sources'],source('timestral-release','Introducing Timestral','Mistral AI',T,'2026-10-15'))
add(c['sources'],source('timestral-repository','Timestral 官方推理代码与许可说明','Mistral AI',G,None))
add(c['items'],dict(id='timestral',name='Timestral',title='用小型模型做多变量时序预测',category='科学研究',mark='TS',accent='cyan',summary='输入历史传感器或需求序列，联合预测多个变量，并输出分位数表示不确定性。',scope='官方提供5M至209M权重与 PyTorch 推理；可在 CPU/GPU 上使用历史或已知未来协变量。',boundary='零样本预测不是故障原因诊断；需防止未来数据泄漏，按设备与时间外推验证。官方成绩不代表本站实测。',repo='mistralai/timestral',sources=['timestral-release','timestral-repository'],requirements='Python >=3.10、PyTorch >=2.4；首次下载权重；先读代码与权重各自许可。',test='以固定时点切分一段获授权的序列，与季节朴素基线比较误差和区间覆盖；禁止把未来目标值当协变量。',checks=['固定代码与权重版本，记录 CPU/GPU 和序列形状','按时间留出测试集，比较 MASE 等误差与区间覆盖','预测异常由人工复核，不直接触发生产设备动作'],command='git clone https://github.com/mistralai/timestral.git\ncd timestral\nuv sync --frozen',effort='本地 CPU / GPU',evidence='官方发布与代码文档',status='code',tested=False,reviewed=DAY,verified_at=VERIFIED))
add(c['events'],dict(id='timestral-release-20261015',task='timestral',date='2026-10-15',kind='release',title='Mistral 发布 Timestral 时序模型与推理代码',summary='四档参数规模支持多变量概率预测与协变量；本地 CPU/GPU 可用。',delta='可先在已有时序监测管线做零样本基线；上线前须验证数据泄漏、区间校准和漂移，不能把官方榜单当现场验收。',sources=['timestral-release','timestral-repository'],reviewed=DAY,verified_at=VERIFIED))
c['snapshot']=DAY;save('catalog',c)
k=load('toolkit')
add(k['items'],dict(id='timestral',publisher='Mistral AI',group='research',access='local',headline='先跑一个96步时序预测基线',input='获授权的历史序列，或固定随机种子的合成序列',output='预测中位数与21个分位数；示例输出96个未来步',requirements='Python >=3.10、PyTorch >=2.4、已安装 uv；首次下载模型权重，需要网络与本地存储。',limitation='只核验官方安装与 API 文档，本站未运行模型；代码 Apache-2.0，权重 Modified MIT，商业部署应分别审核。',cost='本地 CPU/GPU、权重下载与存储成本；不包含托管服务。',steps=[dict(title='克隆并安装锁定依赖',body='在独立目录操作；保存实际代码 commit 与模型 revision，便于重现。',command='git clone https://github.com/mistralai/timestral.git\ncd timestral\nuv sync --frozen'),dict(title='用合成数据检查接口',body='先验证输入维度和输出形状，再换成获授权的数据；不要把示例曲线当效果证据。',command='uv run python - <<\'PY\'\nimport numpy as np\nfrom timestral import TimestralForecaster\nf = TimestralForecaster.from_pretrained("mistralai/Timestral-5M")\nx = np.random.default_rng(42).standard_normal((1, 1, 2000)).cumsum(-1)\ny = f.forecast(x, prediction_length=96)\nprint(y.quantiles.shape, y.median.shape)\nPY'),dict(title='按时间留出验证',body='保持96步预测窗口，与季节朴素基线比较误差、区间覆盖和运行时间。仅提供预测时已知的协变量；不连接生产控制。')],troubleshooting='安装失败核对 Python/PyTorch；下载失败检查网络和缓存；形状不匹配核对(series, variates, time)。未来协变量必须覆盖历史与预测窗口。',sources=[dict(title='Timestral 官方 README：安装、Forecast、License',url=G,published_at=None,verified_at=DAY)],entry_url=G,evidence_level='primary-docs',runtime_tested=False,verified_at=VERIFIED))
save('toolkit',k)
i=load('industry')
for id,title,publisher,url,published in [('orchestra-acquisition','OpenAI acquires Orchestra Bio','OpenAI',O,'2026-10-20'),('rosalind-academic','Rosalind Academic Plan','OpenAI',P,'2026-10-15'),('timestral-industrial','Introducing Timestral','Mistral AI',T,'2026-10-15')]:
 s=source(id,title,publisher,url,published);s['date_label']=None;add(i['sources'],s)
for row in [
 dict(id='orchestra-program-coordination-20261020',sector='pharma',topics=['clinical','csr'],title='Orchestra Bio 加入 OpenAI：研发项目依赖纳入 Agent 工作流',summary='官方收购公告强调研究、项目进度与跨团队依赖的协调，并计划与 Rosalind 结合。',why='可以把研究证据、行动责任人与进度变更放在同一可追溯流程中评估。',boundary='尚不能据此确认临床合规、真实研发提速或统一开放时间；关键研究决策仍由专业人员负责。',sources=['orchestra-acquisition'],kind='update',access='官方公告；产品整合范围待跟踪',published='2026-10-20',steps=['阅读收购原文并区分已完成收购与未来产品计划','选取获授权的非敏感项目流程，定义人工审批节点','要求来源链、权限隔离与变更审计'],metrics=['依赖识别准确性','错误建议与人工复核负担','资料及行动的追溯完整性']),
 dict(id='rosalind-academic-access-20261015',sector='pharma',topics=['targets','molecules'],title='Rosalind 学术计划：先核对美国高校与可信访问资格',summary='符合资格的美国高校实验室可申请最多30个免费席位、最长12个月；GPT-Rosalind 使用仍需审核。',why='新增的是学术访问途径，适合先确认机构资格与研究数据治理，再规划试用。',boundary='不包含 API；并非全球高校自动开放。已有学校 Enterprise 协议的团队应按学校流程申请，研究输出不替代实验。',sources=['rosalind-academic'],kind='update',access='美国高校实验室申请 / 可信访问审核',published='2026-10-15',steps=['由 PI 或实验室负责人核对官方资格和学校既有协议','确认席位、使用限制、数据政策及 GPT-Rosalind 审核条件','用获授权的研究问题记录来源与实验验证计划'],metrics=['申请资格与访问状态','可追溯来源和验证记录','人工审核与真实实验结果']),
 dict(id='timestral-maintenance-20261015',sector='manufacturing',topics=['fab-process','equipment-maintenance'],title='Timestral：为传感器监测补一个概率预测基线',summary='官方模型支持联合预测多个变量，并利用排产等已知未来协变量；推理代码支持 CPU/GPU。',why='预测区间可用于评估漂移和维护风险，但应先在历史数据上建立可复现基线。',boundary='厂商公开评测不是工厂验收；不等同故障因果识别或闭环控制，本站未运行模型。',sources=['timestral-industrial'],kind='tool',access='公开代码与权重；许可分别审查',published='2026-10-15',steps=['按设备与时间切分数据，避免未来信息泄漏','比较季节朴素基线、误差及区间覆盖','影子运行并人工复核告警，不直接控制设备'],metrics=['MASE与区间覆盖','误报漏报与设备漂移','CPU/GPU时延及运维成本'])]:
 row.update(checked=DAY,verified_at=VERIFIED,first_seen_at=VERIFIED,evidence_level='primary-source',featured=True,tested=False);add(i['articles'],row)
i['checked']=DAY;save('industry',i)
r=load('research-radar')
add(r['items'],dict(id='aeon-video-4d-world-model',lane='paradigm',title='AEON：视频潜空间连接显式4D世界',maker='AEON 作者团队',date='2026-10-20',published_at='2026-10-20T17:59:51Z',verified_at=VERIFIED,tags=['World Model','4D Gaussian Splatting','Video Generation'],fact='论文通过域适配把生成视频潜变量接到4D重建解码器，输出动态高斯表示和相机位姿。',insight='显式可渲染表示提供换视角与持久场景的新路径，可与仅输出视频的路线分开观察。',boundary='作者报告不等于独立复现；视觉与几何一致性不能证明物理规律、可控交互或工业可靠性。',next_watch='跟踪代码、权重、运行条件，以及长期一致性、交互控制和跨场景泛化的独立复现。',sources=[dict(label='AEON 论文 v1 / arXiv',url=A,kind='作者论文原文',strength='primary'),dict(label='AEON 作者项目页',url='https://weiqi-zhang.github.io/AEON/',kind='作者项目说明',strength='primary')]))
r['checked']=DAY;save('research-radar',r)
q=load('frontier-candidates')
for row in q['items']:
 if row['arxiv_id']=='2610.28631':row.update(status='reviewed',reviewed_at=VERIFIED,editorial_target='#/progress?view=research',review_note='本轮核验论文与项目原文后进入研究雷达；不是能力排行榜或本站实测。')
save('frontier-candidates',q)
p=R/'tests/test_topics.py';s=p.read_text();old=" def test_counts(self):self.assertEqual((len(self.d['sectors']),len(self.d['topics']),len(self.d['articles']),len(self.d['sources'])),(2,10,15,20))"
new=""" def test_counts(self):
  self.assertEqual((len(self.d['sectors']),len(self.d['topics'])),(2,10))
  for key in ('articles','sources'):
   ids=[x['id'] for x in self.d[key]]
   self.assertTrue(ids)
   self.assertEqual(len(ids),len(set(ids)))
  feed=ET.fromstring(topics.topic_rss(self.d,self.s,'all'))
  self.assertEqual({x.findtext('guid') for x in feed.findall('./channel/item')},{'frontierlog:topic:'+x['id'] for x in self.d['articles']})"""
if old in s:s=s.replace(old,new)
elif new not in s:raise ValueError('Topic test changed; review before applying')
p.write_text(s)
p=R/'tests/test_build.py';s=p.read_text();s=s.replace("len(self.c['events'])+15","len(self.c['events'])+len(json.loads((ROOT/'data/industry.json').read_text())['articles'])");p.write_text(s)
p=R/'src/feed-cockpit.js';s=p.read_text()
fn="""function fcHeatBand(score){
 const n=Number(score);
 return n>=98?{key:'extreme',label:'爆热'}:n>=95?{key:'high',label:'高热'}:n>=90?{key:'rising',label:'升温'}:{key:'watch',label:'关注'};
}
"""
if 'function fcHeatBand(' not in s:s=s.replace('function fcHotPanel(){',fn+'function fcHotPanel(){')
a="'<span class=\"fc-hot-score\"><b>'+esc(String(x.heat))+'</b>'+hTrend(x)+'</span>'"
b="'<span class=\"fc-hot-score fc-heat-'+fcHeatBand(x.heat).key+'\" aria-label=\"编辑热度 '+esc(String(x.heat))+'，'+fcHeatBand(x.heat).label+'\"><b>'+esc(String(x.heat))+'</b><small>'+fcHeatBand(x.heat).label+'</small>'+hTrend(x)+'</span>'"
if a in s:s=s.replace(a,b)
elif b not in s:raise ValueError('Homepage renderer changed')
p.write_text(s)
p=R/'src/feed-cockpit.css';s=p.read_text()
css="""\n/* Editorial heat: numeric strength and text tiers, never color alone. */
.fc-hot-score{display:grid;grid-template-columns:1fr auto;gap:1px 3px;text-align:center;min-width:46px;padding:5px 4px;border-radius:7px}
.fc-hot-score b{font-variant-numeric:tabular-nums;font-size:1rem}
.fc-hot-score small{grid-column:1/-1;grid-row:2;font-size:.65rem;font-weight:700;line-height:1.4}
.fc-hot-score .h-trend{grid-column:2;grid-row:1}
.fc-hot-score.fc-heat-extreme{background:var(--ink);color:var(--lime);border:1px solid var(--ink)}
.fc-hot-score.fc-heat-extreme b{font-size:1.14rem}
.fc-hot-score.fc-heat-high{background:var(--accent-bg);color:var(--accent);border:1px solid var(--accent)}
.fc-hot-score.fc-heat-rising{color:var(--text);border:1px solid var(--line)}
.fc-hot-score.fc-heat-watch{color:var(--muted);border:1px dashed var(--line)}
"""
if '/* Editorial heat:' not in s:s+=css
p.write_text(s)
p=R/'tests/test_topics.py';s=p.read_text()
s=s.replace("self.d['articles'][0]['topics']=['fab-yield']", "self.d['articles'][0]['topics']=['fab-yield' if self.d['articles'][0]['sector']=='pharma' else 'targets']")
s=s.replace("  self.assertEqual(len(rss.findall('./channel/item')),2)\n  self.assertEqual(len(rss.findall('./channel/item/pubDate')),0)","  rows={x.findtext('guid'):x for x in rss.findall('./channel/item')}\n  expected=[x for x in self.d['articles'] if 'csr' in x['topics']]\n  self.assertEqual(set(rows),{'frontierlog:topic:'+x['id'] for x in expected})\n  for x in expected:\n   self.assertEqual(rows['frontierlog:topic:'+x['id']].find('pubDate') is None,x['published'] is None)")
p.write_text(s)
(R/'tests/test_editorial_ui_contracts.py').write_text('''"""Contract regressions for editorial growth and visible heat hierarchy."""
import copy, json, subprocess, sys, unittest
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from topics import topic_rss, validate_topics

class EditorialContracts(unittest.TestCase):
 def test_topic_rss_grows_and_shrinks_without_losing_identity(self):
  base=json.loads((ROOT/'data/industry.json').read_text())
  source=copy.deepcopy(base['articles'][0])
  for count in (1,10,18,25):
   with self.subTest(count=count):
    d=copy.deepcopy(base)
    d['articles']=[dict(copy.deepcopy(source),id='fixture-'+str(i)) for i in range(count)]
    validate_topics(d,{'items':[]})
    feed=ET.fromstring(topic_rss(d,{'base_url':'https://example.org/'}))
    rows=feed.findall('./channel/item')
    self.assertEqual(len(rows),count)
    self.assertEqual({r.findtext('guid') for r in rows},{'frontierlog:topic:fixture-'+str(i) for i in range(count)})
 def test_unknown_dates_remain_unknown_in_mixed_feed(self):
  d=json.loads((ROOT/'data/industry.json').read_text())
  a=copy.deepcopy(d['articles'][0]);a['id']='unknown-date';a['published']=None
  b=dict(copy.deepcopy(a),id='known-date',published='2026-10-15');d['articles']=[a,b]
  rows=ET.fromstring(topic_rss(d,{'base_url':'https://example.org/'})).findall('./channel/item')
  self.assertIsNone(rows[0].find('pubDate'));self.assertIsNotNone(rows[1].find('pubDate'))
 def test_homepage_heat_band_thresholds(self):
  text=(ROOT/'src/feed-cockpit.js').read_text()
  fn=text[text.index('function fcHeatBand('):text.index('function fcHotPanel(')]
  code=fn+"console.log(JSON.stringify([99,98,97,96,95,94,90,89].map(fcHeatBand)));"
  rows=json.loads(subprocess.check_output(['node','-e',code],text=True))
  self.assertEqual([r['key'] for r in rows],['extreme','extreme','high','high','high','rising','rising','watch'])
  self.assertEqual([r['label'] for r in rows],['爆热','爆热','高热','高热','高热','升温','升温','关注'])
 def test_homepage_heat_has_text_and_accessible_numeric_label(self):
  text=(ROOT/'src/feed-cockpit.js').read_text()
  self.assertIn('aria-label="编辑热度 ',text)
  self.assertIn("fcHeatBand(x.heat).label+'</small>'",text)
  css=(ROOT/'src/feed-cockpit.css').read_text()
  for band in ('extreme','high','rising','watch'):self.assertIn('.fc-heat-'+band,css)
''')
p=R/'tests/toolkit-browser.test.cjs';s=p.read_text().replace('data.items[0]',"data.items.find(x=>x.id==='docling')");p.write_text(s)
p=R/'tests/v10-next-coordinate.test.cjs';s=p.read_text()
if 'class FixedDate' not in s:
 s=s.replace('const ctx = {',"let clock='2026-10-08T12:00:00Z';\nclass FixedDate extends Date { constructor(...args){super(...(args.length?args:[clock]))} static now(){return Date.parse(clock)} }\nconst ctx = {")
 s=s.replace('  Intl,Date,','  Intl,Date:FixedDate,')
 s=s.replace("assert.equal(v10NextOfficialEvent().id,'official-soon');", "assert.equal(v10NextOfficialEvent().id,'official-soon');\nclock='2026-10-21T12:00:00Z';\nassert.equal(v10NextOfficialEvent().id,'official-later');")
p.write_text(s)
print('Reviewed content applied; no external source or production update is performed by this script.')
