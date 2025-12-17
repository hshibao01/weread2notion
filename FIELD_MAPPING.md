# Notion 数据库字段对应关系

本文档详细说明了代码中使用的字段与 Notion 数据库实际字段的对应关系。

## 📚 书籍数据库 (BOOK_DATABASE_ID)

**数据库ID**: `2bbdd161f4eb81e596d4c922546f1086`  
**数据源URL**: `collection://2bbdd161-f4eb-8186-a76d-000b09f5ad17`

### 字段对应关系

| 代码字段 | Notion字段名 | 字段类型 | 数据来源 | 状态 |
|---------|------------|---------|---------|------|
| `book_name` | **名称** | title | 微信读书书籍标题 | ✅ 已匹配 |
| `author` | **书籍作者** | text | 微信读书作者信息 | ✅ 已匹配 |
| `intro` | **书籍简介** | text | 微信读书书籍简介 | ✅ 已匹配 |
| `book_id` | **书籍ID** | text | 微信读书书籍ID | ✅ 已匹配 |
| `isbn` | **ISBN** | text | 微信读书ISBN | ✅ 已匹配 |
| `weread_url` | **书籍链接** | url | 构建的微信读书链接 | ✅ 已匹配 |
| `cover` | **书籍封面** | file | 微信读书封面图片 | ✅ 已匹配 |
| `rating` | **豆瓣评分** | number | 微信读书评分（0-10分制） | ✅ 已匹配 |
| `marked_status` | **状态** | status | 阅读状态 | ✅ 已匹配 |
| `datetime.now()` | **添加日期** | date | 当前日期 | ✅ 已匹配 |
| `finishedDate` | **读完日期** | date | 微信读书完成日期 | ✅ 已匹配 |
| `percentage` | **阅读进度** | number | 微信读书阅读进度（0-1，百分比格式） | ✅ 已匹配 |

### 状态字段选项

- **计划阅读** (to_do) - 默认状态
- **正在阅读** (in_progress) - `markedStatus > 0`
- **已经读完** (complete) - `markedStatus == 4`

### 数据库中的其他字段（代码未使用）

- NPC (relation)
- 主题月 (relation)
- 作者 (formula) - 公式字段
- 信息 (relation) - 反向关联到信息数据库
- 小红花 (formula)
- 已读章数 (number)
- 总章数 (number)
- 打卡 (relation)
- 打卡次数 (rollup)
- 技能 (relation)
- 是本月？ (formula)
- 本月小红花 (formula)
- 每日回顾 (relation)
- 添加打卡 (button)
- 笔记 (relation) - 反向关联到笔记数据库
- 简介 (formula)
- 自定义奖励数 (number)
- 解决问题 (relation)
- 评分 (formula)
- 读完了 (button)
- 进度 (formula) - 公式字段

---

## 📝 笔记数据库 (NOTE_DATABASE_ID)

**数据库ID**: `2bbdd161f4eb813fa96deee0a105c004`  
**数据源URL**: `collection://2bbdd161-f4eb-811b-a16a-000b87a9fd3b`

### 字段对应关系

| 代码字段 | Notion字段名 | 字段类型 | 数据来源 | 状态 |
|---------|------------|---------|---------|------|
| `note_content` | **名称** | title | 笔记完整内容 | ✅ 已匹配 |
| `datetime.now()` | **日期** | date | 当前日期 | ✅ 已匹配 |
| `"文献笔记"` | **分类** | status | 固定值"文献笔记" | ✅ 已匹配 |
| `book_page_id` | **书籍** | relation | 关联到书籍数据库 | ✅ 已匹配 |

### 分类字段选项

- **灵感笔记** (to_do) - 紫色
- **文献笔记** (in_progress) - 绿色 ✅ 代码使用
- **项目笔记** (in_progress) - 蓝色
- **永久笔记** (complete) - 粉色

### 数据库中的其他字段（代码未使用）

- NPC (relation)
- 上次复习时间 (rollup)
- 主题月 (relation)
- 学习信息 (relation)
- 复习间隔 (select)
- 双链笔记 (relation)
- 复习 (button)
- 复习小红花 (rollup)
- 复习提醒 (formula)
- 复习次数 (formula)
- 卡片标签 (formula)
- 标签 (multi_select)
- 技能 (relation)
- 影视 (relation)
- 是今天？ (formula)
- 是本月？ (formula)
- 本月小红花 (formula)
- 本月获得 (rollup)
- 每日回顾 (relation)
- 笔记复习次数 (rollup)
- 笔记复习记录 (relation)
- 精力 (formula)
- 萌友 (rollup)
- 解决问题 (relation)
- 辅助关卡 (relation)
- 随机数 (formula)
- 颜色 (formula)
- 小红花 (formula)
- 小红花1 (formula)

