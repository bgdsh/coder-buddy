const { test, expect } = require('@playwright/test');

const buddyIp = process.env.BUDDY_IP || '192.168.31.219';
const baseUrl = process.env.BUDDY_URL || `http://${buddyIp}`;

test.describe.configure({ mode: 'serial' });

async function waitForDashboard(page) {
  await expect(page).toHaveTitle('代码伙伴');
  await expect(page.locator('#device')).toContainText(buddyIp, { timeout: 8000 });
  await expect(page.locator('#ip')).toHaveText(buddyIp);
  await expect(page.getByRole('button', { name: '触发 +1' })).toBeVisible();
  await expect(page.getByRole('button', { name: '停止 -1' })).toBeVisible();
  await expect(page.getByRole('button', { name: '重置' })).toBeVisible();
  await expect(page.getByRole('button', { name: '保存音轨' })).toBeVisible();
  await expect(page.locator('#track option')).not.toHaveCount(0);
}

test.afterEach(async ({ request }) => {
  await request.post(`${baseUrl}/reset`).catch(() => {});
});

test('root page loads and hydrates from the status API', async ({ page }) => {
  await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded' });
  await waitForDashboard(page);
  await expect(page.locator('#level')).toHaveText(/^[0-9]+$/);
  await expect(page.locator('#trackName')).not.toHaveText('-');
});

test('index.html route loads the same UI', async ({ page }) => {
  await page.goto(`${baseUrl}/index.html`, { waitUntil: 'domcontentloaded' });
  await waitForDashboard(page);
  await expect(page.locator('#running')).toHaveText(/^(空闲|运行中)$/);
});

test('trigger and reset update the UI through AJAX', async ({ page }) => {
  await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded' });
  await waitForDashboard(page);

  await page.getByRole('button', { name: '重置' }).click();
  await expect(page.locator('#level')).toHaveText('0');
  await expect(page.locator('#running')).toHaveText('空闲');

  await page.getByRole('button', { name: '触发 +1' }).click();
  await expect(page.locator('#level')).toHaveText('1');
  await expect(page.locator('#running')).toHaveText('运行中');

  await page.getByRole('button', { name: '重置' }).click();
  await expect(page.locator('#level')).toHaveText('0');
  await expect(page.locator('#running')).toHaveText('空闲');
});
