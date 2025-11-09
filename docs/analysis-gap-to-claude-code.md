# Novel Agent → "小说创作界的 Claude Code" 差距分析与优化路线图

**生成时间**: 2025-11-09
**目标**: 成为像 Claude Code/Cursor 一样强大的小说创作 AI 助手

---

## 📊 现状评估

### 当前架构（v0.2.0 开发中）

```
✅ 已实现：
├── ReAct Agent (LangChain + LangGraph)
├── 5 个核心工具（读取、写入、搜索、时间线验证、引用验证）
├── 多 Agent 系统（default/outline-architect/continuity-editor/style-smith）
├── 会话持久化（SqliteSaver）
├── 连续性索引（章节→角色→时间标记→引用）
├── NervusDB 集成（分布式图数据库记忆）
└── CLI 界面（typer + rich + prompt_toolkit）

📊 代码量：
- 核心代码：1,916 行（10 个模块）
- 测试代码：充足（23 个测试文件）
- 文档：完善（ADR、工具规格、使用指南）

🎯 核心能力：
- Agent 可以读取设定、创建章节、搜索内容、验证一致性
- 支持多轮对话和会话恢复
- 具备基本的记忆系统
```

---

## 🎯 Claude Code 的核心能力（对标分析）

### 1. **上下文理解 (Context Awareness)** ⭐⭐⭐⭐⭐

**Claude Code 的做法：**
- 深度理解代码库结构和依赖关系
- 自动索引所有文件、函数、类、类型
- 实时跟踪文件变更
- 智能选择相关上下文（不需要用户手动指定）

**Novel Agent 现状：** ⭐⭐⭐
- ✅ 有连续性索引（章节、角色、引用）
- ❌ 索引需要手动刷新（`refresh-memory`）
- ❌ 无法自动感知文件变更
- ❌ Agent 需要自己搜索相关信息（不够智能）

**差距：**
- 缺少实时文件监控（File Watcher）
- 缺少智能上下文选择（Context Retrieval）
- 缺少依赖关系图（章节→角色→情节）

---

### 2. **智能补全 (Intelligent Completion)** ⭐⭐⭐⭐⭐

**Claude Code 的做法：**
- 基于当前光标位置和上下文，提供精准补全
- 理解代码意图，补全完整的函数/类
- 支持多文件补全（理解跨文件依赖）

**Novel Agent 现状：** ⭐
- ❌ 无补全功能
- ❌ 只能通过对话生成整段内容
- ❌ 无法"边写边提示"

**差距：**
- 缺少编辑器集成（VSCode/Cursor Plugin）
- 缺少实时补全引擎
- 缺少光标位置感知

---

### 3. **智能编辑 (Smart Editing)** ⭐⭐⭐⭐⭐

**Claude Code 的做法：**
- 理解编辑意图（"把这个函数改成异步"）
- 多文件联动编辑（修改函数签名时更新所有调用）
- Diff 预览（显示将要修改的内容）
- 支持批量编辑和重构

**Novel Agent 现状：** ⭐⭐
- ✅ 可以创建新章节
- ❌ 无法精准修改现有内容
- ❌ 无法批量修改（例如：把所有章节的"张三"改成"李四"）
- ❌ 无 Diff 预览

**差距：**
- 缺少 Edit 工具（精准修改指定行）
- 缺少 Multi-Edit 工具（批量修改）
- 缺少 Diff 预览机制

---

### 4. **错误检测与修复 (Error Detection & Fix)** ⭐⭐⭐⭐⭐

**Claude Code 的做法：**
- 实时语法检查（LSP）
- 类型检查、Lint 检查
- 一键修复（Quick Fix）
- 智能建议（Code Actions）

**Novel Agent 现状：** ⭐⭐⭐
- ✅ 有一致性验证（时间线、引用）
- ❌ 验证结果不够精准（无行号）
- ❌ 无自动修复建议
- ❌ 只能在命令行运行（不是实时）

**差距：**
- 验证精度不够（需要精确到行/段）
- 缺少自动修复建议
- 缺少实时检查（需要手动运行 `check`）

---

### 5. **多模态能力 (Multimodal)** ⭐⭐⭐⭐⭐

