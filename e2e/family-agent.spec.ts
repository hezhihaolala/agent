import { expect, test } from '@playwright/test'

test('登录、建关系、关系问答和草稿确认构成完整流程', async ({ page }) => {
  const consoleErrors: string[] = []
  const suffix = Date.now().toString().slice(-6)
  const childName = `测试子${suffix}`
  const motherName = `测试母${suffix}`
  const draftName = `测试新${suffix}`

  await page.goto('/')
  await page.getByLabel('密码').fill('e2e-password')
  await page.getByRole('button', { name: '登录归源' }).click()
  await expect(page.getByRole('heading', { name: '家族概览' })).toBeVisible()
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })

  for (const [name, gender] of [[childName, 'male'], [motherName, 'female']] as const) {
    await page.getByRole('button', { name: '＋ 新增成员' }).click()
    await page.getByLabel('姓名').fill(name)
    await page.getByLabel('性别').selectOption(gender)
    await page.getByRole('button', { name: '保存人物' }).click()
  }

  await page.getByRole('navigation', { name: '主导航' }).getByRole('button', { name: '资料档案' }).click()
  await page.getByRole('button', { name: '＋ 上传资料' }).click()
  await page.getByLabel('资料名称').fill(`测试档案${suffix}`)
  await page.getByLabel('资料类型').selectOption('text')
  await page.getByLabel('关联人物（可选）').selectOption({ label: childName })
  await page.getByLabel('选择文件').setInputFiles({ name: `memo-${suffix}.txt`, mimeType: 'text/plain', buffer: Buffer.from('family evidence') })
  await page.getByRole('button', { name: '安全上传' }).click()
  await expect(page.getByRole('heading', { name: `测试档案${suffix}` })).toBeVisible()

  const sourceList = await (await page.request.get('/api/sources')).json()
  const sourceDetail = await (await page.request.get(`/api/sources/${sourceList[0].id}`)).json()
  expect(sourceDetail.links[0].entity_id).toBeTruthy()

  await page.getByRole('navigation', { name: '主导航' }).getByRole('button', { name: '族谱' }).click()
  await page.getByLabel('人物').selectOption({ label: childName })
  await page.getByLabel('亲属').selectOption({ label: motherName })
  await page.getByRole('button', { name: '建立关系' }).click()
  await expect(page.getByText(`${childName} 的父母是 ${motherName}`)).toBeVisible()

  await page.getByRole('navigation', { name: '主导航' }).getByRole('button', { name: '智能体' }).click()
  await page.getByLabel('向归源提问').fill(`${childName}与${motherName}是什么关系`)
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByText(`${motherName}是${childName}的母亲。当前来源不足，结论待核实。`)).toBeVisible()

  await page.getByLabel('向归源提问').fill(`${childName}的父母是谁`)
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByText(`${childName}的父母是${motherName}。当前来源不足，结论待核实。`)).toBeVisible()

  await page.getByLabel('向归源提问').fill(`新增${draftName}`)
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('heading', { name: '变更预览' })).toBeVisible()
  await page.getByRole('button', { name: '确认写入' }).click()
  await expect(page.getByRole('heading', { name: '已写入族谱' })).toBeVisible()

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('navigation', { name: '移动端导航' }).getByRole('button', { name: '概览' }).click()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  expect(consoleErrors).toEqual([])
})
