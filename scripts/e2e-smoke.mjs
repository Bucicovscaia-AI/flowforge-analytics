// End-to-end smoke test of the running application in a real browser.
//
// It drives the core user journey against a live backend (which also serves
// the built frontend): upload validation errors, a real CSV upload, every
// page, insights, PDF generation and download, report history, and the
// mobile layout. With SCREENSHOT_DIR set it also saves the screenshots used
// in the README.
//
// Usage (from the repository root, with the backend running on port 8000
// and `npm run build` done in frontend/):
//   node scripts/e2e-smoke.mjs
//   SCREENSHOT_DIR=screenshots node scripts/e2e-smoke.mjs
//
// Requires Playwright (`npm i -g playwright && npx playwright install chromium`).

import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
let chromium
try {
  ;({ chromium } = require('playwright'))
} catch {
  console.error('Playwright is not installed. Run: npm i -g playwright && npx playwright install chromium')
  process.exit(2)
}

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const BASE = process.env.BASE_URL ?? 'http://localhost:8000'
const SHOTS = process.env.SCREENSHOT_DIR ? resolve(process.env.SCREENSHOT_DIR) : null
const SAMPLE = join(ROOT, 'sample-data', 'retail_sales_2026_synthetic.csv')

const results = []
const nav = (p, name) => p.getByRole('navigation', { name: 'Main' }).getByRole('link', { name })
const consoleErrors = []

async function step(name, fn) {
  try {
    await fn()
    results.push({ name, ok: true })
    console.log(`PASS  ${name}`)
  } catch (error) {
    results.push({ name, ok: false })
    console.log(`FAIL  ${name}\n      ${error.message.split('\n')[0]}`)
  }
}

async function shot(page, name, fullPage = true) {
  if (!SHOTS) return
  // Close notifications so they do not cover the page in the screenshot.
  for (const button of await page.getByRole('button', { name: 'Dismiss notification' }).all()) await button.click()
  await page.waitForTimeout(400)
  await page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage })
}

function expect(condition, message) {
  if (!condition) throw new Error(message)
}

const tmp = mkdtempSync(join(tmpdir(), 'flowforge-e2e-'))
const badCsv = join(tmp, 'missing_columns.csv')
writeFileSync(badCsv, 'order_ref,amount\nA1,10\n')
if (SHOTS) mkdirSync(SHOTS, { recursive: true })

const browser = await chromium.launch()
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true })
const page = await context.newPage()
page.on('console', (msg) => msg.type() === 'error' && consoleErrors.push(msg.text()))
page.on('pageerror', (err) => consoleErrors.push(err.message))

await step('dashboard shows the empty state before any analysis', async () => {
  await page.goto(BASE)
  await page.getByText('Start by analysing a dataset').waitFor()
})

await step('upload rejects a non-CSV file in the browser', async () => {
  await page.goto(`${BASE}/upload`)
  await page.locator('input[type=file]').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('hello') })
  await page.getByText('"notes.txt" is not a CSV file', { exact: false }).waitFor()
})

await step('server rejects a CSV without the required columns', async () => {
  await page.locator('input[type=file]').setInputFiles(badCsv)
  await page.getByRole('button', { name: 'Validate and analyse' }).click()
  await page.getByText('Required columns are missing', { exact: false }).first().waitFor()
  await shot(page, 'upload-validation-error', false)
})

await step('real CSV upload is validated, cleaned and analysed', async () => {
  await page.locator('input[type=file]').setInputFiles(SAMPLE)
  await page.getByRole('button', { name: 'Validate and analyse' }).click()
  await page.getByText('retail_sales_2026_synthetic.csv analysed').waitFor({ timeout: 20000 })
  const text = await page.locator('[role=status]').filter({ hasText: 'rows received' }).innerText()
  expect(/1,152 rows received/.test(text), `unexpected summary: ${text}`)
  await shot(page, 'upload-success', false)
})

await step('dashboard shows KPIs and charts from the analysis', async () => {
  await nav(page, 'Dashboard').click()
  await page.getByText('Total revenue').waitFor()
  await page.getByText('£107,833').waitFor()
  expect((await page.locator('.recharts-surface').count()) >= 3, 'expected three charts')
  await shot(page, 'dashboard')
})

await step('data analysis page lists cleaning rules and column profile', async () => {
  await nav(page, 'Data Analysis').click()
  await page.getByRole('heading', { name: 'Cleaning rules applied' }).waitFor()
  await page.getByRole('heading', { name: 'Column profile' }).waitFor()
  await shot(page, 'data-analysis')
})

await step('insights page shows labelled observations', async () => {
  await nav(page, 'AI Insights').click()
  await page.getByRole('button', { name: /Generate AI insights|Refresh observations/ }).click()
  await page.getByText(/AI-generated ·|Rule-based observations \(not AI-generated\)/).first().waitFor({ timeout: 90000 })
  await shot(page, 'ai-insights')
})

await step('report is generated and the PDF downloads', async () => {
  await nav(page, 'Reports').click()
  await page.getByRole('button', { name: 'Generate report' }).click()
  const link = page.getByRole('link', { name: /Download PDF/ })
  await link.waitFor({ timeout: 20000 })
  await shot(page, 'reports', false)
  const [download] = await Promise.all([page.waitForEvent('download'), link.click()])
  const path = await download.path()
  const { readFileSync } = await import('node:fs')
  expect(readFileSync(path).subarray(0, 5).toString() === '%PDF-', 'download is not a PDF')
})

await step('report history lists the generated report', async () => {
  await nav(page, 'Report History').click()
  await page.getByRole('link', { name: /^Download Sales performance report/ }).first().waitFor()
  await shot(page, 'report-history', false)
})

await step('settings shows integration status', async () => {
  await nav(page, 'Settings').click()
  await page.getByText('Make.com webhook').waitFor()
  await shot(page, 'settings')
})

const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 })
const phone = await mobile.newPage()
phone.on('pageerror', (err) => consoleErrors.push(err.message))

await step('mobile layout has no horizontal scrolling', async () => {
  // Reuse the analysis chosen on desktop (the id is kept in localStorage).
  const id = await page.evaluate(() => localStorage.getItem('flowforge.currentAnalysisId'))
  await phone.goto(BASE)
  await phone.evaluate((value) => localStorage.setItem('flowforge.currentAnalysisId', value), id)
  for (const path of ['/', '/upload', '/analysis', '/insights', '/reports', '/history', '/settings']) {
    await phone.goto(`${BASE}${path}`)
    await phone.locator('h1').waitFor()
    await phone.waitForTimeout(300)
    const width = await phone.evaluate(() => document.documentElement.scrollWidth)
    expect(width <= 390, `${path} is ${width}px wide`)
  }
  await phone.goto(BASE)
  await phone.getByText('Total revenue').waitFor()
  await shot(phone, 'mobile-dashboard', false)
  await phone.getByRole('button', { name: 'Open navigation menu' }).click()
  await shot(phone, 'mobile-menu', false)
})

await step('no browser console errors', async () => {
  // The deliberate 422 upload is logged by the browser as a failed request.
  const unexpected = consoleErrors.filter((e) => !/status of 422/.test(e))
  expect(unexpected.length === 0, unexpected.join(' | '))
})

await browser.close()
const failed = results.filter((r) => !r.ok).length
console.log(`\n${results.length - failed} passed, ${failed} failed`)
process.exit(failed ? 1 : 0)
