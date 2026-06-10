# Amazon Quick + Keycloak SSO 控制台配置步骤

## 步骤 1/11：创建 Realm

1. 登录 Keycloak 管理台：`https://sso.example.com`
2. 左上角 Realm 下拉 → **Create realm**
3. Realm name: `quick`
4. Enabled: On
5. 点击 **Create**
6. 创建后进入 Realm settings → General → Display name 填入 `Amazon Quick`
7. 保存

验证：访问 `https://sso.example.com/realms/quick/account`，页面标题应显示 "Sign in to Amazon Quick"

## 步骤 2/11：创建管理员用户

1. 确认当前在 `quick` Realm
2. 左侧菜单 → **Users** → **Add user**
3. 填写：
   - Email verified: On
   - Username: `admin`
   - Email: `admin@example.com`
   - First name: （填写）
   - Last name: （填写）
4. 点击 **Create**
5. 进入 **Credentials** 标签 → **Set password**
   - 设置密码
   - Temporary: **Off**
6. 点击 **Save**

> 如果未填写姓名，用户首次登录时 Keycloak 会要求补充。

验证：访问 `https://sso.example.com/realms/quick/account`，使用该用户登录

## 步骤 3/11：创建 SAML Client

1. 确认当前在 `quick` Realm
2. 左侧菜单 → **Clients** → **Create client**
3. Client type: **SAML**
4. Client ID: `urn:amazon:webservices`
5. Name: `Amazon Web Services`
6. 点击 **Next**
7. 填写 Login settings:
   - Valid Redirect URIs: `https://signin.aws.amazon.com/saml`
   - IDP-Initiated SSO URL name: `aws`
   - IDP Initiated SSO Relay State: `https://quicksight.aws.amazon.com/sn/account/{QUICK_ACCOUNT_NAME}/start`
   - Master SAML Processing URL: `https://signin.aws.amazon.com/saml`
8. 点击 **Save**
9. 进入 Settings，修改以下非默认值:
   - SAML capabilities → Name ID Format: 改为 **email**（默认 username）
   - SAML capabilities → Force Name ID Format: 改为 **On**（默认 Off）
   - Signature and Encryption → Sign Assertions: 改为 **On**（默认 Off）
10. 保存
11. 进入 **Client scopes** 标签 → 点击 `urn:amazon:webservices-dedicated` → **Scope** 标签 → 关闭 **Full Scope Allowed**

## 步骤 4/11：配置 Client Roles 和 Mappers

### 4.1 创建 Client Roles

1. 进入 Client `urn:amazon:webservices` → **Roles** 标签 → **Create role**
2. 创建 6 个角色，Name 分别为：
   - `arn:aws:iam::123456789012:role/QuickAdminProRole,arn:aws:iam::123456789012:saml-provider/keycloak`
   - `arn:aws:iam::123456789012:role/QuickAuthorProRole,arn:aws:iam::123456789012:saml-provider/keycloak`
   - `arn:aws:iam::123456789012:role/QuickReaderProRole,arn:aws:iam::123456789012:saml-provider/keycloak`
   - `arn:aws:iam::123456789012:role/QuickAdminRole,arn:aws:iam::123456789012:saml-provider/keycloak`
   - `arn:aws:iam::123456789012:role/QuickAuthorRole,arn:aws:iam::123456789012:saml-provider/keycloak`
   - `arn:aws:iam::123456789012:role/QuickReaderRole,arn:aws:iam::123456789012:saml-provider/keycloak`

### 4.2 创建 Mappers

1. 进入 Client `urn:amazon:webservices` → **Client scopes** 标签
2. 点击 `urn:amazon:webservices-dedicated`
3. 点击 **Mappers** → **Add mapper** → **By configuration**

#### Mapper 1：Role
- Mapper type: **Role list**
- Name: `Role`
- SAML Attribute Name: `https://aws.amazon.com/SAML/Attributes/Role`
- SAML Attribute NameFormat: **URI Reference**
- Single Role Attribute: **Off**

