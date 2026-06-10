"""
Amazon Quick + Keycloak SSO 配置
当前：步骤 1-5, 10.1-10.2
"""
import os
import sys
from dotenv import load_dotenv
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

load_dotenv()

# 配置
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL")
KEYCLOAK_MASTER_ADMIN_USERNAME = os.getenv("KEYCLOAK_MASTER_ADMIN_USERNAME")
KEYCLOAK_MASTER_ADMIN_PASSWORD = os.getenv("KEYCLOAK_MASTER_ADMIN_PASSWORD")
KEYCLOAK_QUICK_REALM = os.getenv("KEYCLOAK_QUICK_REALM")
KEYCLOAK_QUICK_ADMIN_USERNAME = os.getenv("KEYCLOAK_QUICK_ADMIN_USERNAME")
KEYCLOAK_QUICK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_QUICK_ADMIN_PASSWORD")
KEYCLOAK_QUICK_ADMIN_EMAIL = os.getenv("KEYCLOAK_QUICK_ADMIN_EMAIL")
QUICK_ACCOUNT_NAME = os.getenv("QUICK_ACCOUNT_NAME")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")
MAPPER_SESSION_DURATION_VALUE = os.getenv("MAPPER_SESSION_DURATION_VALUE")

required = ["KEYCLOAK_SERVER_URL", "KEYCLOAK_MASTER_ADMIN_USERNAME",
            "KEYCLOAK_MASTER_ADMIN_PASSWORD", "KEYCLOAK_QUICK_REALM",
            "KEYCLOAK_QUICK_ADMIN_USERNAME", "KEYCLOAK_QUICK_ADMIN_PASSWORD",
            "KEYCLOAK_QUICK_ADMIN_EMAIL", "QUICK_ACCOUNT_NAME",
            "AWS_ACCOUNT_ID", "MAPPER_SESSION_DURATION_VALUE"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f"[ERROR] 缺少环境变量: {', '.join(missing)}")
    sys.exit(1)

QUICK_ADMIN_PRO_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/QuickAdminProRole,arn:aws:iam::{AWS_ACCOUNT_ID}:saml-provider/keycloak"
QUICK_AUTHOR_PRO_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/QuickAuthorProRole,arn:aws:iam::{AWS_ACCOUNT_ID}:saml-provider/keycloak"
QUICK_READER_PRO_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/QuickReaderProRole,arn:aws:iam::{AWS_ACCOUNT_ID}:saml-provider/keycloak"
QUICK_ADMIN_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/QuickAdminRole,arn:aws:iam::{AWS_ACCOUNT_ID}:saml-provider/keycloak"
QUICK_AUTHOR_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/QuickAuthorRole,arn:aws:iam::{AWS_ACCOUNT_ID}:saml-provider/keycloak"
QUICK_READER_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/QuickReaderRole,arn:aws:iam::{AWS_ACCOUNT_ID}:saml-provider/keycloak"

# 连接 Keycloak
admin = KeycloakAdmin(
    server_url=KEYCLOAK_SERVER_URL,
    username=KEYCLOAK_MASTER_ADMIN_USERNAME,
    password=KEYCLOAK_MASTER_ADMIN_PASSWORD,
    realm_name="master",
    verify=True
)
print(f"[OK] Keycloak '{KEYCLOAK_SERVER_URL}' 已连接")

# 步骤 1：创建 Realm
try:
    admin.create_realm(payload={
        "enabled": True,
        "realm": KEYCLOAK_QUICK_REALM,
        "displayName": "Amazon Quick"
    })
    print(f"[OK] Realm '{KEYCLOAK_QUICK_REALM}' 创建成功")
except KeycloakError as e:
    if "409" in str(e):
        print(f"[SKIP] Realm '{KEYCLOAK_QUICK_REALM}' 已存在")
    else:
        raise

# 步骤 2：创建管理员用户
admin.change_current_realm(KEYCLOAK_QUICK_REALM)

try:
    admin.create_user({
        "enabled": True,
        "emailVerified": True,
        "username": KEYCLOAK_QUICK_ADMIN_USERNAME,
        "email": KEYCLOAK_QUICK_ADMIN_EMAIL,
        "credentials": [{
            "type": "password",
            "value": KEYCLOAK_QUICK_ADMIN_PASSWORD,
            "temporary": False
        }]
    })
    print(f"[OK] 用户 '{KEYCLOAK_QUICK_ADMIN_USERNAME}' 创建成功")
