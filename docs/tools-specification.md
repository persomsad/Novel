# Tools Specification

Novel Agent 的核心工具规格说明。

## 概述

Novel Agent 提供 5 个核心工具，Agent 可以根据需要自主选择和组合使用。

## 工具列表

### 1. read_file - 读取文件

**用途**：读取任意文本文件内容

**函数签名**：
```python
def read_file(path: str) -> str
```

**参数**：
- `path` (str): 文件路径（相对或绝对）

**返回**：
- `str`: 文件内容（UTF-8 编码）

**异常**：
- `FileNotFoundError`: 文件不存在
- `PermissionError`: 无读取权限

**使用场景**：
- 读取角色设定文件
- 读取已有章节
- 读取大纲或世界观设定

**示例**：
```python
# 读取角色档案
content = read_file("spec/knowledge/character-profiles.md")

# 读取第1章
chapter = read_file("chapters/ch001.md")
```

---

### 2. write_chapter - 创建章节

**用途**：创建新的章节文件

**函数签名**：
```python
def write_chapter(number: int, content: str, base_dir: str = "chapters") -> str
```

**参数**：
- `number` (int): 章节编号（1-999）
- `content` (str): 章节内容
- `base_dir` (str, 可选): 章节目录，默认 "chapters"

**返回**：
- `str`: 创建的文件路径（如 "chapters/ch001.md"）

**异常**：
- `ValueError`: 章节编号无效（<1 或 >999）
- `OSError`: 文件系统错误

**使用场景**：
- 创建新章节
- 按照用户要求生成内容

**示例**：
```python
# 创建第1章
file_path = write_chapter(1, "# 第一章\n\n李明走进咖啡馆...")

# 创建第10章
write_chapter(10, "# 第十章\n\n...")
```

**文件命名规则**：
- 章节编号自动补零：ch001.md, ch002.md, ..., ch999.md
- 自动创建目录（如果不存在）

---

### 3. search_content - 搜索内容

**用途**：在指定目录搜索关键词

**函数签名**：
```python
def search_content(keyword: str, search_dir: str = ".") -> list[dict[str, str]]
```

**参数**：
- `keyword` (str): 搜索关键词（字面字符串匹配）
- `search_dir` (str, 可选): 搜索目录，默认当前目录

**返回**：
- `list[dict]`: 匹配结果列表，每个结果包含：
  - `file` (str): 文件路径
  - `line` (str): 行号
  - `content` (str): 匹配的行内容

**使用场景**：
- 查找角色名称出现的位置
- 搜索关键情节
- 查找时间标记或引用标记

**示例**：
```python
# 搜索角色名
results = search_content("李明", "chapters")
# => [{"file": "chapters/ch001.md", "line": "5", "content": "李明走进咖啡馆"}]

# 搜索时间标记
results = search_content("[TIME:", "chapters")
# => [{"file": "chapters/ch002.md", "line": "10", "content": "- [TIME:2024-01-15] 早上"}]
```

**实现细节**：
- 优先使用 ripgrep（如果已安装）
- 自动回退到 Python 实现
- 只搜索 `.md` 文件

---

### 4. verify_strict_timeline - 时间线精确验证

**用途**：验证时间线的数字一致性（脚本验证）

**函数签名**：
```python
def verify_strict_timeline() -> dict[str, list[str]]
```

**返回**：
- `dict`: 验证结果
  - `errors` (list): 错误列表
  - `warnings` (list): 警告列表

**使用场景**：
- 验证"第X天"的数字连续性
- 检查日期格式正确性
- 发现数字跳跃或倒序

**示例**：
```python
result = verify_strict_timeline()
# => {
#     "errors": ["第2章时间线跳跃：第1天 → 第3天"],
#     "warnings": []
# }
```

**注意**：
- 这是**精确脚本验证**，不是 Agent 推理
- 检查数字和日期格式，不检查语义
- Agent 应该先用推理做语义检查

---

### 5. verify_strict_references - 引用完整性验证

**用途**：验证引用 ID 的完整性（脚本验证）

**函数签名**：
```python
def verify_strict_references() -> dict[str, list[str]]
```

**返回**：
- `dict`: 验证结果
  - `errors` (list): 错误列表（引用不存在）
  - `warnings` (list): 警告列表（未使用的伏笔）

**使用场景**：
- 检查 `[REF:xxx]` 引用是否存在
- 发现悬空引用
- 发现未使用的伏笔

**示例**：
```python
result = verify_strict_references()
# => {
#     "errors": ["第10章引用 [REF:mystery-box] 不存在"],
#     "warnings": ["伏笔 [SETUP:clue-01] 未被引用"]
# }
```