#### Mapper 2：RoleSessionName
- Mapper type: **User Property**
- Name: `RoleSessionName`
- SAML Attribute Name: `https://aws.amazon.com/SAML/Attributes/RoleSessionName`
- SAML Attribute NameFormat: **URI Reference**
- Property: `email`

#### Mapper 3：SessionDuration
- Mapper type: **Hardcoded attribute**
- Name: `SessionDuration`
- SAML Attribute Name: `https://aws.amazon.com/SAML/Attributes/SessionDuration`
- SAML Attribute NameFormat: **URI Reference**
- Attribute value: `43200`

#### Mapper 4：PrincipalTag:Email
- Mapper type: **User Property**
- Name: `PrincipalTag:Email`
- SAML Attribute Name: `https://aws.amazon.com/SAML/Attributes/PrincipalTag:Email`
- SAML Attribute NameFormat: **URI Reference**
- Property: `email`

## 步骤 5/11：创建 Groups 并绑定 Client Roles

1. 左侧菜单 → **Groups** → **Create group**
2. 创建 6 个 Group：
   - `quick-admin-pro`
   - `quick-author-pro`
   - `quick-reader-pro`
   - `quick-admin`
   - `quick-author`
   - `quick-reader`
3. 进入每个 Group → **Role mapping** → **Assign role**：
   - 点击 **Filter by clients** → 选择 `urn:amazon:webservices`
   - `quick-admin-pro` → 绑定 Admin Pro 的 Client Role
   - `quick-author-pro` → 绑定 Author Pro 的 Client Role
   - `quick-reader-pro` → 绑定 Reader Pro 的 Client Role
   - `quick-admin` → 绑定 Admin 的 Client Role
   - `quick-author` → 绑定 Author 的 Client Role
   - `quick-reader` → 绑定 Reader 的 Client Role

## 步骤 6/11：创建 IAM SAML 身份提供商

1. 下载 Keycloak SAML Metadata XML：`https://sso.example.com/realms/quick/protocol/saml/descriptor`
2. AWS 控制台 → **IAM** → **身份提供商** → **添加提供商**
3. 提供商类型：**SAML**
4. 提供商名称：`keycloak`
5. 上传 Metadata XML 文件
6. 点击 **添加提供商**

## 步骤 7/11：创建 IAM 角色

对以下 6 个角色分别执行：

| 角色名 | 权限 Action |
|--------|------------|
| `QuickAdminProRole` | `quicksight:CreateAdmin` |
| `QuickAuthorProRole` | `quicksight:CreateUser` |
| `QuickReaderProRole` | `quicksight:CreateReader` |
| `QuickAdminRole` | `quicksight:CreateAdmin` |
| `QuickAuthorRole` | `quicksight:CreateUser` |
| `QuickReaderRole` | `quicksight:CreateReader` |

每个角色的创建步骤：

1. IAM → **角色** → **创建角色**
2. 受信任实体类型：**SAML 2.0 联合**
3. SAML 提供商：`keycloak`
4. 点击 **下一步** → 不添加权限策略 → **下一步**
5. 角色名称：填入对应角色名
6. 点击 **创建角色**

创建后编辑每个角色：

### 信任策略

编辑信任策略，替换为：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:saml-provider/keycloak"
      },
      "Action": [
        "sts:AssumeRoleWithSAML",
        "sts:TagSession"
      ],
      "Condition": {
        "StringEquals": {
          "SAML:aud": "https://signin.aws.amazon.com/saml"
        }
      }
    }
  ]
}
```

### 内联策略

添加权限 → 创建内联策略 → JSON：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "quicksight:<对应Action>",
      "Resource": "arn:aws:quicksight::<AWS_ACCOUNT_ID>:user/${aws:userid}"
    }
  ]
}
```

策略名称：`QuickSightAccess`

### MaxSessionDuration

编辑角色 → 最大会话持续时间：改为 **43200 秒**（12 小时）

## 步骤 8/11：在 Amazon Quick 开启 SSO

