import { FormEvent, ReactNode, useCallback, useEffect, useState } from 'react'
import { api, ApiError } from './api'
import { LoginPage } from './components/LoginPage'
import { PersonEditor } from './components/PersonEditor'
import { SourceUploader } from './components/SourceUploader'
import type { AgentAnswer, AgentResult, AuditLog, DraftPreview, Person, Relationship, Source } from './types'
import './styles.css'

type Page = 'overview' | 'tree' | 'assistant' | 'archive' | 'settings'
const navigation: Array<{ id: Page; label: string; icon: string }> = [
  { id: 'overview', label: '概览', icon: '⌂' }, { id: 'tree', label: '族谱', icon: '⌘' },
  { id: 'assistant', label: '智能体', icon: '✦' }, { id: 'archive', label: '资料档案', icon: '▤' },
  { id: 'settings', label: '设置', icon: '⚙' },
]

export function App() {
  const [auth, setAuth] = useState<'loading' | 'anonymous' | 'authenticated'>('loading')
  const [username, setUsername] = useState('admin')
  const [page, setPage] = useState<Page>('overview')
  const [people, setPeople] = useState<Person[]>([])
  const [relationships, setRelationships] = useState<Relationship[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [audits, setAudits] = useState<AuditLog[]>([])
  const [editor, setEditor] = useState<Person | 'new' | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    const [nextPeople, nextRelationships, nextSources, nextAudits] = await Promise.all([api.people(), api.relationships(), api.sources(), api.auditLogs()])
    setPeople(nextPeople); setRelationships(nextRelationships); setSources(nextSources); setAudits(nextAudits)
  }, [])

  useEffect(() => {
    api.me().then((current) => { setUsername(current.username); return loadData() }).then(() => setAuth('authenticated')).catch((reason) => {
      if (!(reason instanceof ApiError) || reason.status !== 401) setError(reason instanceof Error ? reason.message : '系统暂时不可用')
      setAuth('anonymous')
    })
  }, [loadData])

  const login = async (name: string, password: string) => {
    const current = await api.login(name, password)
    setUsername(current.username); await loadData(); setAuth('authenticated')
  }

  if (auth === 'loading') return <main className="loading-page"><div className="seal">谱</div><p>正在打开家族记忆…</p></main>
  if (auth === 'anonymous') return <LoginPage onLogin={login} />

  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="seal" aria-hidden="true">谱</div><div><strong>归源</strong><span>家族记忆助手</span></div></div><Navigation page={page} onChange={setPage} className="nav-list" label="主导航" /><div className="sidebar-foot"><div className="admin-avatar">{username.slice(0, 1).toUpperCase()}</div><div><strong>{username}</strong><span>唯一管理员</span></div></div></aside>
    <section className="workspace">
      <header className="topbar"><div className="mobile-brand"><span className="mini-seal">谱</span>归源</div><div className="topbar-tree"><span className="tree-mark" aria-hidden="true">枝</span><div><strong>家族记忆库</strong><span>{people.length} 位成员 · {sources.length} 份档案</span></div></div><div className="top-actions"><span className="sync"><i /> 数据已同步</span><button type="button" className="primary-small" onClick={() => setEditor('new')}>＋ 新增成员</button></div></header>
      {error && <div className="global-error" role="alert">{error}<button onClick={() => setError('')}>关闭</button></div>}
      {page === 'overview' && <Overview people={people} relationships={relationships} sources={sources} audits={audits} onAsk={() => setPage('assistant')} onAdd={() => setEditor('new')} />}
      {page === 'tree' && <FamilyTree people={people} relationships={relationships} refresh={loadData} onAdd={() => setEditor('new')} onEdit={setEditor} />}
      {page === 'assistant' && <Assistant memberCount={people.length} refresh={loadData} />}
      {page === 'archive' && <Archive sources={sources} onUpload={() => setUploading(true)} />}
      {page === 'settings' && <Settings username={username} onLogout={async () => { await api.logout(); setAuth('anonymous') }} />}
    </section>
    <Navigation page={page} onChange={setPage} className="mobile-nav" label="移动端导航" />
    {editor && <PersonEditor person={editor === 'new' ? undefined : editor} onSaved={loadData} onClose={() => setEditor(null)} />}
    {uploading && <SourceUploader people={people} onSaved={loadData} onClose={() => setUploading(false)} />}
  </div>
}