except KeycloakError as e:
    if "409" in str(e):
        print(f"[SKIP] 用户 '{KEYCLOAK_QUICK_ADMIN_USERNAME}' 已存在")
    else:
        raise

# 步骤 3：创建 SAML Client
try:
    admin.create_client({
        "enabled": True,
        "protocol": "saml",
        "clientId": "urn:amazon:webservices",
        "name": "Amazon Web Services",
        "redirectUris": ["https://signin.aws.amazon.com/saml"],
        "adminUrl": "https://signin.aws.amazon.com/saml",
        "attributes": {
            "saml_idp_initiated_sso_url_name": "aws",
            "saml_idp_initiated_sso_relay_state": f"https://quicksight.aws.amazon.com/sn/account/{QUICK_ACCOUNT_NAME}/start",
            "saml_name_id_format": "email",
            "saml_force_name_id_format": "true",
            "saml.assertion.signature": "true",
        },
        "fullScopeAllowed": False,
    })
    print("[OK] SAML Client 'urn:amazon:webservices' 创建成功")
except KeycloakError as e:
    if "409" in str(e):
        print("[SKIP] SAML Client 'urn:amazon:webservices' 已存在")
    else:
        raise

# 步骤 4：配置 Client Roles 和 Mappers
clients = admin.get_clients()
client_uuid = None
for c in clients:
    if c.get("clientId") == "urn:amazon:webservices":
        client_uuid = c["id"]
        break

if not client_uuid:
    print("[ERROR] SAML Client 'urn:amazon:webservices' 未找到")
else:
    # 移除 role_list Client Scope
    default_scopes = admin.get_client_default_client_scopes(client_uuid)
    for scope in default_scopes:
        if scope["name"] == "role_list":
            admin.delete_client_default_client_scope(client_uuid, scope["id"])
            print("[OK] Client Scope 'role_list' 已移除")
            break
    else:
        print("[SKIP] Client Scope 'role_list' 已不存在")

    # 4.1 创建 Client Roles
    roles = [
        {"name": QUICK_ADMIN_PRO_ROLE, "description": "Quick Admin Pro"},
        {"name": QUICK_AUTHOR_PRO_ROLE, "description": "Quick Author Pro"},
        {"name": QUICK_READER_PRO_ROLE, "description": "Quick Reader Pro"},
        {"name": QUICK_ADMIN_ROLE, "description": "Quick Admin"},
        {"name": QUICK_AUTHOR_ROLE, "description": "Quick Author"},
        {"name": QUICK_READER_ROLE, "description": "Quick Reader"},
    ]
    for role in roles:
        try:
            admin.create_client_role(client_uuid, role)
            print(f"[OK] Client Role '{role['description']}' 创建成功")
        except KeycloakError as e:
            if "409" in str(e):
                print(f"[SKIP] Client Role '{role['description']}' 已存在")
            else:
                print(f"[ERROR] Client Role '{role['description']}' 失败: {e}")

    # 4.2 创建 Mappers
    mappers = [
        {
            "protocol": "saml",
            "name": "Role",
            "protocolMapper": "saml-role-list-mapper",
            "config": {
                "single": "false",
                "attribute.name": "https://aws.amazon.com/SAML/Attributes/Role",
                "attribute.nameformat": "URI Reference",
            }
        },
        {
            "protocol": "saml",
            "name": "RoleSessionName",
            "protocolMapper": "saml-user-property-mapper",
            "config": {
                "attribute.name": "https://aws.amazon.com/SAML/Attributes/RoleSessionName",
                "attribute.nameformat": "URI Reference",
                "user.attribute": "email",
            }
        },
        {
            "protocol": "saml",
            "name": "SessionDuration",
            "protocolMapper": "saml-hardcode-attribute-mapper",
            "config": {
                "attribute.name": "https://aws.amazon.com/SAML/Attributes/SessionDuration",
                "attribute.nameformat": "URI Reference",
                "attribute.value": MAPPER_SESSION_DURATION_VALUE,
            }
        },
        {
            "protocol": "saml",
            "name": "PrincipalTag:Email",
            "protocolMapper": "saml-user-property-mapper",
            "config": {
                "attribute.name": "https://aws.amazon.com/SAML/Attributes/PrincipalTag:Email",
                "attribute.nameformat": "URI Reference",
                "user.attribute": "email",
            }
        },
    ]

    for mapper in mappers:
        try:
            admin.add_mapper_to_client(client_uuid, mapper)
            print(f"[OK] Mapper '{mapper['name']}' 创建成功")
        except KeycloakError as e:
            if "409" in str(e):
                print(f"[SKIP] Mapper '{mapper['name']}' 已存在")
            else:
                print(f"[ERROR] Mapper '{mapper['name']}' 失败: {e}")


    # 步骤 5：创建 Groups 并绑定 Client Roles
    groups = [
        {"name": "quick-admin-pro", "role": QUICK_ADMIN_PRO_ROLE, "description": "Quick Admin Pro"},
        {"name": "quick-author-pro", "role": QUICK_AUTHOR_PRO_ROLE, "description": "Quick Author Pro"},
        {"name": "quick-reader-pro", "role": QUICK_READER_PRO_ROLE, "description": "Quick Reader Pro"},
        {"name": "quick-admin", "role": QUICK_ADMIN_ROLE, "description": "Quick Admin"},
        {"name": "quick-author", "role": QUICK_AUTHOR_ROLE, "description": "Quick Author"},
        {"name": "quick-reader", "role": QUICK_READER_ROLE, "description": "Quick Reader"},
    ]
    for group in groups:
        try:
            admin.create_group({"name": group["name"], "attributes": {"description": [group["description"]]}})
            print(f"[OK] Group '{group['name']}' 创建成功")
        except KeycloakError as e:
            if "409" in str(e):
                print(f"[SKIP] Group '{group['name']}' 已存在")
            else:
                print(f"[ERROR] Group '{group['name']}' 失败: {e}")

        group_id = admin.get_group_by_path(f"/{group['name']}")["id"]
        existing_roles = admin.get_group_client_roles(group_id, client_uuid)
        if any(r["name"] == group["role"] for r in existing_roles):
            print(f"[SKIP] Group '{group['name']}' Role 已绑定")
        else:
            client_roles = admin.get_client_roles(client_uuid)
            role = next(r for r in client_roles if r["name"] == group["role"])
            admin.assign_group_client_roles(group_id, client_uuid, [role])
            print(f"[OK] Group '{group['name']}' 绑定 Role 成功")

