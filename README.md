# Amazon Quick SSO with Keycloak

基于 Keycloak 为 Amazon Quick 提供 SAML / OIDC 单点登录。
</br>
<img width="416" height="270" alt="image" src="https://github.com/user-attachments/assets/048836f0-e37c-4f8f-9fd6-d722ef9a72e4" />

## 一、部署指南

### 0. 前置准备

开通 Amazon Quick 账户，选择支持 SSO 的身份验证方法。

- [ ] 注册 AWS 账户
- [ ] 开通 Amazon Quick
  - [ ] 填写账户名称（QUICK_ACCOUNT_NAME），可以是公司英文简称 / 域名标识，如 `example`
  - [ ] 选择默认区域 `US East (N. Virginia)`
  - [ ] 选择身份验证方法：`密码或单点登录（推荐）`

### 1. 部署 Keycloak 基础设施

通过 [`template.yaml`](template.yaml) CloudFormation 模版部署 Keycloak 运行环境。

- [ ] 填写 Keycloak 域名（KEYCLOAK_DOMAIN），如 `sso.example.com`，以及临时管理员用户名和密码
- [ ] 部署过程中在 ACM 控制台完成证书 DNS 验证
- [ ] 配置 DNS 解析，将域名 CNAME 指向 ALB DNS Name
- [ ] 等待部署完成，确认 Keycloak 可访问：`https://<KEYCLOAK_DOMAIN>`

### 2. 配置 Keycloak 管理员

将模板部署时创建的临时管理员，替换为正式管理员。

- [ ] 使用临时管理员登录 Keycloak 管理控制台：`https://<KEYCLOAK_DOMAIN>`
- [ ] 创建正式管理员账户，设置用户名、邮箱、密码，分配 admin 角色
- [ ] 使用正式管理员登录，禁用或删除临时管理员

### 3. 运行 Bootstrap

运行脚本一次性配置好 Realm、Client、Roles、Groups、用户等，不用手动逐个创建。

- [ ] SSH 登录 EC2，进入 `/opt/keycloak/bootstrap/`
- [ ] 编辑 `.env`，填写：
  - Keycloak 管理员凭据（步骤 2 创建的正式管理员的用户名和密码）
  - Quick 管理员信息（Quick 初始用户的用户名和邮箱）
  - Quick 账户名称（QUICK_ACCOUNT_NAME）
  - AWS 账户 ID
- [ ] 运行 `./bootstrap.sh`
- [ ] 确认脚本输出无报错

### 4. 配置 AWS IAM

创建 SAML Identity Provider，建立 AWS 与 Keycloak 之间的信任关系。

- [ ] 下载 SAML Metadata：`https://<KEYCLOAK_DOMAIN>/realms/quick/protocol/saml/descriptor`
- [ ] 在 IAM 控制台创建 SAML Identity Provider
  - 名称：`keycloak`（与模板中 IAM Role 信任策略一致）
  - 上传 Metadata XML 文件

### 5. 配置 Amazon Quick SSO

在 Quick 管理控制台启用 SAML 单点登录，将 Keycloak 作为身份提供商。

- [ ] IdP URL：`https://<KEYCLOAK_DOMAIN>/realms/quick/protocol/saml/clients/aws`
- [ ] IdP 重定向 URL 参数：`RelayState`
- [ ] 开启服务提供商启动的 SSO
- [ ] 开启联合身份用户的电子邮件同步

### 6. 配置 Quick Desktop 扩展访问

通过 OIDC 协议为 Quick Desktop 客户端提供 SSO 登录能力。

- [ ] 添加扩展访问，配置以下参数：
  - Issuer URL：`https://<KEYCLOAK_DOMAIN>/realms/quick`
  - Authorization Endpoint：`https://<KEYCLOAK_DOMAIN>/realms/quick/protocol/openid-connect/auth`
  - Token Endpoint：`https://<KEYCLOAK_DOMAIN>/realms/quick/protocol/openid-connect/token`
  - JWKS URI：`https://<KEYCLOAK_DOMAIN>/realms/quick/protocol/openid-connect/certs`
  - Client ID：`amazon-quick-desktop`
- [ ] 添加扩展

---

## 二、登录方式

### 1. Web 端

