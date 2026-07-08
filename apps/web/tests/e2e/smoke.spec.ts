import { expect, test } from '@playwright/test';

test('the application shell loads and navigates', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  // Sidebar navigation works.
  await page.getByRole('link', { name: 'Cases' }).click();
  await expect(page.getByRole('heading', { name: 'Cases' })).toBeVisible();
});

test('unknown routes render the 404 page', async ({ page }) => {
  await page.goto('/does-not-exist');
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
});
