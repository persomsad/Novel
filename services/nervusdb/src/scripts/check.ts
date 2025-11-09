import { loadConfig } from "../config.js";
import { NervusGateway } from "../gateway.js";

const main = async () => {
  const config = loadConfig();
  const gateway = new NervusGateway(config);
  await gateway.timeline({ limit: 1 } as any);
  await gateway.close();
  console.log(`✅ Nervus check passed for ${config.dbPath}`);
};

main().catch((error) => {
  console.error("❌ Nervus check failed", error);
  process.exitCode = 1;
});
