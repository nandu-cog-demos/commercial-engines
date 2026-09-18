import { expect, test } from "@playwright/test";

// NO-196 — small E2E pass over the seeded engines (see docs/sdd/NO-196-*.md, BDD-13/14/15/16/17).

test("BDD-15: engines list shows overdue badges only for engines with overdue mandatory SBs", async ({
  page,
}) => {
  await page.goto("/");
  const row = (serial: string) => page.getByRole("row").filter({ hasText: serial });

  await expect(row("TF9-001234").getByText("2 overdue")).toBeVisible();
  await expect(row("TF9-001750").getByText("1 overdue")).toBeVisible();
  for (const serial of ["TF9-002000", "TF7X-000100", "TF9-000812"]) {
    await expect(row(serial).getByText(/overdue/)).toHaveCount(0);
  }
});

test("BDD-13: TF9-001234 Compliance tab lists two overdue mandatory SBs", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "TF9-001234" }).click();
  const tab = page.getByRole("button", { name: /Compliance/ });
  await expect(tab.locator(".badge")).toHaveText("2");
  await tab.click();

  const overdueRows = page.locator("tr.overdue");
  await expect(overdueRows).toHaveCount(2);
  await expect(overdueRows.nth(0)).toContainText("TF9-72-0031");
  await expect(overdueRows.nth(1)).toContainText("TF9-73-0044");
  await expect(page.getByText("OVERDUE", { exact: true })).toHaveCount(2);
  await expect(overdueRows.nth(0)).toContainText("-2,250");
});

test("BDD-14: TF7X-000100 has no applicable service bulletins", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "TF7X-000100" }).click();
  const tab = page.getByRole("button", { name: /Compliance/ });
  await expect(tab.locator(".badge")).toHaveCount(0);
  await tab.click();
  await expect(page.getByText("No applicable service bulletins")).toBeVisible();
});

test("BDD-16: releasing TF9-001234 is blocked with the two SB numbers", async ({ page }) => {
  await page.goto("/shop-visits");
  page.once("dialog", (d) => d.accept("qa.tester"));
  const row = page.getByRole("row").filter({ hasText: "TF9-001234" });
  await row.getByRole("button", { name: "Release" }).click();

  const dialog = page.getByRole("dialog", { name: "Release blocked" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("TF9-72-0031");
  await expect(dialog).toContainText("TF9-73-0044");
  await expect(dialog).toContainText("HPT stage 1 blade retention pin inspection");
  await dialog.getByRole("button", { name: "Close" }).click();
  await expect(dialog).toBeHidden();
  await expect(row).toContainText("IN_WORK");
});

test("BDD-17: releasing TF7X-000100 (nothing applicable) succeeds", async ({ page }) => {
  await page.goto("/shop-visits");
  page.once("dialog", (d) => d.accept("qa.tester"));
  const row = page.getByRole("row").filter({ hasText: "TF7X-000100" });
  await row.getByRole("button", { name: "Release" }).click();

  await expect(row).toContainText("RELEASED");
  await expect(row).toContainText("qa.tester");
  await expect(row.getByRole("button", { name: "Release" })).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
