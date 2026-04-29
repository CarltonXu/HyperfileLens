# HyperFileLens License 设计方案

## 核心原则

1. **简单有效**：License 不限制功能，只做数量限制
2. **机器绑定**：激活码绑定机器 + 租户 + 用户
3. **安全可靠**：签名验证，防止篡改

## 1. 机器码设计

### 组成要素

```
机器码 = SHA256(
  MAC地址(主网卡) +
  CPU ID +
  主板序列号 +
  租户ID +
  用户ID
)
```

### 生成流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        机器码生成流程                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  租户管理员操作                                                      │
│  ┌──────────────────┐                                               │
│  │  点击"导出机器码" │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │  后端收集信息    │                                               │
│  │  - MAC 地址      │  ← 从请求头或服务端获取                         │
│  │  - CPU ID        │  ← 服务端执行命令获取                          │
│  │  - 主板序列号    │  ← 服务端执行命令获取                          │
│  │  - 租户 ID       │  ← 当前登录用户的租户                          │
│  │  - 用户 ID       │  ← 当前登录用户                                │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │  SHA256 哈希     │                                               │
│  │  取前 32 字符    │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  机器码: HFL-MCH-XXXX-XXXX-XXXX-XXXX                                │
│           │                                                          │
│           │ 显示给用户，用户发送给销售                                │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │  用户复制机器码  │                                               │
│  │  发送给销售团队  │                                               │
│  └──────────────────┘                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. 激活码设计

### 激活码结构

```
激活码 = Base64(JSON({
  "license_key": "HFL-PRO-2026-XXXXXXXX",  // License 唯一标识
  "machine_code": "HFL-MCH-XXXX-XXXX-...", // 绑定的机器码
  "limits": {                              // 数量限制
    "max_tenants": 5,
    "max_users": 100,
    "max_proxies": 20,
    "max_storage_gb": 1000,
    "max_gateways": 5,
    "ai_insights_quota": 1000,
    "max_backup_tasks": 50,
    "max_recovery_tasks": 50,
    "max_source_resources": 30,
    "max_policies": 100,
    "max_repositories": 20
  },
  "expires_at": "2027-01-01T00:00:00Z",    // 过期时间
  "issued_at": "2026-01-01T00:00:00Z",     // 颁发时间
  "signature": "xxxx"                      // 签名
}))
```

### 生成流程（销售端）

