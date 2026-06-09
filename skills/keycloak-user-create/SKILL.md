---
name: keycloak-user-create
display_name: Keycloak 创建用户
resources: [email-template.md]
description: "创建 Keycloak 用户并发送邀请邮件，支持单个或批量。触发信号：'批量创建用户'、'创建用户'、'创建 Keycloak 用户'、'根据附件创建用户'、'帮我开个账号'等。"
icon: "👥"
trigger: 创建 Keycloak 用户
inputs:
  - name: quick_account_name
    description: "Amazon Quick 账户名称，用于拼接 Web 登录地址"
    type: string
    required: true
  - name: keycloak_domain
    description: "Keycloak 域名，如 sso.example.com"
    type: string
    required: true
  - name: admin_email
    description: "管理员邮箱，用于邮件中的联系方式"
    type: string
    required: true
  - name: phone_number
    description: "联系电话，用于邮件中的联系方式"
    type: string
    required: false
tools: [run_python, file_read]
---

## Overview

从用户清单中读取用户信息，在 Keycloak 中创建用户、按角色分配到对应组、为每人生成随机临时密码，最后通过邮件 MCP 连接器发送包含完整登录引导的邀请邮件。支持 Excel、CSV 附件或对话中直接提供用户信息。

用户已存在时整个跳过，不做任何修改。

## Workflow

### Step 1：解析用户清单
- **Mode**: `agentic`
- **Tool**: `run_python`
- **Input**: 用户提供的用户信息，支持以下方式：
  1. Excel 附件（.xlsx）
  2. CSV 附件（.csv）
  3. 对话中直接提供的单个或多个用户信息（如"创建用户 alice@example.com，角色管理员专业版"）
- **Output**: 用户列表，每条包含以下字段：
  - 邮件（必填）
  - 角色（必填）
  - username（选填，不提供则取邮箱 @ 前缀）
  - 姓 lastName（选填）
  - 名 firstName（选填，如提供全名则智能拆分为姓和名）
- **Validate**: 
  - 至少有1条用户记录
  - 每条记录必须包含邮件和角色，缺少任一字段时提示用户补充
- **On failure**: 提示用户补充缺失信息，每个待创建用户至少需要邮件和角色

解析策略：
- **Excel**：用 openpyxl 读取，识别"邮件"和"角色"列
- **CSV**：用 pandas 或 csv 模块读取，识别"邮件"和"角色"列
- **对话文本**：从用户消息中提取邮箱和角色信息，构建用户列表

### Step 2：查询环境 & 角色映射
- **Mode**: `agentic`
- **Tool**: keycloak `list-groups`
- **Input**: Keycloak realm（固定为 `quick`）
- **Output**: 角色→组 ID 映射表
- **Validate**: 每个用户清单中出现的角色都能匹配到一个组
- **On failure**: 列出可用组让用户确认映射关系

映射规则：
| 标准中文名 | 组名 | 可接受的模糊输入 |
|-----------|------|-----------------|
| 管理员专业版 | `quick-admin-pro` | admin-pro、adminPro、Admin Pro、管理员pro |
| 作者专业版 | `quick-author-pro` | author-pro、authorPro、Author Pro、作者pro |
| 读者专业版 | `quick-reader-pro` | reader-pro、readerPro、Reader Pro、读者pro |
| 管理员 | `quick-admin` | admin、Admin |
| 作者 | `quick-author` | author、Author |
| 读者 | `quick-reader` | reader、Reader |

**角色名标准化**：无论用户清单中使用哪种格式（英文、中英混合、驼峰、短横线等），都智能匹配到对应组，并在邮件中统一显示为标准中文名（如"管理员专业版"）。

### Step 3：按 email 查重
- **Mode**: `deterministic`
- **Tool**: keycloak `search-users`
- **Input**: 用户列表中的每个 email
- **Output**: 分为两组：待创建用户、已存在用户
- **Validate**: 搜索返回正常
- **On failure**: 如连接失败，重试2次后提示用户检查 Keycloak 状态

**已存在的用户整个跳过**，不分组、不改密码、不发邮件。在最终汇总中标注"已存在，跳过"。

### Step 4：创建用户 & 设置密码
- **Mode**: `deterministic`
- **Tool**: keycloak `create-user`、`reset-user-password`
- **Input**: 待创建用户列表
- **Output**: 每个用户的 userId + 随机临时密码
- **Validate**: 每个用户创建成功并获得 userId
- **On failure**: 记录失败用户，继续处理剩余

**字段取值逻辑**：
- **username**（Keycloak 登录名）：清单中提供则用提供的，否则取邮箱 @ 前缀
- **firstName / lastName**：清单中分开提供则直接用；提供全名则智能拆分（中文姓在前名在后，英文名在前姓在后）；未提供则 firstName 取邮箱前缀，lastName 留空
- **邮件中称呼**（模板 `Hi [称呼]`）：优先级依次为姓名 > username > 邮箱前缀

密码生成规则：每人不同，12位随机字符串，包含大小写字母 + 数字 + 特殊字符。设置时 `temporary: true`。

### Step 5：分配到组
- **Mode**: `deterministic`
- **Tool**: keycloak `manage-user-groups`
- **Input**: userId + groupId 映射
- **Output**: 分组结果
- **Validate**: 每个用户成功加入对应组
- **On failure**: 记录失败项，继续处理其余

