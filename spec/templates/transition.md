---
name: 场景过渡模板
category: transition
description: 用于场景转换（时间/空间切换）
variables:
  - transition_type: 过渡类型（time/space/perspective）
  - time_gap: 时间间隔（如"三天后"、"次日清晨"）
  - from_location: 起始地点
  - to_location: 目标地点
  - character: 角色名称
  - activity: 过渡期间的活动（可选）
---

## 时间过渡

${time_gap}，${activity}

---

## 空间过渡

离开${from_location}后，${character}${activity}，来到了${to_location}。

---

## 视角切换

镜头一转，${to_location}。

---

**使用示例（时间过渡）**：

```bash
novel-agent template apply transition \
  --var transition_type="time" \
  --var time_gap="三天后" \
  --var activity="张三终于完成了闭关修炼，实力再次突破"
```

**输出示例**：

```
三天后，张三终于完成了闭关修炼，实力再次突破。
```

**使用示例（空间过渡）**：

```bash
novel-agent template apply transition \
  --var transition_type="space" \
  --var from_location="城主府" \
  --var to_location="张家后院" \
  --var character="张三" \
  --var activity="穿过繁华的街市"
```

**输出示例**：

```
离开城主府后，张三穿过繁华的街市，来到了张家后院。
```