1. 登录 Amazon Quick 管理页面
2. 管理账户 → **SSO**
3. 配置：
   - IdP URL: `https://sso.example.com/realms/quick/protocol/saml/clients/aws`
   - IdP 重定向 URL 参数: `RelayState`
4. 点击 **保存**
5. 服务提供商启动的 SSO → 状态：**开启**
6. 联合身份用户的电子邮件同步：**开启**

验证：使用页面底部的测试 URL，在无痕浏览器中打开测试 SSO 登录

## 步骤 9/11：测试 Web SSO

### IdP-Initiated SSO

1. 在无痕浏览器中访问：`https://sso.example.com/realms/quick/protocol/saml/clients/aws`
2. 跳转到 Keycloak 登录页，使用 Keycloak 用户名和密码登录
3. 登录后验证进入 Quick

### SP-Initiated SSO（推荐）

1. 在无痕浏览器中访问：`https://quicksight.aws.amazon.com/sn/account/{QUICK_ACCOUNT_NAME}/start`
2. 跳转到 Keycloak 登录页，使用 Keycloak 用户名和密码登录
3. 登录后验证进入 Quick

### Keycloak 用户中心

用户可自行管理个人信息、修改密码、查看登录设备：

`https://sso.example.com/realms/quick/account`

### 基于密码登录

需要绕过 IdP 并直接登录 Quick 时：

1. 在无痕浏览器中访问：`https://quicksight.aws.amazon.com/sn/account/{QUICK_ACCOUNT_NAME}/start?enable-sso=0`
2. 在 Quick 登录页输入 AWS 用户名
3. 跳转到 AWS 登录页，使用 AWS 用户名和密码登录
4. 登录后验证进入 Quick

## 步骤 10/11：配置 Quick 桌面客户端 SSO

### 9.1 创建 OIDC Client（Keycloak）

1. 确认当前在 `quick` Realm
2. 左侧菜单 → **Clients** → **Create client**
3. Client type: **OpenID Connect**
4. Client ID: `amazon-quick-desktop`
5. Name: `Amazon Quick Desktop`
6. 点击 **Next**
7. Authentication flow: 仅勾选 **Standard flow**
8. Require PKCE: **On**
9. PKCE Method: **S256**
10. 点击 **Next**
11. Login settings:
    - Valid Redirect URIs: `http://localhost:18080`
12. 点击 **Save**

### 9.2 配置 offline_access Scope

1. 进入 Client `amazon-quick-desktop` → **Client scopes** 标签
2. 找到 `offline_access`，将其从 Optional 改为 **Default**

### 9.3 添加扩展访问权限（Quick 控制台）

1. 登录 Amazon Quick 管理控制台
2. 权限 → **扩展访问权限** → **添加扩展访问**
3. 选择 **Amazon Quick** → 下一步
4. 填写：

| 字段 | 值 |
|------|-----|
| Name | `QuickDesktop-access` |
| Description | `Desktop application for Quick` |
| Issuer URL | `https://sso.example.com/realms/quick` |
| Authorization Endpoint | `https://sso.example.com/realms/quick/protocol/openid-connect/auth` |
| Token Endpoint | `https://sso.example.com/realms/quick/protocol/openid-connect/token` |
| JWKS URI | `https://sso.example.com/realms/quick/protocol/openid-connect/certs` |
| Client ID | `amazon-quick-desktop` |

5. 点击 **添加**

> 以上端点可从 Keycloak 的 well-known 地址确认：`https://sso.example.com/realms/quick/.well-known/openid-configuration`

### 9.4 添加扩展（Quick 控制台）

1. 左侧导航 → 连接应用程序和数据 → **扩展** → **创建扩展**
2. 选择上一步创建的桌面应用程序扩展 → 下一步
3. 点击 **创建**

### 9.5 测试

1. 下载并安装 Amazon Quick Desktop
2. 登录界面选择 **Enterprise 登录**
3. 跳转到 Keycloak 登录页，使用 Keycloak 用户名和密码登录
4. 登录后验证进入 Quick Desktop