### Step 6：发送邀请邮件
- **Mode**: `deterministic`
- **Tool**: email `send_email`
- **Format**: 将模板内容从 Markdown 转为 HTML 后，以 `html=True` 发送。转换和后处理流程如下：

  **预处理（Markdown 转换前）**：
  1. 去掉模板标题行（`#` 开头的第一行，仅用于描述模板风格，不发给用户）和主题行（`**主题：**` 开头的行，用于提取邮件 subject）
  2. 去掉所有 `---` 分隔线行
  3. 去掉 `[电话号码]` 行（如未提供 phone_number）
  4. 密码中 `*` `_` 等 Markdown 特殊字符需转义（`*` → `\*`，`_` → `\_`），避免被解析为斜体/加粗
  5. 提取表格行（`| key | value |` 格式），替换为占位符，后续用 div 模拟

  **Markdown 转换**：`markdown.markdown(text, extensions=['tables'])`

  **HTML 后处理（必须，否则邮件客户端渲染极差）**：
  1. **表格用 div 模拟**（不用 `<table>` 标签，避免邮件客户端兼容性问题）：
     - 外层 `<div>` 带边框 + 圆角 6px + `overflow: hidden`
     - 每行一个 `<div>`，行间 `border-bottom` 分隔
     - 左列 `<span>`：固定宽度 80px，浅灰背景 `#fafafa`，右边框分隔，颜色 `rgba(0,0,0,0.45)`
     - 右列 `<span>`：自动宽度，颜色 `rgba(0,0,0,0.88)`
  2. **`<p>` 和 `<li>` 内容用 `<span>` 包裹**（防止邮件客户端覆盖字体）：
     - span style: `font-family: ...; font-size: 14px; color: rgba(0,0,0,0.88);`
  3. **`<blockquote>` 内部 span 用次要颜色**：`rgba(0,0,0,0.65)`
  4. **所有元素加显式 inline style**（不依赖继承）
  5. **外层 div 包裹**：`max-width: 600px`

  **设计规范（Ant Design v5 Token）**：
  - 字体族：`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
  - 正文字号：14px
  - h2 标题字号：20px，font-weight: 600
  - 行高：1.5714
  - 正文颜色：`rgba(0,0,0,0.88)`
  - 次要文本：`rgba(0,0,0,0.65)`
  - 标签/辅助文本：`rgba(0,0,0,0.45)`
  - 边框色：`#d9d9d9`
  - 背景色：`#fafafa`
  - 主色（引用块左边框）：`#1677ff`
  - 圆角：6px
  - 段落间距：12px
  - 表格 padding：12px 16px

- **Input**: 每个新创建用户的信息 + {{quick_account_name}} + {{keycloak_domain}} + 邮件模板
- **Output**: 邮件发送状态
- **Validate**: 每封邮件返回发送成功
- **On failure**: 记录发送失败的邮箱

**模板来源（按优先级）**：
1. 用户在对话中提供了自定义模板（文字内容或附件文件） → 使用用户提供的模板
2. 未提供 → 使用默认模板 `email-template.md`

发送时将模板中的占位符替换为实际值：
- `[称呼]` → 姓名 > username > 邮箱前缀（按优先级取第一个有值的）
- `[用户名]` → 用户名
- `[邮箱]` → 用户邮箱
- `[临时密码]` → 生成的随机密码
- `[角色]` → 实际角色名（如管理员专业版、作者专业版、读者专业版）
- `[Quick 账户名称]` → {{quick_account_name}}
- `[SSO 域名]` → {{keycloak_domain}}
- `[管理员邮箱]` → {{admin_email}}
- `[电话号码]` → {{phone_number}}（未提供时去掉该行）

自定义模板中如果使用了不同的占位符格式，按实际内容智能匹配替换。

### Step 7：输出汇总报告
- **Mode**: `deterministic`
- **Input**: 所有步骤的执行结果
- **Output**: Markdown 表格

| 邮件 | 用户名 | 角色 | 状态 | 备注 |
|------|--------|------|------|------|
| alice@example.com | alice | 管理员专业版 | ✅ 完成 | 创建 + 分组 + 邮件已发 |
| bob@example.com | bob | 作者专业版 | ⏭️ 跳过 | 用户已存在 |

## Output

一个 Markdown 表格汇总所有用户的处理结果。正常情况下用户无需任何后续操作。

## Lessons Learned

### Do
- 创建前按 email 查重，已存在则整个跳过
- 每人生成不同随机密码
- 邀请信息合并为一封邮件发送
- 设置 `temporary: true`，强制首次登录改密
- 并行调用 Keycloak 接口提升效率

### Don't
- 不要对已存在用户执行任何操作（不重置密码、不重新分组、不发邮件）
- 不要使用统一密码
- 不依赖 Keycloak SMTP 发送邮件，使用邮件 MCP 连接器

### Common Failures
- **Keycloak 连接失败**：可能是服务器未启动或网络问题，重试2次后提示用户
- **用户已存在**：按 email 搜索发现已有用户，整个跳过
- **未知角色**：用户清单中角色名无法匹配到已有组，暂停并询问用户

### When to Ask the User
- inputs 变量未提供时（quick_account_name、keycloak_domain、admin_email、phone_number）
- 用户清单中出现无法匹配的角色名
- Keycloak 连接持续失败
- 邮件发送全部失败