---
name: 动作描写模板（战斗场景）
category: action
description: 用于描写战斗或激烈动作场景
variables:
  - character_a: 角色A名称
  - character_b: 角色B名称
  - action_a: 角色A的动作
  - action_b: 角色B的反应
  - result: 动作结果
  - impact: 影响描写（可选）
---

## 动作交锋

${character_a}${action_a}！

${character_b}${action_b}。

${result}

${impact}

---

**使用示例**：

```bash
novel-agent template apply action \
  --var character_a="张三" \
  --var character_b="李四" \
  --var action_a="身形一闪，剑光如电般刺向对方咽喉" \
  --var action_b="险险侧身躲过，冷汗直流" \
  --var result="剑气擦过李四的面颊，留下一道血痕。" \
  --var impact="围观众人倒吸一口凉气，张三的剑法竟已精进到如此地步！"
```

**输出示例**：

```
## 动作交锋

张三身形一闪，剑光如电般刺向对方咽喉！

李四险险侧身躲过，冷汗直流。

剑气擦过李四的面颊，留下一道血痕。

围观众人倒吸一口凉气，张三的剑法竟已精进到如此地步！
```
