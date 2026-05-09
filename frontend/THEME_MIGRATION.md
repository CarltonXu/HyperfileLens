# Dark Mode 主题迁移指南

## 迁移前 vs 迁移后

### ❌ 迁移前：手动添加 dark 类

```vue
<!-- 繁琐的实现 -->
<div class="bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
<div class="text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50">
```

### ✅ 迁移后：使用语义化类

```vue
<!-- 简洁的实现 -->
<div class="card">
<div class="text-foreground-secondary hover:bg-hover">
```

## 可用的语义化类

### 背景类
- `bg-background` - 主背景
- `bg-background-secondary` - 次要背景
- `bg-background-tertiary` - 三级背景
- `bg-card` - 卡片背景
- `bg-card-secondary` - 卡片次要背景
- `bg-hover` - 悬停背景

### 文字类
- `text-foreground` - 主文字
- `text-foreground-secondary` - 次要文字
- `text-foreground-tertiary` - 三级文字
- `text-foreground-muted` - 静音文字

### 边框类
- `border-border` - 主边框
- `border-border-secondary` - 次要边框

### 颜色类
- `text-primary` - 主色文字
- `bg-primary` - 主色背景
- `text-success` - 成功文字
- `bg-success` - 成功背景
- `text-warning` - 警告文字
- `bg-warning` - 警告背景
- `text-danger` - 危险文字
- `bg-danger` - 危险背景

### 组件类
- `card` - 卡片容器
- `card-header` - 卡片头部
- `card-body` - 卡片内容
- `table` - 表格容器
- `btn` - 按钮基础样式
- `btn-primary` - 主按钮
- `btn-secondary` - 次要按钮
- `btn-ghost` - 幽灵按钮
- `badge` - 徽章
- `badge-success` - 成功徽章
- `badge-warning` - 警告徽章
- `badge-danger` - 危险徽章
- `badge-info` - 信息徽章

## 常用模式

### 1. 容器
```vue
<!-- 迁移前 -->
<div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">

<!-- 迁移后 -->
<div class="card p-4">
```

### 2. 表格行
```vue
<!-- 迁移前 -->
<tr class="bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/50">
  <td class="text-slate-700 dark:text-slate-200">
  <td class="text-slate-600 dark:text-slate-300">

<!-- 迁移后 -->
<tr class="hover:bg-hover">
  <td class="text-foreground">
  <td class="text-foreground-secondary">
```

### 3. 按钮
```vue
<!-- 迁移前 -->
<button class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg">
<button class="text-slate-400 hover:text-blue-600 hover:bg-blue-50 px-2 py-2 rounded-lg">

<!-- 迁移后 -->
<button class="btn btn-primary">
<button class="btn btn-ghost text-primary hover:bg-hover">
```

### 4. 表单输入
```vue
<!-- 迁移前 -->
<input class="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder-slate-400">
<label class="text-sm font-medium text-slate-700 dark:text-slate-300">

<!-- 迁移后 -->
<input class="input">
<label class="label">
```

### 5. 徽章/标签
```vue
<!-- 迁移前 -->
<span class="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
<span class="px-2 py-1 rounded-full text-xs font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400">

<!-- 迁移后 -->
<span class="badge badge-success">
<span class="badge badge-warning">  <!-- 自动支持 dark 模式 -->
```

### 6. 状态文字
```vue
<!-- 迁移前 -->
<p class="text-sm text-slate-500 dark:text-slate-400">
<h3 class="text-lg font-semibold text-slate-800 dark:text-white">

<!-- 迁移后 -->
<p class="text-sm text-foreground-secondary">
<h3 class="text-lg font-semibold text-foreground">
```

## 渐进式迁移

### 方案 1：立即迁移（推荐）
批量替换所有的 `bg-white` → `bg-card`，`text-slate-700` → `text-foreground` 等。

### 方案 2：渐进迁移
1. 新代码使用语义化类
2. 修改旧代码时顺便迁移
3. 分批迁移各个组件

## 常用映射表

| 旧类 | 新类 |
|------|------|
| `bg-white` | `bg-card` |
| `bg-slate-50` | `bg-background-secondary` |
| `bg-slate-100` | `bg-background-tertiary` |
| `bg-slate-800` | `bg-background-secondary` (dark) |
| `text-slate-700` | `text-foreground` |
| `text-slate-600` | `text-foreground-secondary` |
| `text-slate-500` | `text-foreground-secondary` |
| `text-slate-400` | `text-foreground-muted` |
| `border-slate-200` | `border-border` |
| `border-slate-300` | `border-border-secondary` |
| `hover:bg-slate-50` | `hover:bg-hover` |
| `hover:bg-slate-100` | `hover:bg-hover-secondary` |

## 测试

修改完成后，测试以下功能：

1. **主题切换**：切换 light/dark 模式
2. **所有页面**：确保所有页面都正确显示
3. **表单元素**：输入框、下拉框等
4. **表格**：表格行、表头等
5. **按钮**：所有类型的按钮

## 注意事项

1. **保留 Tailwind 原色**：primary、success、warning、danger 等原色仍然可以使用
2. **兼容性**：旧的 `dark:` 类仍然有效，可以混合使用
3. **自定义样式**：如果需要特殊样式，仍然可以使用 Tailwind 原色