function Navigation({ page, onChange, className, label }: { page: Page; onChange: (page: Page) => void; className: string; label: string }) {
  return <nav aria-label={label} className={className}>{navigation.map((item) => <button type="button" key={item.id} className={page === item.id ? (className === 'nav-list' ? 'nav-item active' : 'active') : (className === 'nav-list' ? 'nav-item' : '')} onClick={() => onChange(item.id)}><span aria-hidden="true">{item.icon}</span>{item.label}</button>)}</nav>
}

function generationCount(people: Person[], relationships: Relationship[]) {
  if (!people.length) return 0
  const children = new Map<string, string[]>(), hasParent = new Set<string>()
  relationships.filter((item) => item.kind === 'parent').forEach((item) => { hasParent.add(item.person_id); children.set(item.relative_id, [...(children.get(item.relative_id) ?? []), item.person_id]) })
  const queue = people.map((item) => item.id).filter((id) => !hasParent.has(id)).map((id) => ({ id, depth: 1 })), seen = new Set<string>()
  let max = 1
  while (queue.length) { const current = queue.shift()!; if (seen.has(current.id)) continue; seen.add(current.id); max = Math.max(max, current.depth); for (const child of children.get(current.id) ?? []) queue.push({ id: child, depth: current.depth + 1 }) }
  return max
}

function Overview({ people, relationships, sources, audits, onAsk, onAdd }: { people: Person[]; relationships: Relationship[]; sources: Source[]; audits: AuditLog[]; onAsk: () => void; onAdd: () => void }) {
  const pending = people.filter((item) => item.verification_status !== 'verified').length + sources.filter((item) => item.verification_status !== 'verified').length
  return <main className="page overview-page"><div className="page-heading"><div><p className="eyebrow">PRIVATE FAMILY ARCHIVE</p><h1>家族概览</h1><p>记录每一个名字，也保存名字背后的故事。</p></div></div>
    <section className="stats-grid" aria-label="族谱统计"><Stat icon="人" tone="sage" value={people.length} label="收录成员" note="正式数据" /><Stat icon="代" tone="ochre" value={generationCount(people, relationships)} label="延续世代" note={`${relationships.length} 条关系`} /><Stat icon="档" tone="blue" value={sources.length} label="资料档案" note="私密保存" /><Stat icon="待" tone="coral" value={pending} label="待核实信息" note="需要关注" /></section>
    <section className="content-grid"><article className="panel family-preview"><div className="panel-title"><div><span>血脉一览</span><h2>最近人物</h2></div><button onClick={onAdd}>新增成员 →</button></div><div className="people-preview-grid">{people.slice(0, 6).map((person, index) => <PersonNode key={person.id} person={person} tone={['olive', 'clay', 'ink', 'sand', 'blue'][index % 5]} />)}{!people.length && <Empty text="还没有成员，从录入第一位家人开始。" />}</div></article><article className="panel activity-panel"><div className="panel-title"><div><span>动态</span><h2>最近更新</h2></div></div><ol className="activity-list">{audits.slice(0, 5).map((item) => <li key={item.id}><i className="dot sage" /><div><strong>{item.summary}</strong><span>{new Date(item.created_at).toLocaleString('zh-CN')}</span></div></li>)}{!audits.length && <Empty text="正式操作会记录在这里。" />}</ol></article></section>
    <section className="assistant-banner"><div className="spark">✦</div><div><span>归源智能体</span><h2>想从家族故事里发现什么？</h2><p>关系由规则计算，回答会展示资料来源；任何写入都要经过确认。</p></div><div className="banner-actions"><button onClick={onAsk}>问一个问题</button><button onClick={onAdd}>录入新成员</button></div></section></main>
}

