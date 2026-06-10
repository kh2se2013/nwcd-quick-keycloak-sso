# 管理员须知

本文档面向使用 Keycloak SSO 方案的客户管理员，列出日常运维中的关键操作规范。

## 一、Keycloak 管理

### 🔴 MUST

#### 创建用户时开启 Email Verified

Quick 使用邮箱作为用户唯一标识，未验证的邮箱会导致 SAML 断言中缺少邮箱属性，用户无法正常登录。

#### 每个用户只分配一个 `quick-*` 组

多个组会导致 SAML Response 包含多个 Role，AWS 无法自动选择，用户登录失败。

各组对应的 Quick 角色：

| Keycloak 组 | Quick 角色 | 订阅类型 |
| --- | --- | --- |
| `quick-admin-pro` | Admin Pro | Quick Enterprise |
| `quick-author-pro` | Author Pro | Quick Enterprise |
| `quick-reader-pro` | Reader Pro | Quick Professional |
| `quick-admin` | Admin | Quick Sight Author |
| `quick-author` | Author | Quick Sight Author |
| `quick-reader` | Reader | Quick Sight Reader |

### 🔴 MUST NOT

#### 修改 SSO 相关 Client 配置

`urn:amazon:webservices` 和 `amazon-quick-client` 的 Client ID、Role、Mappers、Scope、签名设置等均与 AWS 联动，任何改动都可能导致 SSO 中断。

#### 修改 Realm 名称

Realm 名称嵌入在所有端点 URL 中，创建后不可更改，修改只能通过重建 Realm 实现。

#### 通过切换 Keycloak 组来变更用户角色

切换 `quick-*` 组会在 Quick 中产生新的联合身份用户，旧身份数据不会迁移，且邮箱冲突可能导致 Desktop 登录失败。变更用户角色应在 Quick 用户管理中直接操作，不要通过切换 Keycloak 组实现。

#### 将 Quick 初始用户对应的 Keycloak 账号加入 `quick-*` 组

IAM 用户和联合身份用户在 Quick 中是两个独立账号，加入组后会额外创建一个联合身份，与原 IAM 用户产生冲突。

### 🟡 SHOULD

#### 配置密码复杂度策略

在 Authentication → Policies → Password policy 中启用密码长度、大小写、特殊字符等要求，降低弱密码风险。

#### 通过 Group 而非 Role 管理用户权限

将用户加入 `quick-*` 组而非直接分配 Client Role，方便按组批量操作和审计。

#### 定期清理已离职用户

离职人员应及时在 Keycloak 中禁用或删除，同时在 Quick 用户管理中删除对应的联合身份用户以释放订阅名额。Keycloak 与 Quick 之间不会自动同步删除。

#### 监控异常登录

建议开启以下两项：

1. **登录事件记录**：Realm Settings → Events → User events settings → 开启 Save events，Event types 至少勾选 `LOGIN_ERROR`、`LOGIN`。开启后可在 Events 页面查看登录失败记录。
2. **暴力破解保护**：Realm Settings → Security defenses → Brute force detection → 开启 Enabled，建议 Max login failures 设为 5（默认30太宽松），Wait increment 设为 60秒，Max wait 设为 15分钟。开启后超过阈值的账户会被临时锁定。

### 🟡 SHOULD NOT

#### 给普通用户分配 Keycloak 管理员权限

管理控制台可修改所有 Realm 配置，权限泄露可能导致 SSO 全面中断，仅限指定人员访问。

## 二、AWS 账户管理

### 🔴 MUST

#### SAML 密钥轮换后同步更新 IAM Provider

若在 Realm Settings → Keys 中重新生成了签名密钥，必须重新下载 Metadata XML 并更新 IAM SAML Provider，否则所有用户立即无法登录。Keycloak 不会自动轮换密钥，默认证书有效期为10年，日常无需主动操作。

### 🔴 MUST NOT

#### 修改 IAM Role 信任策略中的 SAML Provider ARN

该值必须与 IAM 中创建的 SAML Provider 名称完全一致，手动修改会导致信任关系断裂，所有 SSO 用户登录失败。

### 🟡 SHOULD

#### 关注 ACM 证书自动续期状态

ALB 使用的 ACM 证书依赖 DNS 验证自动续期，若域名 DNS 配置变更可能导致续期失败，证书过期后 HTTPS 不可用。

## 三、Quick 用户管理

### 🔴 MUST

#### 保留 Quick 初始用户

Quick 部署时创建的初始用户是 Keycloak 故障时的唯一登录方式。删除后若 Keycloak 不可用，将彻底无法访问 Quick 管理后台。
