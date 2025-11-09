---
name: 场景描写模板
category: scene
description: 用于描写场景环境、氛围和视觉细节
variables:
  - location: 地点名称（如"荒凉的战场"）
  - time: 时间（如"黄昏"、"午夜"）
  - weather: 天气（如"暴雨"、"晴空"）
  - atmosphere: 氛围（如"紧张"、"宁静"）
  - details: 视觉细节（如"残破的城墙"）
---

## 环境描写

${time}时分，${location}${weather}。

${details}

整个场景透着${atmosphere}的氛围。

---

**使用示例**：

```bash
novel-agent template apply scene-description \
  --var time="黄昏" \
  --var location="荒凉的战场上" \
  --var weather="乌云密布" \
  --var details="残破的旗帜在风中猎猎作响，地面散落着破碎的兵器。" \
  --var atmosphere="肃杀"
```

**输出示例**：

```
黄昏时分，荒凉的战场上乌云密布。

残破的旗帜在风中猎猎作响，地面散落着破碎的兵器。

整个场景透着肃杀的氛围。
```