function Stat({ icon, tone, value, label, note }: { icon: string; tone: string; value: number; label: string; note: string }) { return <article><span className={`stat-icon ${tone}`}>{icon}</span><div><b>{value}</b><span>{label}</span></div><em>{note}</em></article> }
function PersonNode({ person, tone = 'olive' }: { person: Person; tone?: string }) { const years = `${person.birth_date || '生年待考'}${person.death_date ? `—${person.death_date}` : ''}`; return <article className="person-node"><div className={`portrait ${tone}`}>{person.name.slice(-1)}</div><div><strong>{person.name}</strong><span>{years} · {person.verification_status === 'verified' ? '已核实' : '待核实'}</span></div></article> }

function Assistant({ memberCount, refresh }: { memberCount: number; refresh: () => Promise<void> }) {
  const [query, setQuery] = useState(''), [lastQuery, setLastQuery] = useState(''), [result, setResult] = useState<AgentResult | null>(null)
  const [saved, setSaved] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const ask = async (message: string) => { if (!message.trim() || busy) return; setBusy(true); setError(''); setSaved(false); setLastQuery(message); try { setResult(await api.queryAgent(message)) } catch (reason) { setError(reason instanceof Error ? reason.message : '智能体暂时不可用') } finally { setBusy(false); setQuery('') } }
  const submit = (event: FormEvent) => { event.preventDefault(); void ask(query) }
  const draft = result?.type === 'draft' ? result : null, answer = result?.type === 'answer' ? result : null
  const confirm = async () => { if (!draft) return; setBusy(true); setError(''); try { await api.confirmDraft(draft.draft_id); await refresh(); setSaved(true) } catch (reason) { setError(reason instanceof Error ? reason.message : '确认失败') } finally { setBusy(false) } }
  const reject = async () => { if (draft) await api.rejectDraft(draft.draft_id); setResult(null); setSaved(false) }
  return <main className="assistant-layout"><section className="chat-column"><header className="assistant-header"><div className="agent-avatar">✦</div><div><h1>归源智能体</h1><p><i /> 基于正式族谱与私密档案</p></div><span className="member-pill">共 {memberCount} 位成员</span></header><div className="messages" aria-live="polite"><div className="date-divider"><span>今天</span></div><AgentBubble><strong>你好，我是归源。</strong><p>可以查询亲属关系，或把自然语言整理为待确认的变更草稿。</p></AgentBubble>{lastQuery && <div className="message-row user"><div className="bubble">{lastQuery}</div><div className="user-avatar">管</div></div>}{answer && <AgentBubble><span className="answer-label">{answer.sources.length ? `已关联 ${answer.sources.length} 条资料` : '暂无关联资料'}</span><p className="answer-main">{answer.answer}</p></AgentBubble>}{draft && <AgentBubble>{saved ? <><strong className="saved-title">已写入族谱</strong><p>草稿已重新校验并完成正式写入。</p></> : <><strong>我已整理成变更草稿。</strong><p>请在右侧核对，确认前不会修改人物和关系。</p></>}</AgentBubble>}{error && <AgentBubble><p className="form-error">{error}</p></AgentBubble>}</div><div className="suggestion-row"><button onClick={() => void ask('张明远的外祖父是谁？')}>查询一段亲属关系</button><button onClick={() => setQuery('新增张明远的儿子张予安')}>辅助录入新成员</button></div><form className="composer" onSubmit={submit}><span aria-hidden="true">✦</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="询问家族关系，或描述要录入的资料…" aria-label="向归源提问" /><button type="submit" className="send-button" aria-label="发送" disabled={busy}>{busy ? '…' : '↑'}</button><small>智能体只生成答案或草稿，重要信息请核对</small></form></section><aside className={`context-panel ${draft ? 'active-context' : ''}`}>{draft ? (saved ? <SavedPanel /> : <ChangePreview draft={draft} onConfirm={confirm} onReject={reject} busy={busy} />) : <EvidencePanel answer={answer} />}</aside></main>
}