**Claude Code 的做法：**
- 代码 + 图片 + 文档
- 可以看截图、理解设计稿
- 生成代码 + 图表 + 文档

**Novel Agent 现状：** ⭐
- ❌ 仅支持文本
- ❌ 无法处理角色设计图、场景插画
- ❌ 无法生成思维导图、关系图

**差距：**
- 缺少多模态输入（图片、音频）
- 缺少可视化输出（关系图、时间线图）

---

### 6. **协作能力 (Collaboration)** ⭐⭐⭐⭐⭐

**Claude Code 的做法：**
- Git 集成（自动 commit、PR、diff）
- 团队协作（多人共享上下文）
- Code Review 辅助

**Novel Agent 现状：** ⭐⭐
- ✅ 基于 Git 的文件管理
- ❌ 无自动 commit
- ❌ 无协作功能

**差距：**
- 缺少 Git 自动化
- 缺少协作功能

---

### 7. **性能与体验 (Performance & UX)** ⭐⭐⭐⭐⭐

**Claude Code 的做法：**
- 毫秒级响应（补全）
- 流式输出（实时看到生成过程）
- 优雅的 UI/UX
- 丰富的快捷键

**Novel Agent 现状：** ⭐⭐⭐
- ✅ 流式输出（Rich 支持）
- ✅ 键盘输入修复完成
- ❌ 响应速度取决于 LLM（5-20秒）
- ❌ UI 简陋（纯命令行）

**差距：**
- 响应速度慢（受限于 LLM API）
- UI 体验不够好
- 缺少可视化界面

---

## 🚀 优化路线图（按优先级）

### **Phase 1: 核心体验提升（P0 - 立即实施）**

#### 1.1 实时上下文理解 ⭐⭐⭐⭐⭐

**目标：** Agent 自动选择相关上下文，不需要用户手动搜索

**实现方案：**
```python
# 新增 context_manager.py
class ContextManager:
    def get_relevant_context(self, query: str) -> dict:
        """根据查询智能选择相关上下文"""
        # 1. 语义搜索：使用 embedding 找到相关章节/设定
        # 2. 依赖分析：找到相关角色、地点、道具
        # 3. 时间线过滤：只返回时间线相关的内容
        # 4. 优先级排序：最相关的放前面
        pass
```

**技术栈：**
- Embedding: Google Gemini Embedding API
- 向量数据库: ChromaDB 或 直接用 NervusDB
- 缓存: 索引结果缓存

**工作量：** 3-5 天

---

#### 1.2 精准编辑能力 ⭐⭐⭐⭐⭐

**目标：** 像 Claude Code 一样精准修改文件，而不是重写整个文件

**实现方案：**
```python
# 新增 edit 工具
@tool
def edit_file(
    path: str,
    old_str: str,  # 要替换的文本
    new_str: str,  # 新文本
    line_number: int | None = None  # 可选：指定行号
) -> str:
    """精准修改文件内容（Find & Replace）"""
    pass

# 新增 multi_edit 工具
@tool
def multi_edit(
    operations: list[dict]  # [{"file": "ch001.md", "old": "...", "new": "..."}]
) -> str:
    """批量修改多个文件"""
    pass
```

**工作量：** 2-3 天

---

#### 1.3 自动修复建议 ⭐⭐⭐⭐⭐

**目标：** 验证脚本不仅报错，还给出修复建议

**实现方案：**
```python
def verify_strict_timeline(...) -> dict:
    return {
        "errors": [
            {
                "file": "chapters/ch002.md",
                "line": 42,
                "type": "timeline_inconsistency",
                "message": "时间倒退：前一章是 2077-03-15，此处是 2077-03-10",
                "suggestion": "将 [TIME:2077-03-10] 改为 [TIME:2077-03-16] 或更晚"
            }
        ],
        "warnings": [...],
        "auto_fix": True  # 是否支持自动修复
    }
```

**工作量：** 2-3 天

---

### **Phase 2: 编辑器集成（P1 - 下一版本）**

#### 2.1 VSCode 插件 ⭐⭐⭐⭐⭐

**目标：** 在编辑器中直接使用 Novel Agent

**功能：**
- 右键菜单："用 Agent 续写这一段"
- 侧边栏：角色列表、时间线、引用检查
- 实时提示：输入角色名时自动补全
- Inline Diff：修改预览

