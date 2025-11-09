import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@nervusdb/core", () => {
  const insertFact = vi.fn(async () => {});
  const timeline = vi.fn(async () => [{ id: 1 }]);
  return {
    NervusDB: {
      open: vi.fn(async () => ({
        insertFact,
        memory: { timeline },
        close: vi.fn(async () => {}),
      })),
    },
  };
});

import { startServer } from "./server.js";

describe("gateway server", () => {
  let stop: (() => Promise<void>) | null = null;
  beforeEach(() => {
    vi.resetModules();
  });

  it("ingests facts", async () => {
    const { app, gateway } = await startServer("memory.config.json");
    stop = async () => {
      await gateway.close();
      await app.close();
    };
    const res = await app.inject({
      method: "POST",
      url: "/facts/ingest",
      payload: {
        facts: [{ subject: "a", predicate: "b", object: "c" }],
      },
    });
    expect(res.statusCode).toBe(200);
    await stop();
  });
});