function AgentBubble({ children }: { children: ReactNode }) { return <div className="message-row agent"><div className="message-avatar">归</div><div className="bubble">{children}</div></div> }
function EvidencePanel({ answer }: { answer: AgentAnswer | null }) { return <div className="context-content"><p className="context-kicker">{answer ? '本次回答依据' : '智能体工作台'}</p><h2>{answer ? '关系路径' : '可信回答，有据可查'}</h2>{answer ? <><div className="path-stack">{answer.relationship.steps.map((step, index) => <div key={step.person_id}>{index > 0 && <div className="relation-line"><i /><span>关系链第 {index} 步</span></div>}<PersonLine name={step.person_name} /></div>)}</div>{answer.sources.map((source) => <div className="source-card" key={source.id}><span>{source.verification_status === 'verified' ? '已核实来源' : '待核实来源'}</span><strong>{source.title}</strong><a href={`/api/sources/${source.id}/download`}>查看原始档案 ↗</a></div>)}{!answer.sources.length && <Empty text="尚未关联资料，此结论需要补充证据。" />}</> : <div className="empty-context"><div>引</div><p>提问后，这里会展示关系路径、引用资料和核实状态。</p></div>}</div> }
function PersonLine({ name }: { name: string }) { return <div className="person-line"><div>{name.slice(-1)}</div><span><strong>{name}</strong><small>正式族谱人物</small></span></div> }
function ChangePreview({ draft, onConfirm, onReject, busy }: { draft: DraftPreview; onConfirm: () => void; onReject: () => void; busy: boolean }) { const gender = { male: '男', female: '女', unknown: '未知' }[draft.payload.person.gender]; return <div className="context-content preview-content"><p className="context-kicker">写入前核对</p><h2>变更预览</h2><div className="change-status"><span>＋</span><div><strong>{draft.summary}</strong><p>尚未写入族谱</p></div></div><dl className="field-list"><div><dt>姓名</dt><dd>{draft.payload.person.name}</dd></div><div><dt>性别</dt><dd>{gender}</dd></div>{draft.payload.parent_name && <div><dt>父母</dt><dd>{draft.payload.parent_name}</dd></div>}</dl><div className="safety-note"><strong>确认机制</strong><p>确认时后端会重新校验当前数据，并在单一事务中写入。</p></div><button className="confirm-button" onClick={onConfirm} disabled={busy}>确认写入</button><button className="cancel-button" onClick={onReject}>拒绝草稿</button></div> }
function SavedPanel() { return <div className="context-content saved-panel"><div className="success-mark">✓</div><p className="context-kicker">操作完成</p><h2>已写入族谱</h2><p>正式数据和操作日志已经更新。</p></div> }