**技术栈：**
- VSCode Extension API
- Language Server Protocol (LSP)
- WebSocket 通信（连接本地 Agent 服务）

**参考：** Gemini CLI 的 vscode-ide-companion

**工作量：** 2-3 周

---

#### 2.2 LSP 服务器 ⭐⭐⭐⭐

**目标：** 提供语言服务器，支持任何编辑器（VSCode/Vim/Emacs）

**功能：**
- Hover：悬停角色名显示设定
- Go to Definition：跳转到角色/地点定义
- Find References：查找角色在哪些章节出现
- Diagnostics：实时一致性检查

**工作量：** 2-3 周

---

### **Phase 3: 智能增强（P1 - 体验提升）**

#### 3.1 流式编辑 ⭐⭐⭐⭐

**目标：** 生成内容时逐字显示，而不是等全部生成完

**现状：** Agent 已经支持流式输出（LangChain 的 streaming）

**改进：** 优化 CLI 显示效果

**工作量：** 1-2 天

---

#### 3.2 智能提示系统 ⭐⭐⭐⭐

**目标：** 像 GitHub Copilot 一样提供写作建议

**功能：**
- 写到一半自动建议后续内容
- 角色对话自动补全（根据角色性格）
- 场景描写建议（根据世界设定）

**技术方案：**
```python
@tool
def get_writing_suggestions(
    current_text: str,
    cursor_position: int,
    context: dict
) -> list[str]:
    """根据当前内容和光标位置，提供写作建议"""
    pass
```

**工作量：** 1 周

---

#### 3.3 可视化面板 ⭐⭐⭐⭐

**目标：** 提供 Web UI，可视化展示项目结构

**功能：**
- 角色关系图（力导向图）
- 时间线可视化（Gantt 图）
- 章节大纲树状图
- 引用网络图

**技术栈：**
- 后端：FastAPI
- 前端：React + D3.js / Cytoscape.js
- 通信：WebSocket

**工作量：** 2-3 周

---

### **Phase 4: 高级能力（P2 - 差异化竞争）**

#### 4.1 多模态创作 ⭐⭐⭐⭐

**功能：**
- 上传角色设计图 → 自动提取特征描述
- 上传场景照片 → 自动生成场景描述
- 生成思维导图、关系图

**工作量：** 1-2 周

---

#### 4.2 智能大纲生成 ⭐⭐⭐⭐

**目标：** 根据题材、类型、字数，自动生成完整大纲

**功能：**
```bash
novel-agent outline generate \
  --genre "玄幻" \
  --target-words 100000 \
  --themes "复仇,成长" \
  --style "爽文"
```

**输出：**
- 完整的三幕结构大纲
- 角色设定
- 世界观设定
- 章节列表

**工作量：** 1 周

---

#### 4.3 协作写作 ⭐⭐⭐

**功能：**
- 多人协作（实时同步）
- Git 自动化（自动 commit、PR、合并）
- 版本对比（章节版本历史）

**工作量：** 2-3 周

---

## 🎯 **关键差距总结**

| 能力 | Claude Code | Novel Agent | 差距 | 优先级 |
|------|-------------|-------------|------|--------|
| **上下文理解** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 智能上下文选择 | P0 |
| **智能补全** | ⭐⭐⭐⭐⭐ | ⭐ | 实时补全引擎 | P1 |
| **精准编辑** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Edit/Multi-Edit | P0 |
| **错误检测** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 自动修复建议 | P0 |
| **多模态** | ⭐⭐⭐⭐⭐ | ⭐ | 图片/音频支持 | P2 |
| **协作** | ⭐⭐⭐⭐⭐ | ⭐⭐ | 多人协作 | P2 |
| **性能** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 响应速度 | P1 |
| **UI/UX** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 编辑器集成 | P1 |

---

## 🏆 **立即可以做的优化（Quick Wins）**

### 1. **实时文件监控** (1 天)

```python
# 使用 watchdog 监控文件变更
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChapterWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            # 自动刷新索引
            build_continuity_index()
```

**收益：** 索引始终最新，Agent 不会读到过时的数据

---