# 步骤 10.1：创建 OIDC Client (Quick Desktop)
try:
    admin.create_client({
        "enabled": True,
        "protocol": "openid-connect",
        "clientId": "amazon-quick-desktop",
        "name": "Amazon Quick Desktop",
        "directAccessGrantsEnabled": False,
        "redirectUris": ["http://localhost:18080"],
        "attributes": {
            "pkce.code.challenge.method": "S256",
        },
    })
    print("[OK] OIDC Client 'amazon-quick-desktop' 创建成功")
except KeycloakError as e:
    if "409" in str(e):
        print("[SKIP] OIDC Client 'amazon-quick-desktop' 已存在")
    else:
        raise

# 步骤 10.2：配置 offline_access Scope 为 Default
oidc_clients = admin.get_clients()
oidc_client_uuid = None
for c in oidc_clients:
    if c.get("clientId") == "amazon-quick-desktop":
        oidc_client_uuid = c["id"]
        break

if oidc_client_uuid:
    optional_scopes = admin.get_client_optional_client_scopes(oidc_client_uuid)
    for scope in optional_scopes:
        if scope["name"] == "offline_access":
            admin.delete_client_optional_client_scope(oidc_client_uuid, scope["id"])
            admin.add_client_default_client_scope(oidc_client_uuid, scope["id"], {})
            print("[OK] Scope 'offline_access' 已设为 Default")
            break
    else:
        default_scopes = admin.get_client_default_client_scopes(oidc_client_uuid)
        if any(s["name"] == "offline_access" for s in default_scopes):
            print("[SKIP] Scope 'offline_access' 已是 Default")
        else:
            print("[WARN] Scope 'offline_access' 未找到")
else:
    print("[ERROR] 未找到 OIDC Client 'amazon-quick-desktop'")
