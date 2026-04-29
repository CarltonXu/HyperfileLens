# License 机器绑定安全方案

## 问题分析

当前实现的问题是：License 在生成时不包含机器信息，任何拿到 License 的人都可以在自己机器上激活使用。这违背了"机器绑定"的初衷。

## 三种正确的绑定方案

### 方案 A：预绑定模式（推荐 - 最安全）

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. 客户提供机器指纹                                                 │
│     ┌──────────────────┐                                            │
│     │  客户环境        │                                            │
│     │  运行命令获取    │                                            │
│     │  机器指纹        │                                            │
│     └────────┬─────────┘                                            │
│              │                                                       │
│              │ 发送给销售                                            │
│              ▼                                                       │
│  2. 销售生成绑定 License                                            │
│     ┌──────────────────┐                                            │
│     │  License 生成    │                                            │
│     │  - 其他信息      │                                            │
│     │  - machine_id ✓ │  ← 包含机器指纹                             │
│     │  - signature     │  ← 签名包含 machine_id                      │
│     └────────┬─────────┘                                            │
│              │                                                       │
│              │ 发送给客户                                            │
│              ▼                                                       │
│  3. 客户导入并验证                                                   │
│     ┌──────────────────┐                                            │
│     │  导入 License    │                                            │
│     │  验证签名        │                                            │
│     │  检查 machine_id │  ← 必须匹配当前机器                         │
│     │  == 当前机器?    │                                            │
│     └────────┬─────────┘                                            │
│              │                                                       │
│         ┌────┴────┐                                                 │
│         │         │                                                 │
│      匹配 ✓    不匹配 ❌                                             │
│         │         │                                                 │
│         ▼         ▼                                                 │
│      导入成功   导入失败                                             │
│      可直接使用  "此 License 绑定到其他机器"                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

优点：最安全，License 一旦生成就绑定特定机器
缺点：需要客户先提供机器指纹
```

### 方案 B：双向激活码模式（灵活）

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. 客户导入 License                                                │
│     ┌──────────────────┐                                            │
│     │  导入 License    │                                            │
│     │  status=inactive │                                            │
│     │  生成激活请求码  │                                            │
│     │  = machine_id    │                                            │
│     │  + license_key   │                                            │
│     └────────┬─────────┘                                            │
│              │                                                       │
│              │ 发送给销售                                            │
│              ▼                                                       │
│  2. 销售生成激活确认码                                              │
│     ┌──────────────────┐                                            │
│     │  验证请求码      │                                            │
│     │  签名确认码      │                                            │
│     │  = sign(         │                                            │
│     │    machine_id +  │                                            │
│     │    license_key   │                                            │
│     │  )               │                                            │
│     └────────┬─────────┘                                            │
│              │                                                       │
│              │ 发送给客户                                            │
│              ▼                                                       │
│  3. 客户输入确认码激活                                              │
│     ┌──────────────────┐                                            │
│     │  验证确认码签名  │                                            │
│     │  激活 License    │                                            │
│     │  status=active   │                                            │
│     └──────────────────┘                                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

优点：License 可以提前生成，激活时才绑定
缺点：需要销售介入每次激活
```

### 方案 C：在线激活模式（便捷）

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. 客户导入 License                                                │
│     ┌──────────────────┐                                            │
│     │  导入 License    │                                            │
│     │  status=inactive │                                            │
│     └────────┬─────────┘                                            │
│              │                                                       │
│              ▼                                                       │
│  2. 点击"在线激活"                                                   │
│     ┌──────────────────┐                                            │
│     │  发送到激活服务器│                                            │
│     │  - license_key   │                                            │
│     │  - machine_id    │                                            │
│     └────────┬─────────┘                                            │
│              │                                                       │
│              ▼                                                       │
│  3. 激活服务器验证                                                  │
│     ┌──────────────────┐                                            │
│     │  检查 License    │                                            │
│     │  是否已激活？    │                                            │
│     └────────┬─────────┘                                            │
│              │                                                       │
│         ┌────┴────┐                                                 │
│         │         │                                                 │
│      未激活    已激活                                                │
│         │         │                                                 │
│         ▼         ▼                                                 │
│     记录绑定   检查 machine_id                                      │
│     返回成功   匹配? → 成功 : 失败                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

优点：自动化，用户体验好
缺点：需要联网，激活服务器可能成为攻击目标
```

## 推荐实现

结合方案 A 和 B，提供两种模式：

1. **标准模式（预绑定）**：客户先提供机器指纹，销售生成绑定 License
2. **灵活模式（激活码）**：License 可导入，但需要销售确认才能激活

## 代码改进建议

### 1. 添加机器指纹获取工具

```python
# backend/licenses/management/commands/get_machine_fingerprint.py
from django.core.management.base import BaseCommand
from licenses.crypto import HardwareFingerprint

class Command(BaseCommand):
    help = 'Get current machine fingerprint for license binding'
    
    def handle(self, *args, **options):
        fingerprint = HardwareFingerprint.get_machine_id()
        self.stdout.write(self.style.SUCCESS(f'Machine Fingerprint: {fingerprint}'))
```

### 2. License 导入时验证预绑定

```python
# 在 License.import_license 中添加
def import_license(cls, encoded_license: str) -> 'License':
    license_data, signature = LicenseEncoder.decode(encoded_license)
    
    # 验证签名
    if not LicenseSigner.verify_signature(license_data, signature):
        raise ValueError("License signature verification failed")
    
    # 检查预绑定
    pre_bound_machine = license_data.get("machine_id")
    if pre_bound_machine:
        current_machine = HardwareFingerprint.get_machine_id()
        if pre_bound_machine != current_machine:
            raise ValueError(
                f"This license is bound to another machine. "
                f"Expected: {pre_bound_machine[:16]}... "
                f"Current: {current_machine[:16]}..."
            )
        # 预绑定且匹配，直接激活
        initial_status = cls.LicenseStatus.ACTIVE
    else:
        # 未预绑定，需要后续激活
        initial_status = cls.LicenseStatus.INACTIVE
    
    # ... 创建 License
```

### 3. 激活时需要确认码（可选）

```python
# 新增激活确认码验证
@action(detail=True, methods=['post'])
def activate(self, request, pk=None):
    license = self.get_object()
    
    # 方案 1：直接激活（当前实现）
    # 任何人都可以激活
    
    # 方案 2：需要确认码
    confirmation_code = request.data.get('confirmation_code')
    if not confirmation_code:
        # 返回激活请求码
        machine_id = HardwareFingerprint.get_machine_id()
        request_code = f"{license.license_key}:{machine_id}"
        return Response({
            'status': 'confirmation_required',
            'request_code': request_code,
            'message': 'Please contact sales with this request code to get confirmation code'
        })
    
    # 验证确认码
    if not verify_confirmation_code(license.license_key, confirmation_code):
        return Response({'error': 'Invalid confirmation code'}, status=400)
    
    # 激活
    license.activate()
    return Response({'status': 'activated'})
```

## 总结

| 方案 | 安全性 | 便捷性 | 适用场景 |
|------|--------|--------|----------|
| A 预绑定 | ⭐⭐⭐⭐⭐ | ⭐⭐ | 高安全要求，企业版 |
| B 激活码 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 中等安全要求，需要销售介入 |
| C 在线激活 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 有网络环境，SaaS 模式 |
| 当前实现 | ⭐⭐ | ⭐⭐⭐⭐⭐ | 不推荐，存在安全漏洞 |
