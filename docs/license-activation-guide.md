# License 激活流程完整指南

## 概述

HyperFileLens 使用机器绑定 License 机制，确保每个 License 只能在指定的环境和租户中使用。

## 激活流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         License 激活流程                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 获取机器码                                                           │
│     ┌──────────────┐                                                    │
│     │ 平台管理员    │ ──▶ License 管理页面 ──▶ 获取机器码                  │
│     └──────────────┘                                                    │
│              │                                                          │
│              ▼                                                          │
│     生成: HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5                   │
│     (128位，绑定: 机器硬件标识 + 租户ID)                                  │
│              │                                                          │
│              ▼                                                          │
│     发送给销售团队                                                       │
│                                                                         │
│  2. 生成激活码                                                           │
│     ┌──────────────┐                                                    │
│     │ 销售团队      │ ──▶ license_generator.py                          │
│     └──────────────┘                                                    │
│              │                                                          │
│              ▼                                                          │
│     $ python scripts/license_generator.py \                             │
│         --machine-code HFL-MCH-... \                                    │
│         --tier pro                                                      │
│              │                                                          │
│              ▼                                                          │
│     生成: HFL-ACT-eyJsaWNlbnNlX2tleSI6...                               │
│     (包含: License Key + 机器码 + 配额 + 签名)                            │
│              │                                                          │
│              ▼                                                          │
│     发送给客户                                                           │
│                                                                         │
│  3. 激活 License                                                         │
│     ┌──────────────┐                                                    │
│     │ 平台管理员    │ ──▶ License 管理页面 ──▶ 激活 License               │
│     └──────────────┘                                                    │
│              │                                                          │
│              ▼                                                          │
│     输入激活码                                                           │
│              │                                                          │
│              ▼                                                          │
│     验证: 机器码匹配 + 签名有效 + 未过期                                   │
│              │                                                          │
│              ▼                                                          │
│     License 绑定到租户，激活成功                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 机器码组成

机器码确保 License 只能在特定环境使用：

```
机器码 = SHA256(硬件标识 + 租户ID)[:32]

格式: HFL-MCH-XXXX-XXXX-XXXX-XXXX
```

### 硬件标识优先级

| 优先级 | 标识符 | 说明 |
|--------|--------|------|
| 1 | 云平台实例 ID | AWS/GCP/Azure 实例 ID |
| 2 | 主板 UUID | 物理服务器 DMI UUID |
| 3 | 磁盘序列号 | 启动盘序列号 |
| 4 | 混合标识符 | MAC + 主机名（兜底） |

### 租户绑定

- 机器码绑定到**租户**，而非用户
- 同一租户的多个管理员可共享 License
- 不同租户的机器码完全不同

## 激活码组成

```
激活码 = Base64(JSON({
    "license_key": "HFL-PRO-2026-XXXXXXXX",
    "machine_code": "HFL-MCH-XXXX-XXXX-XXXX-XXXX",
    "limits": {
        "max_tenants": 5,
        "max_users": 100,
        ...
    },
    "issued_at": "2026-04-29T03:50:25+00:00",
    "expires_at": "2027-04-29T03:50:25+00:00",
    "signature": "HMAC-SHA256签名"
}))

格式: HFL-ACT-base64编码...
```

### 签名验证

- 使用共享密钥 `LICENSE_SECRET_KEY` 生成签名
- 后端验证签名确保激活码未被篡改
- **密钥必须保密**，只在后端和生成器中使用

## License 类型

| 类型 | 有效期 | 适用场景 |
|------|--------|----------|
| trial | 30天 | 试用评估 |
| pro | 1年 | 专业版 |
| enterprise | 1年 | 企业版 |
| perpetual | 永久 | 永久授权 |

## 配额限制项

| 限制项 | 说明 |
|--------|------|
| max_tenants | 租户数量 |
| max_users | 用户数量 |
| max_proxies | Proxy 数量 |
| max_storage_gb | 存储容量 (GB) |
| max_gateways | Gateway 数量 |
| ai_insights_quota | AI Insights 月度免费次数 |
| max_backup_tasks | 备份任务数量 |
| max_recovery_tasks | 恢复任务数量 |
| max_source_resources | 源端资源数量 |
| max_policies | 备份策略数量 |
| max_repositories | 备份仓库数量 |

## 使用 license_generator.py

### 预设套餐（快速生成）

```bash
# 试用版 (30天，基础配额)
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier trial

# 专业版 (1年，中等配额)
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier pro

# 企业版 (1年，高级配额)
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier enterprise

# 永久版 (永久有效，最高配额)
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier perpetual
```

