import { render, screen } from '@testing-library/react'
import { App } from './App'

describe('家谱智能体 Demo', () => {
  it('默认显示族谱概览和主要导航', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '家族概览' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: '主导航' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '智能体' })).toBeInTheDocument()
  })
})
