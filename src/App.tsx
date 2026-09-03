import { FormEvent, useState } from 'react'
import './styles.css'

type Page = 'overview' | 'tree' | 'assistant' | 'archive' | 'settings'
type Conversation = 'welcome' | 'relationship' | 'draft' | 'saved'

const navigation: Array<{ id: Page; label: string; icon: string }> = [
  { id: 'overview', label: '概览', icon: '⌂' },
  { id: 'tree', label: '族谱', icon: '⌘' },
  { id: 'assistant', label: '智能体', icon: '✦' },
  { id: 'archive', label: '资料档案', icon: '▤' },
  { id: 'settings', label: '设置', icon: '⚙' },
]

const people = [
  { name: '张景和', years: '1921—1998', role: '曾祖父', tone: 'olive' },
  { name: '林月琴', years: '1926—2007', role: '曾祖母', tone: 'clay' },
  { name: '张启山', years: '1947—', role: '祖父', tone: 'ink' },
  { name: '陈素贞', years: '1950—', role: '祖母', tone: 'sand' },
  { name: '张明远', years: '1975—', role: '父亲', tone: 'blue' },
]

export function App() {
  const [page, setPage] = useState<Page>('overview')
  const [conversation, setConversation] = useState<Conversation>('welcome')
  const [memberCount, setMemberCount] = useState(24)
  const [query, setQuery] = useState('')

  const openRelationship = () => {
    setPage('assistant')
    setConversation('relationship')
  }

  const openDraft = () => {
    setPage('assistant')
    setConversation('draft')
  }

  const confirmDraft = () => {
    setMemberCount(25)
    setConversation('saved')
  }

  const submitQuery = (event: FormEvent) => {
    event.preventDefault()
    if (!query.trim()) return
    if (query.includes('新增') || query.includes('录入')) {
      setConversation('draft')
    } else {
      setConversation('relationship')
    }
    setQuery('')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="seal" aria-hidden="true">谱</div>
          <div>
            <strong>归源</strong>
            <span>家族记忆助手</span>
          </div>
        </div>

        <nav aria-label="主导航" className="nav-list">
          {navigation.map((item) => (
            <button
              type="button"
              key={item.id}
              className={page === item.id ? 'nav-item active' : 'nav-item'}
              onClick={() => setPage(item.id)}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="admin-avatar">何</div>
          <div>
            <strong>族谱管理员</strong>
            <span>仅本账号可编辑</span>
          </div>
          <span aria-hidden="true">···</span>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="mobile-brand"><span className="mini-seal">谱</span>归源</div>
          <div className="topbar-tree">
            <span className="tree-mark" aria-hidden="true">枝</span>
            <div><strong>张氏家族谱</strong><span>始迁祖张维清 · 建于 2026</span></div>
          </div>
          <div className="top-actions">
            <span className="sync"><i /> 数据已同步</span>
            <button type="button" className="icon-button" aria-label="通知">♧<b>3</b></button>
            <button type="button" className="primary-small" onClick={openDraft}>＋ 录入资料</button>
          </div>
        </header>

        {page === 'overview' && <Overview onAsk={openRelationship} onAdd={openDraft} />}
        {page === 'assistant' && (
          <Assistant
            conversation={conversation}
            memberCount={memberCount}
            query={query}
            onQueryChange={setQuery}
            onSubmit={submitQuery}
            onRelationship={openRelationship}
            onDraft={openDraft}
            onConfirm={confirmDraft}
            onCancel={() => setConversation('welcome')}
          />
        )}
        {page === 'tree' && <FamilyTree />}
        {page === 'archive' && <Archive />}
        {page === 'settings' && <Settings />}
      </section>

      <nav className="mobile-nav" aria-label="移动端导航">
        {navigation.map((item) => (
          <button type="button" key={item.id} className={page === item.id ? 'active' : ''} onClick={() => setPage(item.id)}>
            <span aria-hidden="true">{item.icon}</span>{item.label}
          </button>
        ))}
      </nav>
    </div>
  )
}

function Overview({ onAsk, onAdd }: { onAsk: () => void; onAdd: () => void }) {
  return (
    <main className="page overview-page">
      <div className="page-heading">
        <div><p className="eyebrow">二〇二六 · 仲秋</p><h1>家族概览</h1><p>记录每一个名字，也保存名字背后的故事。</p></div>
        <button type="button" className="outline-button">导出族谱 <span>↗</span></button>
      </div>

      <section className="stats-grid" aria-label="族谱统计">
        <article><span className="stat-icon sage">人</span><div><b>24</b><span>收录成员</span></div><em>＋3 本月</em></article>
        <article><span className="stat-icon ochre">代</span><div><b>5</b><span>延续世代</span></div><em>始于 1921</em></article>
        <article><span className="stat-icon blue">档</span><div><b>16</b><span>资料档案</span></div><em>照片与文献</em></article>
        <article><span className="stat-icon coral">待</span><div><b>4</b><span>待核实信息</span></div><em className="attention">需要关注</em></article>
      </section>

      <section className="content-grid">
        <article className="panel family-preview">
          <div className="panel-title"><div><span>血脉一览</span><h2>家族脉络</h2></div><button type="button">查看完整族谱 →</button></div>
          <div className="generation-label"><span>第一代</span><span>第二代</span><span>第三代</span></div>
          <div className="mini-tree">
            <div className="generation first">
              {people.slice(0, 2).map((person) => <PersonNode key={person.name} {...person} />)}
            </div>
            <div className="tree-line vertical" />
            <div className="generation second">
              {people.slice(2, 4).map((person) => <PersonNode key={person.name} {...person} />)}
            </div>
            <div className="tree-line vertical short" />
            <div className="generation third"><PersonNode {...people[4]} /></div>
          </div>
        </article>

        <article className="panel activity-panel">
          <div className="panel-title"><div><span>动态</span><h2>最近更新</h2></div><button type="button">全部记录</button></div>
          <ol className="activity-list">
            <li><i className="dot sage" /><div><strong>补充了陈素贞的出生地点</strong><p>地点更新为“广东省梅州市梅县区”</p><span>今天 09:42 · 管理员</span></div></li>
            <li><i className="dot ochre" /><div><strong>上传一张家庭合影</strong><p>《一九八二年春节合影》</p><span>昨天 20:16 · 管理员</span></div></li>
            <li><i className="dot blue" /><div><strong>新增成员张知夏</strong><p>关联为张明远之女</p><span>8 月 28 日 · 管理员</span></div></li>
          </ol>
        </article>
      </section>

      <section className="assistant-banner">
        <div className="spark">✦</div>
        <div><span>归源智能体</span><h2>想从家族故事里发现什么？</h2><p>我可以帮你梳理亲属关系、查找资料，也能协助录入新的家族记忆。</p></div>
        <div className="banner-actions"><button type="button" onClick={onAsk}>问一个问题</button><button type="button" onClick={onAdd}>录入新成员</button></div>
      </section>
    </main>
  )
}

function PersonNode({ name, years, role, tone }: { name: string; years: string; role: string; tone: string }) {
  return <article className="person-node"><div className={`portrait ${tone}`}>{name.slice(-1)}</div><div><strong>{name}</strong><span>{role} · {years}</span></div></article>
}

type AssistantProps = {
  conversation: Conversation
  memberCount: number
  query: string
  onQueryChange: (value: string) => void
  onSubmit: (event: FormEvent) => void
  onRelationship: () => void
  onDraft: () => void
  onConfirm: () => void
  onCancel: () => void
}

function Assistant(props: AssistantProps) {
  const showRelationship = props.conversation === 'relationship'
  const showDraft = props.conversation === 'draft'
  const showSaved = props.conversation === 'saved'

  return (
    <main className="assistant-layout">
      <section className="chat-column">
        <header className="assistant-header">
          <div className="agent-avatar">✦</div>
          <div><h1>归源智能体</h1><p><i /> 正在守护张氏家族的记忆</p></div>
          <span className="member-pill">共 {props.memberCount} 位成员</span>
        </header>

        <div className="messages" aria-live="polite">
          <div className="date-divider"><span>今天</span></div>
          <div className="message-row agent">
            <div className="message-avatar">归</div>
            <div className="bubble"><strong>你好，我是归源。</strong><p>你可以问我家族成员之间的关系，或者让我帮你整理一段新的家族资料。所有变更都会先请你确认。</p></div>
          </div>

          {showRelationship && <RelationshipConversation />}
          {(showDraft || showSaved) && <DraftConversation saved={showSaved} />}
        </div>

        <div className="suggestion-row">
          <button type="button" onClick={props.onRelationship}>张明远的外祖父是谁？</button>
          <button type="button" onClick={props.onDraft}>模拟录入成员</button>
          <button type="button" onClick={props.onRelationship}>找出待核实的出生信息</button>
        </div>

        <form className="composer" onSubmit={props.onSubmit}>
          <button type="button" aria-label="添加附件">＋</button>
          <input value={props.query} onChange={(event) => props.onQueryChange(event.target.value)} placeholder="询问家族关系，或描述要录入的资料…" aria-label="向归源提问" />
          <button type="submit" className="send-button" aria-label="发送">↑</button>
          <small>演示数据 · 智能体可能出错，请核对重要信息</small>
        </form>
      </section>

      <aside className={`context-panel ${showDraft || showSaved ? 'active-context' : ''}`}>
        {showDraft ? <ChangePreview onConfirm={props.onConfirm} onCancel={props.onCancel} /> : showSaved ? <SavedPanel /> : <EvidencePanel active={showRelationship} />}
      </aside>
    </main>
  )
}

function RelationshipConversation() {
  return (
    <>
      <div className="message-row user"><div className="bubble">张明远的外祖父是谁？</div><div className="user-avatar">何</div></div>
      <div className="message-row agent">
        <div className="message-avatar">归</div>
        <div className="bubble answer">
          <span className="answer-label">已查阅 3 条家族记录</span>
          <p className="answer-main">张明远的外祖父是陈守义。</p>
          <p>陈守义（1918—1989）是陈素贞的父亲；陈素贞是张明远的母亲，因此两人为外祖孙关系。</p>
          <div className="inline-path"><span>张明远</span><b>母亲</b><span>陈素贞</span><b>父亲</b><span>陈守义</span></div>
          <button type="button" className="text-action">在族谱中定位 ↗</button>
        </div>
      </div>
    </>
  )
}

function DraftConversation({ saved }: { saved: boolean }) {
  return (
    <>
      <div className="message-row user"><div className="bubble">新增张明远的儿子张予安，2012 年 5 月 18 日生于深圳。</div><div className="user-avatar">何</div></div>
      <div className="message-row agent">
        <div className="message-avatar">归</div>
        <div className="bubble">
          {saved ? <><strong className="saved-title">已模拟写入族谱</strong><p>张予安已作为张明远之子加入当前演示数据。</p></> : <><strong>我已整理成一条人物记录。</strong><p>右侧是将要发生的变更。请检查姓名、日期、地点和亲属关系，确认后才会写入。</p></>}
        </div>
      </div>
    </>
  )
}

function EvidencePanel({ active }: { active: boolean }) {
  return (
    <div className="context-content">
      <p className="context-kicker">{active ? '本次回答依据' : '智能体工作台'}</p>
      <h2>{active ? '关系路径' : '可信回答，有据可查'}</h2>
      {active ? (
        <>
          <div className="path-stack">
            <PersonLine name="张明远" meta="1975— · 广东梅州" initial="远" />
            <div className="relation-line"><i /><span>母亲</span></div>
            <PersonLine name="陈素贞" meta="1950— · 广东梅州" initial="贞" />
            <div className="relation-line"><i /><span>父亲</span></div>
            <PersonLine name="陈守义" meta="1918—1989 · 广东梅州" initial="义" />
          </div>
          <div className="source-card"><span>主要来源 · 可信度高</span><strong>《陈氏家谱》民国三十六年续修本</strong><p>卷三 · 世系表 · 第 18 页</p><button type="button">查看原始档案 ↗</button></div>
          <div className="source-card secondary"><span>辅助来源</span><strong>陈素贞口述记录</strong><p>录音整理 · 2004 年 6 月</p></div>
        </>
      ) : (
        <div className="empty-context"><div>引</div><p>提问后，这里会展示人物关系、引用资料和可信度。</p></div>
      )}
    </div>
  )
}

function PersonLine({ name, meta, initial }: { name: string; meta: string; initial: string }) {
  return <div className="person-line"><div>{initial}</div><span><strong>{name}</strong><small>{meta}</small></span></div>
}

function ChangePreview({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="context-content preview-content">
      <p className="context-kicker">写入前核对</p><h2>变更预览</h2>
      <div className="change-status"><span>＋</span><div><strong>新增 1 位成员</strong><p>尚未写入族谱</p></div></div>
      <dl className="field-list">
        <div><dt>姓名</dt><dd>张予安</dd></div><div><dt>性别</dt><dd>男</dd></div>
        <div><dt>出生日期</dt><dd>2012 年 5 月 18 日</dd></div><div><dt>出生地点</dt><dd>广东省深圳市</dd></div>
      </dl>
      <div className="relation-preview"><span>将建立亲属关系</span><div><b>张明远</b><i>父子</i><b>张予安</b></div></div>
      <div className="safety-note"><strong>确认机制</strong><p>当前只是模拟操作。正式版中，未经你的确认，智能体不会修改任何族谱数据。</p></div>
      <button type="button" className="confirm-button" onClick={onConfirm}>确认写入</button>
      <button type="button" className="cancel-button" onClick={onCancel}>返回修改</button>
    </div>
  )
}

function SavedPanel() {
  return <div className="context-content saved-panel"><div className="success-mark">✓</div><p className="context-kicker">操作完成</p><h2>已模拟保存</h2><p>真实版本会在这里提供变更编号、操作者和撤销入口。</p><button type="button" className="confirm-button">查看人物档案</button></div>
}

function FamilyTree() {
  return <main className="page simple-page"><div className="page-heading"><div><p className="eyebrow">五代同堂</p><h1>张氏家族谱</h1><p>以张明远为中心浏览直系亲属。</p></div><button className="primary-small">＋ 添加成员</button></div><div className="panel large-placeholder"><div className="tree-canvas"><PersonNode {...people[0]} /><span className="branch">└────┬────┘</span><div className="tree-row"><PersonNode {...people[2]} /><PersonNode {...people[3]} /></div><span className="branch">└────┬────┘</span><PersonNode {...people[4]} /></div><p>拖动空白区域浏览 · 滚轮缩放</p></div></main>
}

function Archive() {
  return <main className="page simple-page"><div className="page-heading"><div><p className="eyebrow">家族记忆</p><h1>资料档案</h1><p>照片、家谱原件与口述记录统一归档。</p></div><button className="primary-small">＋ 上传资料</button></div><div className="archive-grid">{['《陈氏家谱》续修本','一九八二年春节合影','陈素贞口述记录','张维清迁居文书'].map((title, index) => <article className="archive-card" key={title}><div className={`document-cover cover-${index + 1}`}>卷<br />{index + 1}</div><span>{index % 2 ? '照片 / 口述' : '家谱 / 文献'}</span><h2>{title}</h2><p>已关联 {index + 2} 位家族成员</p></article>)}</div></main>
}

function Settings() {
  return <main className="page simple-page"><div className="page-heading"><div><p className="eyebrow">系统配置</p><h1>设置</h1><p>Demo 仅展示未来的关键配置入口。</p></div></div><div className="panel settings-panel"><h2>智能体安全</h2><div className="setting-row"><div><strong>写入前人工确认</strong><p>任何新增或修改都必须由管理员确认。</p></div><span className="toggle on"><i /></span></div><div className="setting-row"><div><strong>回答显示资料来源</strong><p>在回答旁展示使用的族谱记录和档案。</p></div><span className="toggle on"><i /></span></div><div className="setting-row"><div><strong>托管模型服务</strong><p>OpenAI 兼容 API · 尚未连接</p></div><button className="outline-button">配置</button></div></div></main>
}