### 2. **智能上下文检索** (2-3 天)

```python
@tool
def smart_context_retrieval(query: str, max_chunks: int = 5) -> str:
    """根据查询智能检索相关上下文"""
    # 1. Embedding 语义搜索
    # 2. 关键词搜索（角色名、地名）
    # 3. 时间线过滤
    # 4. 返回最相关的前 N 个片段
    pass
```

**收益：** Agent 自动找到相关信息，不需要用户指定

---

### 3. **精准编辑工具** (2-3 天)

```python
@tool
def edit_chapter(
    chapter: int,
    search: str,
    replace: str,
    occurrence: int | None = None  # None=全部替换
) -> str:
    """精准修改章节内容"""
    pass

@tool
def insert_at_line(
    file: str,
    line_number: int,
    content: str
) -> str:
    """在指定行插入内容"""
    pass
```

**收益：** 可以精准修改，不需要重写整个文件

---

### 4. **自动修复建议** (2 天)

```python
# 增强 verify_strict_timeline
def verify_strict_timeline(...) -> dict:
    errors = []
    for error in detected_errors:
        error["suggestion"] = generate_fix_suggestion(error)
        error["auto_fix_code"] = generate_fix_code(error)
    return {"errors": errors}

# 新增自动修复命令
@app.command()
def fix(issue_id: str):
    """自动修复一致性问题"""
    # 读取问题 → 应用修复 → 验证
    pass
```

**收益：** 用户可以一键修复问题

---

### 5. **命令历史和自动补全** (1 天)

```python
# 使用 prompt_toolkit 的高级功能
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

session = PromptSession(
    history=FileHistory('.novel-agent/history'),
    auto_suggest=AutoSuggestFromHistory(),
)
```

**收益：** 更好的输入体验

---

## 📈 **推荐实施顺序（v0.3.0）**

### **第一周：核心能力补齐**

1. ✅ **精准编辑工具** (edit_chapter, insert_at_line, multi_edit)
2. ✅ **自动修复建议** (增强验证脚本)
3. ✅ **智能上下文检索** (embedding + 语义搜索)

### **第二周：体验提升**

4. ✅ **实时文件监控** (watchdog)
5. ✅ **命令历史和自动补全** (prompt_toolkit 高级功能)
6. ✅ **流式编辑优化** (实时显示)

### **第三周（可选）：编辑器集成**

7. 🔲 **VSCode 插件** (基础版)
   - 右键菜单集成
   - 侧边栏显示

---

## 💡 **核心突破点**

要成为"小说创作界的 Claude Code"，需要在以下 3 个方面突破：

### 1. **上下文智能 > 工具丰富**
- 不是工具多就好，而是 Agent 能自动找到相关信息
- 投入：智能检索 + 依赖分析

### 2. **精准编辑 > 全量生成**
- 用户不想重写整章，只想改一段话
- 投入：Edit 工具 + Diff 预览

### 3. **实时反馈 > 命令式执行**
- 用户想边写边看到提示，而不是写完再检查
- 投入：编辑器集成 + LSP

---

## 🎯 **下一步行动**

建议创建 **v0.3.0 Milestone**，包含以下 P0 Issue：

1. **#XX: 实现精准编辑工具（edit_chapter, insert_at_line）**
2. **#XX: 增强验证脚本（输出行号 + 修复建议）**
3. **#XX: 智能上下文检索（embedding + 语义搜索）**
4. **#XX: 实时文件监控（watchdog）**
5. **#XX: 命令历史和自动补全（prompt_toolkit 高级功能）**

**预计时间：** 2-3 周
**预期效果：** 体验接近 Claude Code 的 50-60%

---

## 🔮 **长期愿景（v1.0.0）**

最终目标：
- 📝 **智能写作伙伴**：理解你的风格，提供精准建议
- 🔍 **全知全能**：记住所有设定，永不遗忘
- ⚡ **极速响应**：秒级补全，实时检查
- 🎨 **多模态创作**：图片、音频、视频全支持
- 👥 **协作友好**：多人共创，版本管理
- 🌐 **跨平台**：CLI + VSCode + Web + 移动端

---

**思考：你觉得哪些功能最重要？我们可以先聚焦在最有价值的 2-3 个功能上。**