Quick 中的用户名就是 IAM 联合用户名称，格式为 `角色名/邮箱`，如 `QuickAdminProRole/admin@example.com`。

#### 1.1 IAM 用户（Quick 初始用户）

使用 AWS 用户名和密码登录：

`https://quicksight.aws.amazon.com/sn/account/<QUICK_ACCOUNT_NAME>/start?enable-sso=0`

#### 1.2 Keycloak 用户

使用 Keycloak 用户名和密码登录（SSO）：

`https://quicksight.aws.amazon.com/sn/account/<QUICK_ACCOUNT_NAME>/start`

#### 1.3 Keycloak 用户中心

用户可自行管理个人信息、修改密码、查看登录设备：

`https://<KEYCLOAK_DOMAIN>/realms/quick/account`

### 2. Desktop 端

通过邮件地址识别，对应 Quick 用户管理中的电子邮件，如 `admin@example.com`。

#### 2.1 IAM 用户（Quick 初始用户）

先使用 AWS 用户名和密码登录 Web 端，再使用 Keycloak 用户名和密码登录（SSO）：

- Bootstrap 脚本已自动创建一个和 Quick 初始用户相同的 Keycloak 用户（密码独立）
- 该用户不能加入 Keycloak 中任何 quick-* 组，否则会在 Quick 中额外创建一个 IAM 联合身份用户

#### 2.2 Keycloak 用户

使用 Keycloak 用户名和密码登录（SSO）：

- 如果用户从未登录过 Quick（包括 Web 端），首次 SSO 登录会自动创建用户并停留在 Web 端
- 再次点击 Desktop 的 SSO 登录及后续登录，跳转正常

---

## 三、常用操作

### 1.【管理员】批量创建用户

通过导入 `keycloak-user-create` Skill，上传用户清单即可自动完成创建用户、分配角色、发送邀请邮件。

#### 前置条件

在 Amazon Quick Desktop 中完成以下配置：

**1. keycloak-mcp-server**

Keycloak 管理 MCP Server，支持用户、组、角色、Client 等 80+ 操作。

参考：https://github.com/M0-AR/keycloak-mcp-server

设置 → 连接 → MCP Server → 添加：

```json
{
  "sso.example.com": {
    "command": "npx",
    "args": ["keycloak-mcp-server"],
    "env": {
      "KEYCLOAK_URL": "https://sso.example.com",
      "KEYCLOAK_ADMIN": "admin",
      "KEYCLOAK_ADMIN_PASSWORD": "changeme"
    }
  }
}
```

**2. mcp-email-server**

IMAP / SMTP 邮件收发 MCP Server，支持收件、发件、附件等操作。

参考：https://github.com/ai-zerolab/mcp-email-server

设置 → 连接 → MCP Server → 添加：

```json
{
  "admin@example.com": {
    "command": "uvx",
    "args": ["mcp-email-server@latest", "stdio"],
    "env": {
      "MCP_EMAIL_SERVER_EMAIL_ADDRESS": "admin@example.com",
      "MCP_EMAIL_SERVER_PASSWORD": "changeme",
      "MCP_EMAIL_SERVER_IMAP_HOST": "imap.example.com",
      "MCP_EMAIL_SERVER_SMTP_HOST": "smtp.example.com"
    }
  }
}
```

**3. keycloak-user-create Skill**

支持单个或批量的创建 Keycloak 用户并发送邀请邮件的自动化流程。

设置 → 技能 → 导入，选择本仓库 `skills/keycloak-user-create/` 文件夹。

#### 操作步骤

1. 准备用户清单，CSV 或 Excel 格式，至少包含"邮件"和"角色"两列：

```csv
邮件,角色
alice@example.com,管理员专业版
bob@example.com,作者专业版
carol@example.com,读者专业版
```

2. 在 Amazon Quick Desktop 中上传文件并输入指令：

> 根据附件创建用户
> Quick 账户名称：example
> SSO 域名：sso.example.com
> 管理员邮箱：admin@example.com

3. 之后自动完成以下全部流程：
- 解析用户清单，智能识别字段
- 按邮箱查重，已存在的用户自动跳过
- 创建用户，生成随机临时密码
- 根据角色分配到对应 Keycloak 组
- 逐人发送包含登录引导的邀请邮件
