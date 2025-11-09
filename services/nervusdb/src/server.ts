import Fastify from "fastify";
import { z } from "zod";

import { loadConfig } from "./config.js";
import { NervusGateway } from "./gateway.js";

const factsSchema = z.object({
  facts: z.array(
    z.object({
      subject: z.string(),
      predicate: z.string(),
      object: z.string(),
      properties: z.record(z.any()).optional(),
    }),
  ),
});

const timelineSchema = z.object({
  entityId: z.number().optional(),
  predicateKey: z.string().optional(),
  role: z.string().optional(),
  limit: z.number().optional(),
});

const cypherSchema = z.object({
  query: z.string(),
  params: z.record(z.any()).optional(),
});

export async function startServer(configPath?: string) {
  const config = loadConfig(configPath);
  const gateway = new NervusGateway(config);
  const app = Fastify({ logger: true });

  app.get("/health", async () => ({ status: "ok" }));

  app.post("/facts/ingest", async (request, reply) => {
    const body = factsSchema.parse(request.body);
    const count = await gateway.ingestFacts(body.facts);
    reply.send({ ok: true, count });
  });

  app.post("/timeline/query", async (request, reply) => {
    const body = timelineSchema.parse(request.body);
    const result = await gateway.timeline({
      entity_id: body.entityId,
      predicate_key: body.predicateKey,
      role: body.role,
      limit: body.limit,
    } as any);
    reply.send({ ok: true, result });
  });

  app.post("/graph/query", async (request, reply) => {
    const body = cypherSchema.parse(request.body);
    const result = await gateway.cypher(body.query, body.params);
    reply.send({ ok: true, result });
  });

  const close = async () => {
    await gateway.close();
    await app.close();
  };

  process.on("SIGINT", close);
  process.on("SIGTERM", close);

  await app.listen({ host: config.host ?? "0.0.0.0", port: config.port ?? 8787 });
  return { app, gateway };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  startServer().catch((error) => {
    console.error("Failed to start Nervus gateway", error);
    process.exit(1);
  });
}
