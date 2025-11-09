# NervusDB CLI 集成指南

> 目标：不改动 NervusDB 仓库，只通过命令行接口在 Novel Agent 中读写/查询事实与时间线。

## 1. 安装 CLI

```bash
# 建议全局安装
npm install -g @nervusdb/core

# 或者使用 npx（每次执行会下载，速度较慢）
npx --yes nervusdb stats demo.nervusdb
```

> `nervusdb` 命令来自 @nervusdb/core 包。保持 Node.js ≥ 20。

## 2. Python 调用方式

我们新增了 `src/novel_agent/nervus_cli.py`：

- `cypher_query(db_path, query, *, params=None, limit=None, format='json', readonly=True)`
  调用 `nervusdb cypher <db> --query ... --format json`，返回解析后的 JSON。
- `run_raw(command, args)`
  调用任意 Nervus CLI 子命令，返回 stdout 文本。

所有命令通过 `subprocess.run` 执行，无需在 Novel Agent 仓库添加 Node 依赖。

## 3. 配置

| 变量/参数 | 说明 | 默认值 |
|-----------|------|--------|
| `NERVUSDB_BIN` | CLI 可执行文件（支持带空格，例如 `npx --yes nervusdb`） | `nervusdb` |
| `NERVUSDB_DB_PATH` | 可选：默认数据库路径，缺省时在函数调用里显式传入 | （无） |

示例：

```bash
export NERVUSDB_BIN="npx --yes nervusdb"
export NERVUSDB_DB_PATH="$PWD/.novel-agent/memory/demo.nervusdb"
```

## 4. 查询示例

```python
from novel_agent import nervus_cli

result = nervus_cli.cypher_query(
    db_path="/data/novel/demo.nervusdb",
    query="MATCH (c:Character {name: $name})-[:APPEARS_IN]->(e:Event) RETURN c, e",
    params={"name": "李明"},
    limit=10,
)
print(result["rows"])
```

## 5. 写入 NervusDB

使用 `novel-agent memory ingest` 可以先重建连续性索引，再批量调用 Nervus CLI 写入：

```bash
poetry run novel-agent memory ingest --db data/novel.nervusdb

# 或者仅复用已有索引
poetry run novel-agent memory ingest --db data/novel.nervusdb --no-refresh
```

该命令默认：

1. 运行 `novel-agent refresh-memory`（除非 `--no-refresh`）。
2. 加载 `data/continuity/index.json`。
3. 对角色/章节/时间线/引用调用 `nervusdb cypher ... --readonly false` 批量写入。

可使用 `--dry-run` 查看统计而不实际写入数据库。

## 6. 错误处理

- CLI 返回码非 0 → 抛出 `NervusCLIError`（包含命令、 stdout、stderr）。
- JSON 解析失败 → 抛出 `ValueError`，提醒检查 `--format` 与输出。
- 若 CLI 未安装 → `FileNotFoundError`，提示用户运行 `npm i -g @nervusdb/core` 或设置 `NERVUSDB_BIN`。

## 7. 后续扩展

- `memory ingest` / `memory stats` CLI 会复用 `nervus_cli.run_raw`。
- LangChain 工具 `nervus_query` / `nervus_timeline` 将基于本模块封装，统一日志与错误处理。
- CI 中可通过 `NERVUSDB_BIN="npx --yes nervusdb"` + 下载缓存实现无状态测试。

## 8. Gateway 服务（services/nervusdb）

对于需要常驻守护进程或远程访问的场景，可以运行 Node 版 Gateway：

1. 安装依赖（需 Node ≥ 20 + pnpm）：
   ```bash
   pnpm install --filter services/nervusdb
   ```
2. 配置 `services/nervusdb/memory.config.json`（数据库路径、端口、Nervus CLI）。
3. 启动服务：
   ```bash
   pnpm --filter services/nervusdb memory:dev
   ```
   默认监听 `127.0.0.1:8787`，提供：
   - `GET /health`
   - `POST /facts/ingest`
   - `POST /timeline/query`
   - `POST /graph/query`（执行 Cypher）
4. 运维命令：
   ```bash
   pnpm --filter services/nervusdb memory:check     # 打开 DB 并跑一次时间线查询
   pnpm --filter services/nervusdb memory:compact   # 调用 Nervus CLI 执行 compact --force
   pnpm --filter services/nervusdb test             # Vitest（mock @nervusdb/core）
   ```

Gateway 内部复用 `@nervusdb/core` 打开数据库，保持与 CLI/脚本统一的数据路径。Python 仍可通过 HTTP 请求或现有 CLI Wrapper 调用，满足线上/离线两种部署模式。