function FamilyTree({ people, relationships, refresh, onAdd, onEdit }: { people: Person[]; relationships: Relationship[]; refresh: () => Promise<void>; onAdd: () => void; onEdit: (person: Person) => void }) {
  const [kind, setKind] = useState<'parent' | 'spouse'>('parent')
  const [personId, setPersonId] = useState(people[0]?.id ?? '')
  const [relativeId, setRelativeId] = useState(people[1]?.id ?? people[0]?.id ?? '')
  const [error, setError] = useState('')
  const personMap = new Map(people.map((person) => [person.id, person.name]))
  const create = async (event: FormEvent) => { event.preventDefault(); setError(''); try { await api.createRelationship({ kind, person_id: personId, relative_id: relativeId }); await refresh() } catch (reason) { setError(reason instanceof Error ? reason.message : '关系保存失败') } }
  const remove = async (id: string) => { try { await api.deleteRelationship(id); await refresh() } catch (reason) { setError(reason instanceof Error ? reason.message : '关系删除失败') } }
  return <main className="page simple-page"><div className="page-heading"><div><p className="eyebrow">GENEALOGY</p><h1>族谱与人物档案</h1><p>{relationships.length} 条正式关系，点击人物可编辑档案。</p></div><button className="primary-small" onClick={onAdd}>＋ 添加成员</button></div>
    <div className="panel people-directory">{people.map((person, index) => <button type="button" key={person.id} onClick={() => onEdit(person)}><PersonNode person={person} tone={['olive', 'clay', 'ink', 'sand', 'blue'][index % 5]} /></button>)}{!people.length && <Empty text="还没有族谱人物。" />}</div>
    <section className="panel relationship-manager"><div className="panel-title"><div><span>关系维护</span><h2>父母与配偶</h2></div></div><form onSubmit={create}><label>关系类型<select value={kind} onChange={(event) => setKind(event.target.value as 'parent' | 'spouse')}><option value="parent">父母关系</option><option value="spouse">配偶关系</option></select></label><label>人物<select aria-label="人物" value={personId} onChange={(event) => setPersonId(event.target.value)}>{people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label><label>亲属<select aria-label="亲属" value={relativeId} onChange={(event) => setRelativeId(event.target.value)}>{people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label><button className="primary-small" disabled={people.length < 2}>建立关系</button></form>{error && <p className="form-error" role="alert">{error}</p>}<div className="relationship-list">{relationships.map((item) => <div key={item.id}><span>{personMap.get(item.person_id)} {item.kind === 'parent' ? '的父母是' : '的配偶是'} {personMap.get(item.relative_id)}</span><button type="button" onClick={() => void remove(item.id)}>删除</button></div>)}{!relationships.length && <Empty text="还没有亲属关系。" />}</div></section>
  </main>
}
function Archive({ sources, onUpload }: { sources: Source[]; onUpload: () => void }) { return <main className="page simple-page"><div className="page-heading"><div><p className="eyebrow">PRIVATE SOURCES</p><h1>资料档案</h1><p>原件只通过登录后的受保护接口下载。</p></div><button className="primary-small" onClick={onUpload}>＋ 上传资料</button></div><div className="archive-grid">{sources.map((source, index) => <article className="archive-card" key={source.id}><div className={`document-cover cover-${index % 4 + 1}`}>{source.source_type === 'image' ? '影' : source.source_type === 'text' ? '记' : '卷'}</div><span>{source.verification_status === 'verified' ? '已核实' : '待核实'} · {source.era || '年代待考'}</span><h2>{source.title}</h2><p>{source.original_filename} · {Math.ceil(source.size_bytes / 1024)} KB</p><a href={`/api/sources/${source.id}/download`}>查看原件</a></article>)}{!sources.length && <Empty text="还没有资料，上传 PDF、图片或文字记录。" />}</div></main> }
function Settings({ username, onLogout }: { username: string; onLogout: () => Promise<void> }) { return <main className="page simple-page"><div className="page-heading"><div><p className="eyebrow">SYSTEM</p><h1>设置</h1><p>敏感配置由服务器环境变量管理，不会发送到浏览器。</p></div></div><div className="panel settings-panel"><h2>安全与模型</h2><div className="setting-row"><div><strong>当前管理员</strong><p>{username} · 单管理员模式</p></div><button className="outline-button" onClick={() => void onLogout()}>退出登录</button></div><div className="setting-row"><div><strong>写入前人工确认</strong><p>智能体正式写入只能通过已保存草稿的确认接口。</p></div><span className="toggle on"><i /></span></div><div className="setting-row"><div><strong>托管模型服务</strong><p>OpenAI 兼容 API · 由服务端配置</p></div><span className="toggle on"><i /></span></div></div></main> }
function Empty({ text }: { text: string }) { return <div className="empty-state">{text}</div> }