**注意**：
- 这是**精确脚本验证**，检查 ID 匹配
- 不检查引用的语义合理性
- Agent 应该先用推理做语义检查

---

## 工具设计原则

### 1. Agent 推理优先

**核心理念**：Agent 通过推理能力完成大部分检查，无需专门工具。

```
❌ 错误方式：为每种检查提供专门工具
- check_character_consistency()
- check_plot_logic()
- check_worldview()
...（7+ 工具）

✅ 正确方式：让 Agent 用推理 + 基础工具
- Agent 读取设定 (read_file)
- Agent 读取章节 (read_file)
- Agent 自己推理对比
- Agent 发现矛盾
```

### 2. 脚本用于精确验证

**使用场景**：需要精确计算或 ID 匹配时

```
Agent 推理：语义层面
- "角色性格前后矛盾"
- "情节逻辑不合理"
- "时间线不符合常识"

脚本验证：精确层面
- verify_strict_timeline(): 数字连续性
- verify_strict_references(): ID 完整性
```

### 3. 工具保持简单

**特点**：
- 每个工具只做一件事
- 参数尽量少
- 返回值简单
- 易于理解和组合

---

## 工具组合示例

### 场景 1：检查角色一致性

```
用户："检查第3章角色是否一致"

Agent 推理过程：
1. read_file("spec/knowledge/character-profiles.md")  # 读取设定
2. read_file("chapters/ch003.md")  # 读取章节
3. [推理对比] → 发现矛盾
4. 返回详细报告 + 修复建议
```

### 场景 2：创建新章节

```
用户："创建第5章，讲述主角的第一次战斗"

Agent 推理过程：
1. read_file("spec/outline.md")  # 了解大纲
2. read_file("chapters/ch004.md")  # 了解上一章结尾
3. [推理生成内容]
4. write_chapter(5, content)  # 创建章节
```

### 场景 3：查找角色出现位置

```
用户："李明在哪些章节出现过？"

Agent 推理过程：
1. search_content("李明", "chapters")  # 搜索
2. [整理结果]
3. 返回："李明在第1、3、5章出现"
```

### 场景 4：完整一致性检查

```
用户："全面检查一致性"

Agent 推理过程：
1. [语义检查 - Agent 推理]
   - read_file() 读取所有设定
   - read_file() 读取所有章节
   - 推理发现语义矛盾

2. [精确检查 - 脚本验证]
   - verify_strict_timeline()  # 时间线数字
   - verify_strict_references()  # 引用ID

3. 综合报告
```

---

## 错误处理

所有工具都遵循一致的错误处理模式：

### 1. 明确的异常类型

```python
try:
    content = read_file("nonexistent.md")
except FileNotFoundError:
    print("文件不存在")
except PermissionError:
    print("无权限读取")
```

### 2. 友好的错误消息

```
❌ 错误：Exception: Error code 2
✅ 正确：FileNotFoundError: 文件不存在: chapters/ch999.md
```

### 3. 日志记录

所有工具操作都会记录日志：
- DEBUG：详细操作步骤
- INFO：成功完成的操作
- WARNING：非致命问题
- ERROR：失败的操作

---

## 性能考虑

### 1. read_file
- 适用于小文件（<10MB）
- 大文件建议分块读取或搜索

### 2. search_content
- ripgrep 性能优异（100MB 文件 <100ms）
- Python fallback 较慢但足够

### 3. write_chapter
- 同步写入，立即返回
- 自动创建目录

### 4. verify_* 工具
- 需要扫描所有文件
- 适合批量检查，不适合频繁调用

---

## 扩展性

### 未来可能添加的工具

**v0.2.0**:
- `export_to_pdf()` - 导出为 PDF
- `export_to_epub()` - 导出为 EPUB
- `analyze_character_arc()` - 角色弧分析

**v1.0.0**:
- `generate_summary()` - 生成章节摘要
- `translate_chapter()` - 翻译章节
- `check_grammar()` - 语法检查

### 工具添加原则

只在以下情况添加新工具：
1. **Agent 无法通过推理完成**
2. **需要外部 API 或工具**（如 PDF 生成）
3. **性能关键**（如大规模数据处理）

---

## 总结

| 工具 | 用途 | 类型 | 复杂度 |
|------|------|------|--------|
| read_file | 读取文件 | 基础 | 简单 |
| write_chapter | 创建章节 | 基础 | 简单 |
| search_content | 搜索内容 | 基础 | 中等 |
| verify_strict_timeline | 时间线验证 | 验证 | 中等 |
| verify_strict_references | 引用验证 | 验证 | 中等 |

**核心思想**：工具简单，Agent 智能。让 Agent 的推理能力充分发挥，工具只提供必要的支持。