---

## 📋 信息数据库 (INFO_DATABASE_ID)

**数据库ID**: `2bbdd161f4eb8141bf2ee02d3a908745`  
**数据源URL**: `collection://2bbdd161-f4eb-8101-9bfd-000b703c3623`

### 字段对应关系

| 代码字段 | Notion字段名 | 字段类型 | 数据来源 | 状态 |
|---------|------------|---------|---------|------|
| `highlight_text` | **名称** | title | 划线完整内容 | ✅ 已匹配 |
| `"摘抄"` | **类型** | select | 固定值"摘抄" | ✅ 已匹配 |
| `"收集"` | **状态** | status | 固定值"收集" | ✅ 已匹配 |
| `book_url` | **网址** | url | 微信读书链接 | ✅ 已匹配 |
| `datetime.now()` | **创建日期** | date | 当前日期 | ✅ 已匹配 |
| `note_page_ids` | **笔记** | relation | 关联到笔记数据库 | ✅ 已匹配 |
| `book_page_id` | **书籍** | relation | 关联到书籍数据库 | ✅ 已匹配 |

### 类型字段选项

- **文章** (pink)
- **视频** (orange)
- **播客** (red)
- **政策** (brown)
- **摘抄** (green) ✅ 代码使用

### 状态字段选项

- **收集** (to_do) ✅ 代码使用
- **参考** (in_progress)
- **归档** (complete)

### 数据库中的其他字段（代码未使用）

- NPC (relation)
- colour (rollup)
- 专注 (relation)
- 主题月 (relation)
- 信息源 (relation)
- 分钟 (formula)
- 完成时间 (date)
- 完成阅读 (button)
- 小时 (formula)
- 小红花 (formula)
- 开始时间 (date)
- 开始阅读 (button)
- 情绪 (rollup)
- 情绪记录 (relation)
- 技能 (relation)
- 技能/类型 (formula)
- 时间概述 (formula)
- 是今天？ (formula)
- 是本月？ (formula)
- 本月小红花 (formula)
- 每日回顾 (relation)
- 添加笔记 (button)
- 精力 (formula)
- 自定义奖励数 (number)
- 萌友 (rollup)
- 解决 (formula)
- 解决问题 (relation)
- 辅助关卡 (relation)
- 阅读用时 (formula)
- 颜色 (formula)

---

## 🔗 数据库关联关系

### 书籍 ↔ 笔记
- **书籍数据库** → `笔记` (relation) → **笔记数据库**
- **笔记数据库** → `书籍` (relation) → **书籍数据库**

### 书籍 ↔ 信息
- **书籍数据库** → `信息` (relation) → **信息数据库**
- **信息数据库** → `书籍` (relation) → **书籍数据库**

### 笔记 ↔ 信息
- **信息数据库** → `笔记` (relation) → **笔记数据库**
- **笔记数据库** → `学习信息` (relation) → **信息数据库**

---

## ✅ 验证结果

### 匹配状态
- ✅ **书籍数据库**: 所有使用的字段都已匹配
- ✅ **笔记数据库**: 所有使用的字段都已匹配
- ✅ **信息数据库**: 所有使用的字段都已匹配

### 修复内容
1. ✅ 添加了 **ISBN** 字段到书籍数据库的插入和更新函数中
2. ✅ 所有字段名称与 Notion 数据库完全匹配
3. ✅ 所有字段类型与 Notion 数据库完全匹配
4. ✅ 所有状态选项值与 Notion 数据库完全匹配

---

## 📊 代码修改总结

### 修改的函数

1. **`insert_book_to_notion()`**
   - ✅ 添加了 ISBN 字段处理

2. **`update_book_in_notion()`**
   - ✅ 添加了 ISBN 字段处理

### 未修改的函数（已匹配）

1. **`check_book_exists()`** - 使用"书籍ID"字段查询 ✅
2. **`insert_note_to_notion()`** - 所有字段已匹配 ✅
3. **`insert_highlight_to_info()`** - 所有字段已匹配 ✅
4. **`check_info_exists()`** - 使用"名称"字段查询 ✅

---

**最后更新**: 2025-12-17  
**验证方式**: 通过 MCP Notion API 获取数据库实际字段结构

