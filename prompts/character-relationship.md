---
description: 分析角色关系
usage: novel-agent chat -f prompts/character-relationship.md --var CHARACTER=张三
---

请分析角色 ${CHARACTER} 的关系网络：

1. **直接关系**：与哪些角色有直接关系？（认识、朋友、敌人、亲人等）
2. **关系变化**：这些关系在故事中如何发展？
3. **间接关系**：通过其他角色，还能联系到哪些人？
4. **社交地位**：在角色网络中的重要程度？

请使用 `build_character_network` 工具来辅助分析。
