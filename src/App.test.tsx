import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { App } from './App'

afterEach(cleanup)

describe('家谱智能体 Demo', () => {
  it('默认显示族谱概览和主要导航', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '家族概览' })).toBeInTheDocument()
    const mainNav = screen.getByRole('navigation', { name: '主导航' })
    expect(mainNav).toBeInTheDocument()
    expect(within(mainNav).getByRole('button', { name: '智能体' })).toBeInTheDocument()
  })

  it('移动端导航按钮使用不含装饰图标的可访问名称', () => {
    render(<App />)

    const mobileNav = screen.getByRole('navigation', { name: '移动端导航' })
    expect(mobileNav).toHaveAccessibleName('移动端导航')
    expect(mobileNav.querySelector('button:nth-child(3)')).toHaveAccessibleName('智能体')
    expect(within(mobileNav).getByRole('button', { name: '设置' })).toBeInTheDocument()
  })

  it('通过示例问题展示亲属结论和依据', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(within(screen.getByRole('navigation', { name: '主导航' })).getByRole('button', { name: '智能体' }))
    await user.click(screen.getByRole('button', { name: '张明远的外祖父是谁？' }))

    expect(screen.getByText('张明远的外祖父是陈守义。')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '关系路径' })).toBeInTheDocument()
    expect(screen.getByText('《陈氏家谱》民国三十六年续修本')).toBeInTheDocument()
  })

  it('新增成员必须先预览，确认后才更新模拟人数', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(within(screen.getByRole('navigation', { name: '主导航' })).getByRole('button', { name: '智能体' }))
    await user.click(screen.getByRole('button', { name: '模拟录入成员' }))

    const previewHeading = screen.getByText('变更预览')
    expect(previewHeading).toBeInTheDocument()
    expect(previewHeading.closest('aside')).toHaveClass('active-context')
    expect(screen.getByText('共 24 位成员')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '确认写入' }))

    expect(screen.getByText('已模拟写入族谱')).toBeInTheDocument()
    expect(screen.getByText('共 25 位成员')).toBeInTheDocument()
  })
})
