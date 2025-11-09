import { readFileSync } from "node:fs";
import path from "node:path";

export type GatewayConfig = {
  dbPath: string;
  host?: string;
  port?: number;
  nervusCli?: string;
  openOptions?: Record<string, unknown>;
};

const DEFAULT_CONFIG_PATH = path.resolve("memory.config.json");

export const loadConfig = (configPath?: string): GatewayConfig => {
  const target = configPath
    ? path.resolve(configPath)
    : process.env.NERVUS_GATEWAY_CONFIG
      ? path.resolve(process.env.NERVUS_GATEWAY_CONFIG)
      : DEFAULT_CONFIG_PATH;

  const raw = readFileSync(target, "utf8");
  const parsed = JSON.parse(raw);
  if (!parsed.dbPath) {
    throw new Error("config requires dbPath");
  }
  return {
    host: "127.0.0.1",
    port: 8787,
    nervusCli: "nervusdb",
    ...parsed,
  };
};

export type FactsPayload = {
  subject: string;
  predicate: string;
  object: string;
  properties?: Record<string, unknown>;
};
