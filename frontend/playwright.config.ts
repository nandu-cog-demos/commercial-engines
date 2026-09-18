import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Each run gets a fresh SQLite file so the release scenario is repeatable.
const dbPath = join(mkdtempSync(join(tmpdir(), "ce-e2e-")), "compliance.db");
const backendPort = 8001;
const frontendPort = 5174;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${frontendPort}`,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `cd ../backend && . .venv/bin/activate && uvicorn app.main:app --port ${backendPort}`,
      url: `http://localhost:${backendPort}/api/v1/health`,
      env: { DATABASE_URL: `sqlite:///${dbPath}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npx vite --port ${frontendPort} --strictPort`,
      url: `http://localhost:${frontendPort}`,
      env: { VITE_API_TARGET: `http://localhost:${backendPort}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
