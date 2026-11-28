import { expect, test, type Page } from "@playwright/test";

const apiOrigin = "http://api.test";

type Role = "admin" | "participant";

async function mockAuthenticatedApi(page: Page, role: Role) {
  await page.route(`${apiOrigin}/api/v1/health`, (route) =>
    route.fulfill({ json: { status: "healthy", service: "VEILBENCH", version: "0.2.0", session_storage: "postgresql" } }),
  );
  await page.route(`${apiOrigin}/api/v1/sessions?**`, (route) =>
    route.fulfill({ json: { sessions: [], total: 0 } }),
  );
  await page.route(`${apiOrigin}/api/v1/accounts?**`, (route) =>
    route.fulfill({ json: { accounts: [], total: 0 } }),
  );
  await page.route(`${apiOrigin}/api/v1/accounts/login`, async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toMatchObject({ username: role === "admin" ? "admin" : "founder0" });
    await route.fulfill({ json: { token: `${role}-synthetic-token`, role, username: role === "admin" ? "admin" : "founder0" } });
  });
  await page.route(`${apiOrigin}/api/v1/accounts/logout`, async (route) => {
    expect(route.request().headers().authorization).toBe(`Bearer ${role}-synthetic-token`);
    await route.fulfill({ status: 200, json: {} });
  });
  if (role === "participant") {
    await page.route(`${apiOrigin}/api/v1/accounts/assignment`, async (route) => {
      expect(route.request().headers().authorization).toBe("Bearer participant-synthetic-token");
      await route.fulfill({ json: { session_id: "synthetic-session", party_id: 0, capability: "synthetic-capability" } });
    });
  }
}

async function openAccessScreen(page: Page) {
  await page.goto("/");
  await page.locator(".vanguard-start:visible, .vanguard-mobile-cta:visible").click();
  await expect(page.getByRole("heading", { name: /enter.*system/i })).toBeVisible();
}

test("public landing and access screen render at the selected viewport", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.locator(".vanguard-start:visible, .vanguard-mobile-cta:visible")).toBeVisible();
  await page.locator(".vanguard-start:visible, .vanguard-mobile-cta:visible").click();
  await expect(page.getByRole("heading", { name: /enter.*system/i })).toBeVisible();
  await expect(page.getByRole("region", { name: "Sign in" })).toBeVisible();
  await expect(page.locator("input[name=username]")).toBeVisible();
  await expect(page.locator("input[name=password]")).toBeVisible();
  expect(await page.locator("body").evaluate((body) => body.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath("access-screen.png"), fullPage: true });
});

test("administrator can sign in, load protected dashboard data, and sign out", async ({ page }) => {
  await mockAuthenticatedApi(page, "admin");
  await openAccessScreen(page);
  await page.locator("input[name=username]").fill("admin");
  await page.locator("input[name=password]").fill("AdminStrongPassword123!");
  await page.getByRole("button", { name: /access veilbench/i }).click();
  await expect(page.getByRole("navigation", { name: "Administrator navigation" })).toBeVisible();
  await expect(page.getByText(/awaiting initialization/i)).toBeVisible();
  await page.getByRole("button", { name: "SIGN OUT" }).click();
  await expect(page.getByRole("heading", { name: /enter.*system/i })).toBeVisible();
});

test("founder sign-in resolves assignment and submits only to the assigned party", async ({ page }) => {
  await mockAuthenticatedApi(page, "participant");
  await page.route("http://party0.test/sessions/synthetic-session/input", async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().headers().authorization).toBe("Bearer synthetic-capability");
    expect(route.request().postDataJSON()).toEqual({ salary: 50_000 });
    await route.fulfill({ json: { party_id: 0, input_submitted: true } });
  });
  await openAccessScreen(page);
  await page.locator("input[name=username]").fill("founder0");
  await page.locator("input[name=password]").fill("FounderStrongPassword123!");
  await page.getByRole("button", { name: /access veilbench/i }).click();
  await expect(page.getByRole("region", { name: "Private founder input" })).toBeVisible();
  await page.locator("input[name=salary]").fill("50000");
  await page.getByRole("button", { name: /seal & submit/i }).click();
  await expect(page.getByText("INPUT SEALED.")).toBeVisible();
  await expect(page.getByText(/accepted by your assigned MPC party/i)).toBeVisible();
});
