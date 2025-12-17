# 配置说明

## 已完成的配置

✅ **微信读书 Cookie** - 已配置在 `.env` 文件中
✅ **Python 虚拟环境** - 已创建并安装依赖

## 需要配置的项

### 1. Notion Integration Token

需要获取 Notion Integration Token 才能同步数据到 Notion。

#### 获取步骤：

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 点击 **"+ New integration"**
3. 填写信息：
   - **Name**: 例如 "微信读书同步"
   - **Type**: 选择 "Internal"
   - **Associated workspace**: 选择你的工作区
4. 点击 **"Submit"**
5. 复制 **"Internal Integration Token"**（以 `secret_` 开头）
6. 在 Notion 中打开你的数据库页面，点击右上角 **"..."** → **"Connections"** → 选择你刚创建的 Integration

#### 配置 Token：

编辑 `.env` 文件，取消注释并填入你的 Token：

```bash
NOTION_TOKEN=secret_你的token_这里
```

### 2. 数据库权限

确保你的 Notion Integration 有权限访问以下数据库：
- 书籍数据库
- 笔记数据库  
- 信息数据库

在 Notion 中打开每个数据库页面，点击右上角 **"..."** → **"Connections"** → 选择你的 Integration。

## 运行脚本

### 方式一：使用提供的运行脚本

```bash
./run.sh
```

### 方式二：手动运行

```bash
source venv/bin/activate
python scripts/weread.py
```

### 方式三：同步所有书籍（忽略已同步状态）

```bash
source venv/bin/activate
python scripts/weread.py --all
```

## 当前状态

- ✅ Cookie 已配置
- ✅ 依赖已安装
- ⚠️ 需要配置 NOTION_TOKEN
- ✅ 已检测到 12 本书籍

