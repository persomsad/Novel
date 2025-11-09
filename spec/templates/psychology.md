---
name: 心理描写模板
category: psychology
description: 用于描写角色内心活动和心理变化
variables:
  - character: 角色名称
  - trigger: 触发事件
  - emotion: 情绪变化
  - thought: 内心想法
  - decision: 最终决定（可选）
---

${trigger}

${character}心中${emotion}。

"${thought}"${character}暗自想道。

${decision}

---

**使用示例**：

```bash
novel-agent template apply psychology \
  --var character="张三" \
  --var trigger="看着师父的遗物，往事涌上心头。" \
  --var emotion="悲痛交加，却又夹杂着一丝坚定" \
  --var thought="师父，我一定会为您报仇，将那些叛徒一个个找出来！" \
  --var decision="他紧紧握住手中的令牌，眼中闪过一道寒光。"
```

**输出示例**：

```
看着师父的遗物，往事涌上心头。

张三心中悲痛交加，却又夹杂着一丝坚定。

"师父，我一定会为您报仇，将那些叛徒一个个找出来！"张三暗自想道。

他紧紧握住手中的令牌，眼中闪过一道寒光。
```