### 自定义配额（灵活配置）

```bash
# 在套餐基础上覆盖特定配额
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier pro \
    --max-users 200 \
    --max-proxies 50 \
    --max-storage-gb 2000

# 自定义有效期（天数）
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier pro \
    --valid-days 730  # 2年

# 永久有效
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier enterprise \
    --perpetual
```

### 完全自定义（无预设套餐）

```bash
# 不使用预设套餐，完全自定义所有配额
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier custom \
    --max-tenants 10 \
    --max-users 500 \
    --max-proxies 100 \
    --max-storage-gb 5000 \
    --max-gateways 5 \
    --ai-insights-quota 5000 \
    --max-backup-tasks 200 \
    --max-recovery-tasks 200 \
    --max-source-resources 100 \
    --max-policies 500 \
    --max-repositories 20 \
    --valid-days 365
```

### 可配置参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--tier` | 套餐类型 | trial, pro, enterprise, perpetual, custom |
| `--valid-days` | 有效期（天数） | 365, 730 |
| `--perpetual` | 永久有效 | 标志参数，无需值 |
| `--max-tenants` | 最大租户数 | 10 |
| `--max-users` | 最大用户数 | 500 |
| `--max-proxies` | 最大代理数 | 100 |
| `--max-storage-gb` | 最大存储容量(GB) | 5000 |
| `--max-gateways` | 最大网关数 | 5 |
| `--ai-insights-quota` | AI Insights配额 | 5000 |
| `--max-backup-tasks` | 最大备份任务数 | 200 |
| `--max-recovery-tasks` | 最大恢复任务数 | 200 |
| `--max-source-resources` | 最大源端资源数 | 100 |
| `--max-policies` | 最大策略数 | 500 |
| `--max-repositories` | 最大仓库数 | 20 |
| `--output json` | JSON格式输出 | 便于脚本处理 |

### 输出格式

```bash
# 文本格式（默认）
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier pro

# JSON格式（便于脚本处理）
python scripts/license_generator.py \
    --machine-code HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5 \
    --tier pro \
    --output json
```

### 验证激活码

```bash
# 验证激活码是否有效
python scripts/license_generator.py \
    --verify "HFL-ACT-eyJsaWNlbnNlX2tleSI6..."
```

### 输出示例

```
============================================================
HyperFileLens License Generator
============================================================

License Key:    HFL-PRO-2026-D0802BC293CD6A52
Tier:           Professional
Machine Code:   HFL-MCH-5F2086D3-BC4DA929-EC6547F1-14042CD5
Valid Days:     365
Expires At:     2027-04-29T03:50:25+00:00
Issued At:      2026-04-29T03:50:25+00:00

Limits (Customized):
  max_users: 200        ← 自定义覆盖
  max_proxies: 50       ← 自定义覆盖
  max_storage_gb: 1000  ← 套餐默认

------------------------------------------------------------
ACTIVATION CODE:
------------------------------------------------------------
HFL-ACT-eyJsaWNlbnNlX2tleSI6...
------------------------------------------------------------

Send the ACTIVATION CODE above to the customer.

Verifying generated code...
✓ Code verification: PASSED
```

## API 接口

### 获取机器码

```
POST /api/v1/licenses/machine_code/

Response:
{
    "machine_code": "HFL-MCH-1089-817D-3A31-351A",
    "components": {
        "machine_id": "fallback:00:16:3E:XX:XX:XX:hostname",
        "tenant_id": "4567f7f1-0c08-44fd-9825-7eaa1871da01"
    }
}
```

### 激活 License

```
POST /api/v1/licenses/activate/
Content-Type: application/json

{
    "activation_code": "HFL-ACT-eyJsaWNlbnNlX2tleSI6..."
}

Response:
{
    "success": true,
    "message": "License activated successfully",
    "license": {
        "id": "uuid",
        "license_key": "HFL-PRO-2026-XXXXXXXX",
        "status": "active",
        "is_valid": true,
        ...
    }
}
```

### 获取当前 License

```
GET /api/v1/licenses/current/

Response:
{
    "is_valid": true,
    "license": {...},
    "limits": {...},
    "days_until_expiry": 364
}
```

## 安全注意事项

1. **保护密钥**：`LICENSE_SECRET_KEY` 必须保密
2. **机器码唯一**：每个租户的机器码唯一
3. **激活码一次性**：激活码使用后失效
4. **防篡改**：签名验证确保激活码完整性
5. **环境绑定**：License 只能在生成机器码的环境使用
