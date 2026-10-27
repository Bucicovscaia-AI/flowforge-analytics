const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')
// End-to-end walkthrough of the main workflow in a real browser, saving the README screenshots.
// Run against a fresh backend (empty DATA_DIR, no AI key, no webhook) and the built frontend:
//   node scripts/e2e_walkthrough.cjs [downloads-dir]
// Requires Playwright with Chromium (npm install --no-save playwright && npx playwright install chromium).
const os = require('os')
const ROOT = path.resolve(__dirname, '..')
const BASE = process.env.BASE_URL ?? 'http://127.0.0.1:4173'
const SHOTS = path.join(ROOT, 'screenshots')
const DL = process.argv[2] ?? fs.mkdtempSync(path.join(os.tmpdir(), 'flowforge-e2e-'))
const SAMPLE = path.join(ROOT, 'sample-data', 'flowforge-retail-sample.csv')
const problems = []
const log = (...a) => console.log('•', ...a)

;(async () => {
  const browser = await chromium.launch()
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true, locale: 'en-GB' })
  const page = await context.newPage()
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') problems.push(`console ${m.type()}: ${m.text()}`) })
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`))
  page.on('response', (r) => { if (r.url().includes('/api/') && r.status() >= 400) problems.push(`HTTP ${r.status()} ${r.url()}`) })
  const shot = async (name, full = true) => {
    await page.waitForTimeout(600)
    if (full) {
      const height = await page.evaluate(() => document.documentElement.scrollHeight)
      await page.setViewportSize({ width: 1440, height: Math.min(Math.max(900, height), 4000) })
      await page.waitForTimeout(400)
    }
    await page.screenshot({ path: path.join(SHOTS, name) })
    await page.setViewportSize({ width: 1440, height: 900 })
    log('screenshot', name)
  }
  const h1 = () => page.locator('h1').first().textContent()

  await page.goto(BASE + '/')
  await page.getByRole('button', { name: /Explore sample data/ }).waitFor()
  await shot('01-onboarding.png', false)

  // Real upload of the sample file through the file input
  await page.goto(BASE + '/upload')
  await page.locator('input[type=file]').setInputFiles(SAMPLE)
  await page.getByLabel('Dataset name (optional)').fill('Retail orders upload')
  await page.getByRole('button', { name: 'Upload and validate' }).click()
  await page.getByText('Import complete').waitFor({ timeout: 20000 })
  await page.getByRole('table').first().waitFor()
  await shot('02-upload-result.png')

  // Rejected upload: not a CSV
  const bad = path.join(DL, 'notes.csv'); fs.writeFileSync(bad, Buffer.from([0, 1, 2, 0, 5, 6]))
  await page.locator('input[type=file]').setInputFiles(bad)
  await page.getByRole('button', { name: 'Upload and validate' }).click()
  await page.getByText('The server rejected this file').waitFor()
  log('binary file rejected:', (await page.locator('text=The server rejected this file').locator('..').textContent()).slice(0, 160))
  problems.splice(0, problems.length, ...problems.filter((p) => !p.includes('HTTP 4') && !p.includes('status of 4')))

  // Load the labelled demonstration dataset, then delete the uploaded copy from the Datasets page
  await page.getByRole('button', { name: 'Load sample dataset' }).click()
  await page.getByText('Sample dataset loaded').waitFor()
  await page.goto(BASE + '/datasets'); await page.getByRole('button', { name: 'Delete Retail orders upload' }).waitFor()
  await page.getByRole('button', { name: 'Delete Retail orders upload' }).click()
  await page.getByRole('button', { name: 'Delete dataset' }).click()
  await page.getByText('Dataset deleted').waitFor()
  await page.getByText(/Columns in /).waitFor()
  await shot('03-datasets.png', false)

  await page.goto(BASE + '/quality'); await page.getByText('Clean the data').waitFor()
  const scoreBefore = await page.locator('main').getByText(/\/ 100|score/i).first().textContent().catch(() => '')
  await shot('04-quality.png')
  // Apply the first suggested fix: preview then apply
  const fix = page.getByRole('button', { name: /Remove duplicate|duplicate/i }).first()
  await fix.click()
  await page.getByRole('button', { name: 'Preview', exact: true }).click()
  await page.getByText(/^Preview:/).waitFor()
  log('cleaning preview:', await page.getByText(/^Preview:/).textContent())
  await page.getByRole('button', { name: 'Apply to working copy' }).click()
  const confirm = page.getByRole('button', { name: 'Apply and remove' })
  if (await confirm.isVisible().catch(() => false)) await confirm.click()
  await page.getByText(/Cleaning history|applied/i).first().waitFor()
  await page.waitForTimeout(1500)
  await shot('05-quality-after-cleaning.png')

  await page.goto(BASE + '/'); await page.getByText(/Total revenue/i).first().waitFor({ timeout: 20000 })
  await shot('06-dashboard.png')

  await page.goto(BASE + '/analysis'); await page.getByText('Column summaries').waitFor({ timeout: 20000 })
  await shot('07-analysis.png')

  await page.goto(BASE + '/visualisations'); await page.getByText('Build a chart').waitFor()
  await page.locator('.recharts-surface').first().waitFor()
  await shot('08-visualisations.png')
  await page.getByRole('radio', { name: 'Distribution' }).click()
  await page.getByText(/^Distribution of/).waitFor()
  const csvDownload = page.waitForEvent('download')
  await page.getByRole('link', { name: 'CSV' }).first().click()
  const csvFile = await csvDownload; const csvPath = path.join(DL, 'grouped.csv'); await csvFile.saveAs(csvPath)
  log('grouped CSV:', fs.readFileSync(csvPath, 'utf8').split('\n').slice(0, 3).join(' | '))

  await page.goto(BASE + '/insights'); await page.getByText('Rule-based mode').waitFor({ timeout: 20000 })
  await shot('09-insights.png')

  await page.goto(BASE + '/reports')
  await page.getByLabel('Report title (optional)').fill('Retail orders review')
  await page.getByRole('button', { name: 'Generate report' }).click()
  await page.getByText(/^Generated .* from /).waitFor({ timeout: 30000 })
  await shot('10-reports.png')
  for (const fmt of ['HTML', 'PDF', 'CSV', 'JSON']) {
    const d = page.waitForEvent('download')
    await page.getByRole('link', { name: fmt, exact: true }).first().click()
    const file = await d; const target = path.join(DL, file.suggestedFilename()); await file.saveAs(target)
    log(`report ${fmt}:`, file.suggestedFilename(), fs.statSync(target).size, 'bytes')
  }

  await page.goto(BASE + '/reports/history'); await page.getByText('Retail orders review').first().waitFor()
  await shot('11-report-history.png', false)

  await page.goto(BASE + '/automation'); await page.getByText('Make.com connection').waitFor()
  await page.getByRole('button', { name: 'Preview payload' }).click()
  await page.getByLabel('Payload preview').waitFor()
  log('send button disabled without webhook:', await page.getByRole('button', { name: 'Send to Make.com' }).isDisabled())
  await shot('12-automation.png')

  await page.goto(BASE + '/settings'); await page.getByText('Upload limits').waitFor()
  await shot('13-settings.png', false)

  // The generated HTML report as it opens in the browser
  const reportId = await page.evaluate(async () => (await (await fetch('/api/reports')).json())[0].id)
  await page.goto(`${BASE}/api/reports/${reportId}/download?format=html&inline=true`)
  await shot('14-html-report.png', false)

  // Mobile layout
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } })
  mobile.on('pageerror', (e) => problems.push(`mobile pageerror: ${e.message}`))
  await mobile.goto(BASE + '/'); await mobile.getByText(/Total revenue/i).first().waitFor({ timeout: 20000 })
  await mobile.waitForTimeout(600)
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  log('mobile horizontal overflow px:', overflow)
  await mobile.screenshot({ path: path.join(SHOTS, '15-mobile-dashboard.png') })

  await browser.close()
  console.log('\nPROBLEMS:', problems.length ? '\n' + problems.join('\n') : 'none')
  if (problems.length) process.exitCode = 1
})().catch((e) => { console.error('FAILED', e); console.log('PROBLEMS so far:', problems.join('\n')); process.exit(1) })
