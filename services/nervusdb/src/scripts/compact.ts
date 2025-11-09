import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { loadConfig } from "../config.js";

const execFileAsync = promisify(execFile);

const main = async () => {
  const config = loadConfig();
  const bin = config.nervusCli?.split(" ") ?? ["nervusdb"];
  const [cmd, ...rest] = bin;
  const args = [...rest, "compact", config.dbPath, "--force"];
  await execFileAsync(cmd, args, { stdio: "inherit" });
  console.log("✅ Nervus compact completed");
};

main().catch((error) => {
  console.error("❌ Nervus compact failed", error);
  process.exitCode = 1;
});
