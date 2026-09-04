import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import productDesign from '../docs/product-design.md?raw'
import technicalDesign from '../docs/technical-design.md?raw'
import implementationPlan from '../docs/superpowers/plans/2026-09-04-family-agent-mvp.md?raw'
import { App } from './App'

type MockResponse = { ok: boolean; status: number; json: () => Promise<unknown> }

function response(body: unknown, status = 200): MockResponse {
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

const person = (id: string, name: string) => ({
  id,
  name,
  gender: 'male',
  birth_date: null,
  death_date: null,
  native_place: null,
  biography: null,
  verification_status: 'verified',
  created_at: '2026-09-04T00:00:00Z',
  updated_at: '2026-09-04T00:00:00Z',
})

function dataResponse(url: string, people = [person('p1', '张明远')]) {
  if (url.endsWith('/api/persons')) return response(people)
  if (url.endsWith('/api/relationships')) return response([])
  if (url.endsWith('/api/sources')) return response([])
  if (url.endsWith('/api/audit-logs')) return response([])
  throw new Error(`未模拟请求：${url}`)
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('归源家族记忆助手', () => {
  it('设计文档和实施计划保留关键边界', () => {
    expect(productDesign).toContain('## 5. MVP 范围')
    expect(technicalDesign).toContain('模型只能提出变更')
    expect(implementationPlan).toContain('Task 6: Migrations, Production Deployment')
    expect(`${productDesign}${technicalDesign}`).not.toMatch(/TODO|TBD/)
  })

  it('未登录时显示登录页，登录后加载真实概览数量', async () => {
    const people = [person('p1', '张明远'), person('p2', '陈素贞')]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/auth/me')) return response({ detail: '未登录' }, 401)
      if (url.endsWith('/api/auth/login')) {
        expect(init?.credentials).toBe('include')
        return response({ username: 'admin', csrf_token: 'csrf-token' })
      }
      return dataResponse(url, people)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    await screen.findByRole('heading', { name: '管理员登录' })
    await user.type(screen.getByLabelText('管理员账号'), 'admin')
    await user.type(screen.getByLabelText('密码'), 'correct horse battery staple')
    await user.click(screen.getByRole('button', { name: '登录归源' }))

    expect(await screen.findByRole('heading', { name: '家族概览' })).toBeInTheDocument()
    const memberStat = screen.getByText('收录成员').closest('article')
    expect(memberStat).not.toBeNull()
    expect(within(memberStat!).getByText('2')).toBeInTheDocument()
  })

  it('聊天页展示 API 返回的确定性关系和来源', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/auth/me')) return response({ username: 'admin', csrf_token: 'csrf-token' })
      if (url.endsWith('/api/agent/query')) {
        return response({
          type: 'answer',
          answer: '陈守义是张明远的外祖父。结论来自已核实资料。',
          relationship: {
            label: '外祖父',
            steps: [
              { person_id: 'p1', person_name: '张明远' },
              { person_id: 'p2', person_name: '陈素贞' },
              { person_id: 'p3', person_name: '陈守义' },
            ],
          },
          sources: [{ id: 's1', title: '《陈氏家谱》续修本', verification_status: 'verified' }],
          verification_status: 'verified',
        })
      }
      return dataResponse(url)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    const mainNav = await screen.findByRole('navigation', { name: '主导航' })
    await user.click(within(mainNav).getByRole('button', { name: '智能体' }))
    await user.type(screen.getByLabelText('向归源提问'), '张明远的外祖父是谁？')
    await user.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText('陈守义是张明远的外祖父。结论来自已核实资料。')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '关系路径' })).toBeInTheDocument()
    expect(screen.getByText('《陈氏家谱》续修本')).toBeInTheDocument()
  })

  it('智能体草稿确认前不改变人数，确认后重新加载成员', async () => {
    const initial = [person('p1', '张明远')]
    const confirmed = [...initial, person('p2', '张予安')]
    let didConfirm = false
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/auth/me')) return response({ username: 'admin', csrf_token: 'csrf-token' })
      if (url.endsWith('/api/agent/query')) {
        return response({
          type: 'draft',
          draft_id: 'draft-1',
          status: 'pending',
          summary: '新增子女：张予安',
          payload: { operation: 'create_child', person: { name: '张予安', gender: 'male' }, parent_name: '张明远' },
        })
      }
      if (url.endsWith('/api/change-drafts/draft-1/confirm')) {
        didConfirm = true
        return response({ id: 'draft-1', status: 'confirmed' })
      }
      if (url.endsWith('/api/persons')) return response(didConfirm ? confirmed : initial)
      return dataResponse(url)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    const mainNav = await screen.findByRole('navigation', { name: '主导航' })
    await user.click(within(mainNav).getByRole('button', { name: '智能体' }))
    await user.type(screen.getByLabelText('向归源提问'), '新增张明远的儿子张予安')
    await user.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByRole('heading', { name: '变更预览' })).toBeInTheDocument()
    expect(screen.getByText('共 1 位成员')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '确认写入' }))

    expect(await screen.findByRole('heading', { name: '已写入族谱' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('共 2 位成员')).toBeInTheDocument())
  })

  it('族谱页可以建立父母关系并刷新关系列表', async () => {
    const people = [person('p1', '张明远'), person('p2', '陈素贞')]
    let relationships: unknown[] = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/auth/me')) return response({ username: 'admin', csrf_token: 'csrf-token' })
      if (url.endsWith('/api/relationships') && init?.method === 'POST') {
        relationships = [{ id: 'r1', kind: 'parent', person_id: 'p1', relative_id: 'p2', verification_status: 'unverified', created_at: '2026-09-04T00:00:00Z' }]
        return response(relationships[0], 201)
      }
      if (url.endsWith('/api/relationships')) return response(relationships)
      return dataResponse(url, people)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    const mainNav = await screen.findByRole('navigation', { name: '主导航' })
    await user.click(within(mainNav).getByRole('button', { name: '族谱' }))
    await user.selectOptions(screen.getByLabelText('人物'), 'p1')
    await user.selectOptions(screen.getByLabelText('亲属'), 'p2')
    await user.click(screen.getByRole('button', { name: '建立关系' }))

    expect(await screen.findByText('张明远 的父母是 陈素贞')).toBeInTheDocument()
  })

  it('族谱页可以选择兄弟姊妹和堂兄弟姊妹关系', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/auth/me')) return response({ username: 'admin', csrf_token: 'csrf-token' })
      return dataResponse(url, [person('p1', '贺志豪'), person('p2', '贺志兰')])
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    const mainNav = await screen.findByRole('navigation', { name: '主导航' })
    await user.click(within(mainNav).getByRole('button', { name: '族谱' }))

    expect(screen.getByRole('option', { name: '兄弟姊妹关系' })).toHaveValue('sibling')
    expect(screen.getByRole('option', { name: '堂兄弟姊妹关系' })).toHaveValue('paternal_cousin')
  })

  it('设置页验证当前密码后提交新密码', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/auth/me')) return response({ username: 'admin', csrf_token: 'csrf-token' })
      if (url.endsWith('/api/auth/password')) {
        expect(init?.method).toBe('POST')
        expect(new Headers(init?.headers).get('X-CSRF-Token')).toBe('csrf-token')
        expect(JSON.parse(String(init?.body))).toEqual({ current_password: 'old password', new_password: 'new secure password' })
        return response(null, 204)
      }
      return dataResponse(url)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    const mainNav = await screen.findByRole('navigation', { name: '主导航' })
    await user.click(within(mainNav).getByRole('button', { name: '设置' }))
    await user.type(screen.getByLabelText('当前密码'), 'old password')
    await user.type(screen.getByLabelText('新密码'), 'new secure password')
    await user.type(screen.getByLabelText('确认新密码'), 'new secure password')
    await user.click(screen.getByRole('button', { name: '修改密码' }))

    expect(await screen.findByText('密码已更新')).toBeInTheDocument()
  })
})
