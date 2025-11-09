import type { FactInput, NervusDB, TemporalTimelineQuery } from "@nervusdb/core";
import { NervusDB as NervusCore } from "@nervusdb/core";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

import type { FactsPayload, GatewayConfig } from "./config.js";

const execFileAsync = promisify(execFile);

export class NervusGateway {
  private db: NervusDB | null = null;

  constructor(private readonly config: GatewayConfig) {}

  private async getDb(): Promise<NervusDB> {
    if (!this.db) {
      this.db = await NervusCore.open(this.config.dbPath, this.config.openOptions ?? {});
    }
    return this.db;
  }

  async ingestFacts(facts: FactsPayload[]): Promise<number> {
    const db = await this.getDb();
    for (const fact of facts) {
      const payload: FactInput = {
        subject: fact.subject,
        predicate: fact.predicate,
        object: fact.object,
        properties: fact.properties ?? {},
      };
      await db.insertFact(payload);
    }
    return facts.length;
  }

  async timeline(query: TemporalTimelineQuery) {
    const db = await this.getDb();
    return db.memory.timeline(query);
  }

  async cypher(query: string, params?: Record<string, unknown>) {
    const bin = this.config.nervusCli?.split(" ") ?? ["nervusdb"];
    const [cmd, ...rest] = bin;
    const args = [
      ...rest,
      "cypher",
      this.config.dbPath,
      "--query",
      query,
      "--format",
      "json",
    ];
    if (params && Object.keys(params).length > 0) {
      args.push("--params", JSON.stringify(params));
    }
    const { stdout } = await execFileAsync(cmd, args, { encoding: "utf8" });
    return JSON.parse(stdout || "{}");
  }

  async close(): Promise<void> {
    if (this.db) {
      await this.db.close?.();
      this.db = null;
    }
  }
}

export type NervusGatewayType = NervusGateway;