```
┌─────────────────────────────────────────────────────────────────────┐
│                        激活码生成流程（销售端）                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  销售收到机器码                                                      │
│  ┌──────────────────┐                                               │
│  │  输入机器码      │                                               │
│  │  HFL-MCH-XXX...  │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │  选择 License    │                                               │
│  │  套餐/版本       │  → 决定 limits 数值                           │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │  生成 License    │                                               │
│  │  - license_key   │                                               │
│  │  - machine_code  │  ← 绑定机器码                                 │
│  │  - limits        │                                               │
│  │  - expires_at    │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │  私钥签名        │                                               │
│  │  signature       │  ← 防止篡改                                   │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  激活码: HFL-ACT-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX                   │
│           │                                                          │
│           │ 发送给客户                                               │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │  客户收到激活码  │                                               │
│  └──────────────────┘                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 3. 激活流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        License 激活流程                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  租户管理员操作                                                      │
│  ┌──────────────────┐                                               │
│  │  输入激活码      │                                               │
│  │  HFL-ACT-XXX...  │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────────────────────────────┐                       │
│  │  后端验证                                │                       │
│  │                                          │                       │
│  │  1. 解码激活码                           │                       │
│  │     └─ 解析 JSON 数据                    │                       │
│  │                                          │                       │
│  │  2. 验证签名                             │                       │
│  │     └─ 用公钥验证，防止篡改              │                       │
│  │                                          │                       │
│  │  3. 验证机器码                           │                       │
│  │     └─ 激活码中的 machine_code           │                       │
│  │        必须等于                          │                       │
│  │        当前机器 + 当前租户 + 当前用户     │                       │
│  │                                          │                       │
│  │  4. 检查是否已激活                       │                       │
│  │     └─ 同一 machine_code 只能激活一次    │                       │
│  │                                          │                       │
│  └──────────────┬───────────────────────────┘                       │
│                 │                                                    │
│         ┌───────┴───────┐                                           │
│         │               │                                           │
│      验证通过        验证失败                                         │
│         │               │                                           │
│         ▼               ▼                                           │
│  ┌──────────────┐ ┌──────────────────────────┐                      │
│  │ 保存 License │ │ 返回错误                  │                      │
│  │ 状态=active  │ │ - "签名验证失败"          │                      │
│  │              │ │ - "机器码不匹配"          │                      │
│  │ 绑定机器码   │ │ - "已激活过"              │                      │
│  │ 绑定租户     │ │ - "激活码已过期"          │                      │
│  └──────────────┘ └──────────────────────────┘                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 4. License 限制项

| 限制项 | 字段名 | 说明 |
|--------|--------|------|
| 租户数量 | `max_tenants` | 系统最大租户数 |
| 用户数量 | `max_users` | 所有租户总用户数 |
| Proxy 数量 | `max_proxies` | 所有租户总 Proxy 数 |
| 存储容量 | `max_storage_gb` | 总存储容量 (GB) |
| Gateway 数量 | `max_gateways` | Gateway 节点数 |
| AI Insights 次数 | `ai_insights_quota` | 每月免费 AI 查询次数 |
| 备份任务数 | `max_backup_tasks` | 同时运行的最大任务数 |
| 恢复任务数 | `max_recovery_tasks` | 同时运行的最大任务数 |
| 源端资源数 | `max_source_resources` | 备份源数量 |
| 备份策略数 | `max_policies` | 策略规则数量 |
| 备份仓库数 | `max_repositories` | Kopia 仓库数量 |

## 5. 数据模型

```python
class License(models.Model):
    """License 授权模型"""
    
    # 基本信息
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    license_key = models.CharField(max_length=64, unique=True)  # License 唯一标识
    
    # 绑定信息
    machine_code = models.CharField(max_length=64, unique=True)  # 绑定的机器码
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # 绑定的租户
    activated_by = models.ForeignKey(User, on_delete=models.CASCADE)  # 激活的用户
    
    # 数量限制
    max_tenants = models.IntegerField(default=1)
    max_users = models.IntegerField(default=10)
    max_proxies = models.IntegerField(default=5)
    max_storage_gb = models.IntegerField(default=100)
    max_gateways = models.IntegerField(default=1)
    ai_insights_quota = models.IntegerField(default=100)  # 每月免费次数
    max_backup_tasks = models.IntegerField(default=10)
    max_recovery_tasks = models.IntegerField(default=10)
    max_source_resources = models.IntegerField(default=20)
    max_policies = models.IntegerField(default=50)
    max_repositories = models.IntegerField(default=5)
    
    # 时间信息
    issued_at = models.DateTimeField()  # 颁发时间
    expires_at = models.DateTimeField(null=True, blank=True)  # 过期时间（null=永久）
    activated_at = models.DateTimeField(auto_now_add=True)  # 激活时间
    
    # 安全
    signature = models.TextField()  # 签名
    status = models.CharField(choices=[
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ], default='active')
    
    @property
    def is_valid(self):
        """检查 License 是否有效"""
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
    
    def verify_machine(self, request):
        """验证当前机器是否匹配"""
        current_code = generate_machine_code(request)
        return self.machine_code == current_code
```

## 6. API 设计

```
# 1. 导出机器码（租户管理员）
GET /api/v1/license/machine-code/
Response: {
  "machine_code": "HFL-MCH-XXXX-XXXX-XXXX-XXXX",
  "components": {
    "mac": "00:1a:2b:3c:4d:5e",
    "tenant_id": "uuid",
    "user_id": "uuid"
  }
}

# 2. 激活 License（租户管理员）
POST /api/v1/license/activate/
Request: {
  "activation_code": "HFL-ACT-XXXXXXXXXXXXXXXX"
}
Response: {
  "success": true,
  "license": {
    "license_key": "HFL-PRO-2026-XXXX",
    "expires_at": "2027-01-01",
    "limits": { ... }
  }
}

# 3. 查看 License 状态
GET /api/v1/license/status/
Response: {
  "is_valid": true,
  "license": { ... },
  "usage": {
    "tenants": 2,
    "users": 50,
    "proxies": 10,
    ...
  }
}

# 4. 管理员 - 生成 License（销售端，独立工具）
# 这是一个离线工具，不是 API
```

## 7. 安全要点

1. **签名验证**：激活码必须用私钥签名，后端用公钥验证
2. **机器码唯一**：同一机器码只能激活一次
3. **租户隔离**：激活码绑定租户，无法跨租户使用
4. **过期检查**：每次使用都检查过期时间
5. **使用量检查**：创建资源时检查 License 限制

## 8. 使用量检查示例

```python
def check_license_limit(tenant, limit_type, increment=1):
    """检查 License 限制"""
    license = License.get_active_license(tenant)
    
    if not license or not license.is_valid:
        raise LicenseError("No valid license")
    
    # 获取当前使用量
    usage = get_current_usage(tenant)
    
    # 检查限制
    limits = {
        'users': (usage['users'], license.max_users),
        'proxies': (usage['proxies'], license.max_proxies),
        'storage_gb': (usage['storage_gb'], license.max_storage_gb),
        # ...
    }
    
    current, limit = limits[limit_type]
    if current + increment > limit:
        raise LicenseError(
            f"License limit exceeded: {limit_type} "
            f"(current: {current}, limit: {limit})"
        )
    
    return True
```
