---
name: 对话模板
category: dialogue
description: 用于描写角色对话，包含动作、表情和心理活动
variables:
  - character: 角色名称
  - emotion: 情绪（如"愤怒"、"悲伤"、"喜悦"）
  - action: 动作描写（如"紧握双拳"）
  - expression: 表情描写（如"眉头紧皱"）
  - dialogue: 对话内容
  - psychology: 心理活动（可选）
---

${character}${expression}，${action}，${emotion}地说道："${dialogue}"

${psychology}

---

**使用示例**：

```bash
novel-agent template apply dialogue \
  --var character="张三" \
  --var emotion="愤怒" \
  --var action="猛地一拍桌子" \
  --var expression="双目圆睁" \
  --var dialogue="你竟敢欺骗我！" \
  --var psychology="他心中怒火中烧，恨不得立刻将对方碎尸万段。"
```

**输出示例**：

```
张三双目圆睁，猛地一拍桌子，愤怒地说道："你竟敢欺骗我！"

他心中怒火中烧，恨不得立刻将对方碎尸万段。
```
