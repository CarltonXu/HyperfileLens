export default {
  // Navigation
  nav: {
    dashboard: '仪表盘',
    nodes: '节点管理',
    proxies: '代理管理',
    backupTasks: '备份任务',
    recoveryTasks: '恢复任务',
    repository: '目标存储仓库',
    sourceResources: '源端资源',
    policies: '备份策略',
    aiQuery: 'AI 查询',
    auditLog: '审计日志',
    settings: '设置',
    logout: '退出登录'
  },

  // Common
  common: {
    save: '保存',
    cancel: '取消',
    delete: '删除',
    edit: '编辑',
    create: '创建',
    add: '添加',
    remove: '移除',
    search: '搜索',
    filter: '筛选',
    reset: '重置',
    refresh: '刷新',
    download: '下载',
    upload: '上传',
    copy: '复制',
    copied: '已复制！',
    back: '返回',
    next: '下一步',
    previous: '上一步',
    loading: '加载中...',
    noData: '暂无数据',
    confirm: '确认',
    yes: '是',
    no: '否',
    enabled: '已启用',
    disabled: '已禁用',
    active: '活跃',
    inactive: '不活跃',
    pending: '待处理',
    all: '全部',
    total: '总计',
    name: '名称',
    status: '状态',
    type: '类型',
    role: '角色',
    date: '日期',
    actions: '操作',
    details: '详情',
    description: '描述',
    required: '必填',
    optional: '可选',
    settings: '设置',
    close: '关闭',
    never: '从未',
    justNow: '刚刚',
    minutesAgo: '分钟前',
    hoursAgo: '小时前',
    daysAgo: '天前'
  },

  // Auth
  auth: {
    login: '登录',
    logout: '退出登录',
    register: '注册',
    email: '邮箱',
    password: '密码',
    confirmPassword: '确认密码',
    rememberMe: '记住我',
    forgotPassword: '忘记密码？',
    createAccount: '创建账户',
    welcomeBack: '欢迎回来！',
    loginSubtitle: '登录您的账户以继续',
    invalidCredentials: '邮箱或密码错误',
    loginSuccess: '登录成功',
    logoutSuccess: '退出成功'
  },

  // Dashboard
  dashboard: {
    title: '仪表盘',
    welcome: '欢迎回来',
    subtitle: '系统概览',

    stats: {
      totalNodes: '节点总数',
      onlineNodes: '在线节点',
      activeTasks: '活动任务',
      storageUsed: '已用存储',
      totalBackups: '备份总数',
      successRate: '成功率'
    },

    recentActivity: '最近活动',
    quickActions: '快捷操作',
    systemStatus: '系统状态',

    actions: {
      newBackup: '新建备份',
      newRecovery: '新建恢复',
      viewNodes: '查看节点',
      viewReports: '查看报告'
    }
  },

  // Nodes
  nodes: {
    title: '节点管理',
    subtitle: '管理源端代理和目标网关',
    addNode: '添加节点',
    online: '在线',
    offline: '离线',
    checking: '检查中...',
    neverConnected: '从未连接',

    types: {
      source_proxy: '源端代理',
      target_gateway: '目标网关'
    },

    status: {
      pending: '待处理',
      active: '活跃',
      inactive: '不活跃',
      error: '错误',
      maintenance: '维护中'
    },

    detail: {
      connection: '连接地址',
      operatingSystem: '操作系统',
      lastHeartbeat: '最后心跳',
      uptime: '运行时间',
      cpuCores: 'CPU 核心数',
      memory: '内存',
      disk: '磁盘',
      version: '版本',
      credentials: '节点凭证',
      credentialsHint: '使用这些凭证在您的服务器上配置代理程序',
      recentHeartbeats: '最近心跳记录'
    },

    heartbeat: {
      time: '时间',
      cpu: 'CPU',
      memory: '内存',
      disk: '磁盘',
      tasks: '任务数'
    },

    form: {
      addSourceProxy: '添加源端代理',
      addTargetGateway: '添加目标网关',
      editNode: '编辑节点',
      deleteNode: '删除节点',
      deleteConfirm: '确定要删除此节点吗？',
      name: '节点名称',
      namePlaceholder: '例如：production-server-01',
      type: '节点类型',
      hostname: '主机名 / IP',
      port: '端口',
      protocol: '协议',
      os: '操作系统',
      heartbeatInterval: '心跳间隔（秒）',
      ipAddress: 'IP 地址',
      operatingSystem: '操作系统'
    },

    actions: {
      viewDetails: '查看详情',
      edit: '编辑',
      delete: '删除',
      setMaintenance: '设为维护',
      activate: '激活',
      setActive: '设为活跃',
      viewHeartbeats: '查看心跳',
      copyApiKey: '复制 API 密钥'
    },

    deleteConfirm: {
      title: '删除节点',
      message: '确定要删除节点 "{name}" 吗？此操作无法撤销。'
    },

    empty: {
      title: '暂无节点',
      description: '添加您的第一个源端代理或目标网关'
    }
  },

  // Proxies
  proxies: {
    title: '代理管理',
    subtitle: '管理 Agent 和 Sync 代理节点',
    installProxy: '安装代理',
    online: '在线',
    noConnection: '未连接',

    stats: {
      total: '代理总数',
      online: '在线',
      agent: 'Agent 代理',
      sync: 'Sync 代理'
    },

    roles: {
      agent: 'Agent 代理',
      sync: 'Sync 代理'
    },

    status: {
      active: '活跃',
      pending: '待安装',
      offline: '离线',
      error: '错误',
      maintenance: '维护中',
      installing: '安装中'
    },

    actions: {
      viewDetails: '查看详情',
      edit: '编辑',
      delete: '删除',
      setMaintenance: '设为维护',
      activate: '激活',
      regenerateToken: '重新生成令牌',
      regenerateTokenConfirm: '这将使当前令牌失效，代理需要重新配置。是否继续？',
      viewInstall: '查看安装命令',
      viewInstallDesc: '此代理尚未安装，点击查看安装命令'
    },

    form: {
      name: '代理名称',
      hostname: '主机名',
      heartbeatInterval: '心跳间隔（秒）',
      labels: '标签',
      capabilities: '能力'
    },

    detail: {
      hostname: '主机名',
      internalIp: '内部 IP',
      operatingSystem: '操作系统',
      version: '版本',
      kopiaVersion: 'Kopia 版本',
      uptime: '运行时间',
      lastHeartbeat: '最后心跳',
      registeredAt: '注册时间',
      heartbeatInterval: '心跳间隔',
      capabilities: '能力',
      labels: '标签',
      systemInfo: '系统信息',
      currentlyOnline: '当前在线',
      currentlyOffline: '当前离线',
      recentTasks: '最近任务',
      noTasks: '暂无最近任务',
      noHeartbeats: '暂无心跳历史',
      proxyId: '代理 ID',
      role: '角色',
      status: '状态',
      owner: '所有者',
      createdAt: '创建时间',
      cpuCores: 'CPU 核心数',
      cpuUsage: 'CPU 使用率',
      memoryUsage: '内存使用率',
      diskUsage: '磁盘使用率',
      memoryTotal: '总内存',
      diskTotal: '总磁盘',
      memoryUsed: '已用内存',
      diskUsed: '已用磁盘',
      osVersion: '系统版本',
      websocketStatus: 'WebSocket 状态',
      connectionIp: '连接 IP',
      notInstalled: '未安装',
      installTokenUsed: '安装令牌已使用',
      installTokenNotUsed: '安装令牌未使用',
      total: '总计',
      pendingHint: '代理尚未安装，请按照安装说明进行操作',
      basicInfo: '基础信息',
      tabs: {
        overview: '概览',
        tasks: '任务历史',
        heartbeats: '心跳记录',
        install: '安装信息',
        monitoring: '监控信息'
      },
      sections: {
        basicInfo: '基础信息',
        systemInfo: '系统信息',
        hardwareInfo: '硬件资源',
        networkInfo: '网络连接'
      }
    },

    monitoring: {
      '24hHeartbeats': '24h 心跳数',
      avgCpu: '平均 CPU',
      avgMemory: '平均内存',
      avgDisk: '平均磁盘',
      realtimeStatus: '实时状态',
      connectionInfo: '连接信息',
      websocketStatus: 'WebSocket 状态',
      connected: '已连接',
      disconnected: '已断开',
      heartbeatInterval: '心跳间隔'
    },

    tasks: {
      total: '总任务数',
      completed: '已完成',
      failed: '失败',
      running: '运行中',
      taskId: '任务 ID',
      type: '类型',
      status: '状态',
      progress: '进度',
      startTime: '开始时间',
      duration: '耗时'
    },

    heartbeats: {
      '24hCount': '24h 心跳数',
      avgCpu: '平均 CPU',
      avgMemory: '平均内存',
      avgDisk: '平均磁盘',
      time: '时间',
      cpu: 'CPU',
      memory: '内存',
      disk: '磁盘',
      uptime: '运行时间',
      activeTasks: '活动任务'
    },

    install: {
      title: '安装新代理',
      subtitle: '选择角色并生成安装命令',
      agentDescription: '运行在业务服务器（Windows/Linux/macOS）。读取本地文件系统，执行备份，上报状态。无挂载能力。',
      syncDescription: '运行在独立节点/跳板机。挂载 NAS，接入对象存储，提供统一数据接入点。',
      requirements: '系统要求',
      agentOS: 'Windows/Linux/macOS',
      agentCPU: '2 核心以上',
      agentMemory: '4GB 以上',
      agentDisk: '根据数据量',
      syncOS: 'Ubuntu 24.04 LTS',
      syncCPU: '4 核心以上',
      syncMemory: '16GB 以上',
      syncDisk: '500GB 以上缓存',
      infoTitle: '角色说明',
      infoDescription: 'Agent 代理安装在业务服务器上，备份本地数据。Sync 代理安装在跳板机，用于挂载和备份 NAS/对象存储等远程资源。',
      proxyName: '代理名称',
      namePlaceholder: '例如：prod-backup-proxy-01',
      targetOS: '目标操作系统',
      syncFixedOS: 'Ubuntu 24.04 LTS (固定)',
      syncFixedOSNote: 'Sync 代理需要运行在 Ubuntu 24.04 LTS 上以支持 NFS/SMB 挂载',
      labels: '标签（可选）',
      labelPlaceholder: '添加标签',
      generateCommand: '生成安装命令',
      generating: '生成中...',
      installCommand: '安装命令',
      downloadConfig: '下载配置',
      proxyId: '代理 ID',
      apiToken: 'API 令牌',
      ready: '安装准备就绪',
      readyDescription: '复制下面的命令在目标服务器上运行以安装代理。',
      step1Title: '在目标服务器上执行安装命令',
      step1Desc: '登录到目标服务器，将以下命令粘贴到终端中执行。安装脚本会自动下载并配置代理程序。',
      step1Text: '登录到目标服务器，将命令粘贴到终端执行',
      credentialsTitle: '请妥善保管以下凭证',
      credentialsDesc: '这些凭证用于代理与管理端的安全通信，安装完成后请保存备份。如需重新生成令牌，请在代理详情页操作。',
      proxyIdLabel: '代理 ID',
      proxyIdDesc: '代理的唯一标识符，用于识别和管理此代理节点',
      apiTokenLabel: 'API 令牌',
      apiTokenDesc: 'API 认证令牌，用于代理与管理端的安全通信',
      warningTitle: '代理尚未安装',
      warningText: '此代理已创建但尚未安装。请在目标服务器上运行安装命令完成安装。如需重新获取安装信息，请点击"重新生成令牌"按钮。',
      helpTitle: '安装说明：',
      help1: '安装完成后代理会自动连接到管理端',
      help2: '安装令牌为一次性使用，安装成功后将自动失效',
      help3: 'API 令牌用于代理的长期认证，请妥善保管',
      done: '完成',
      os: {
        linux: 'Linux',
        windows: 'Windows',
        macos: 'macOS'
      }
    },

    edit: {
      title: '编辑代理'
    },

    delete: {
      title: '删除代理',
      description: '确定要删除代理 "{name}" 吗？此操作无法撤销。',
      confirm: '确定要删除此代理吗？所有任务历史将丢失。'
    },

    empty: {
      title: '暂无已安装代理',
      description: '安装代理以开始管理备份节点'
    }
  },

  // Backup Tasks
  backupTasks: {
    title: '备份任务',
    subtitle: '管理备份操作',
    createTask: '创建备份任务',

    types: {
      full: '完整备份',
      incremental: '增量备份',
      differential: '差异备份'
    },

    status: {
      pending: '待处理',
      queued: '排队中',
      running: '运行中',
      paused: '已暂停',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消'
    },

    form: {
      taskName: '任务名称',
      taskType: '备份类型',
      sourceNode: '源节点',
      targetGateway: '目标网关',
      repository: '存储仓库',
      sourcePaths: '源路径',
      excludePaths: '排除路径',
      schedule: '调度',
      runNow: '立即运行',
      scheduleForLater: '稍后调度'
    },

    progress: {
      files: '文件',
      size: '大小',
      progress: '进度',
      speed: '速度',
      eta: '预计剩余时间',
      errors: '错误',
      warnings: '警告'
    },

    actions: {
      viewDetails: '查看详情',
      start: '启动',
      pause: '暂停',
      resume: '恢复',
      cancel: '取消',
      retry: '重试',
      delete: '删除',
      viewLogs: '查看日志'
    },

    empty: {
      title: '暂无备份任务',
      description: '创建您的第一个备份任务以保护数据'
    }
  },

  // Recovery Tasks
  recoveryTasks: {
    title: '恢复任务',
    subtitle: '管理数据恢复操作',
    createTask: '创建恢复任务',

    types: {
      original_location: '原位置',
      new_location: '新位置'
    },

    status: {
      pending: '待处理',
      queued: '排队中',
      running: '运行中',
      paused: '已暂停',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消'
    },

    form: {
      targetNode: '目标节点',
      repository: '存储仓库',
      snapshot: '快照',
      type: '恢复类型',
      targetPath: '目标路径',
      filePatterns: '文件模式',
      priority: '优先级'
    },

    progress: {
      progress: '进度',
      files: '个文件',
      size: '大小'
    },

    actions: {
      start: '启动',
      cancel: '取消',
      viewDetails: '查看详情'
    },

    empty: {
      title: '暂无恢复任务',
      description: '创建您的第一个恢复任务以恢复数据'
    }
  },

  // Repository
  repository: {
    title: '存储仓库',
    subtitle: '管理备份存储',

    stats: {
      total: '仓库总数',
      totalSize: '总大小',
      totalCapacity: '总容量',
      usedSpace: '已用空间',
      availableSpace: '可用空间',
      snapshots: '快照数',
      lastBackup: '最后备份'
    },

    form: {
      addRepository: '添加仓库',
      editRepository: '编辑仓库',
      repositoryName: '仓库名称',
      repositoryType: '仓库类型',
      connectionString: '连接字符串',
      capacity: '容量',
      retention: '保留策略',
      path: '路径'
    },

    types: {
      local: '本地',
      s3: 'S3 兼容',
      azure: 'Azure Blob',
      gcs: 'Google Cloud Storage',
      b2: 'Backblaze B2'
    },

    empty: {
      title: '暂无仓库',
      description: '添加备份仓库以存储备份数据'
    },

    confirmDelete: '确定要删除此仓库吗？'
  },

  // Source Resources
  sourceResources: {
    title: '源端资源',
    subtitle: '管理备份数据源（NAS、NFS、CIFS、对象存储、本地）',

    stats: {
      total: '资源总数',
      active: '活跃',
      mounted: '已挂载',
      error: '错误'
    },

    addResource: '添加源端资源',
    allTypes: '全部类型',
    allStatus: '全部状态',
    noBoundNode: '未绑定节点',
    notMounted: '未挂载',
    testConnection: '测试连接',
    mountStatus: '挂载状态',
    mountPoint: '挂载点',
    boundNode: '绑定节点',
    noResources: '暂无源端资源',
    noResourcesDesc: '添加源端资源以开始备份数据',
    deleteConfirm: '删除源端资源',
    deleteConfirmDesc: '确定要删除 "{name}" 吗？',

    status: {
      label: '状态',
      connected: '已连接',
      disconnected: '未连接',
      error: '错误'
    },

    form: {
      name: '名称',
      type: '资源类型',
      boundNode: '绑定节点',
      selectNode: '选择节点',
      server: '服务器',
      exportPath: '导出路径',
      share: '共享名称',
      endpoint: '端点 URL',
      bucket: '存储桶名称',
      region: '区域',
      accessKey: '访问密钥',
      secretKey: '秘密密钥',
      username: '用户名',
      password: '密码',
      path: '路径'
    }
  },

  // Policies
  policies: {
    title: '备份策略',
    subtitle: '定义备份规则和调度',

    stats: {
      total: '策略总数',
      enabled: '已启用',
      disabled: '已禁用'
    },

    form: {
      addPolicy: '添加策略',
      editPolicy: '编辑策略',
      policyName: '策略名称',
      description: '描述',
      schedule: '调度',
      scheduleType: '调度类型',
      retention: '保留天数',
      compression: '压缩',
      encryption: '加密',
      backupTask: '备份任务',
      time: '时间',
      nextRun: '下次运行'
    },

    scheduleTypes: {
      hourly: '每小时',
      daily: '每天',
      weekly: '每周',
      monthly: '每月',
      manual: '手动'
    },

    empty: {
      title: '暂无策略',
      description: '创建备份策略以自动化备份操作'
    },

    confirmDelete: '确定要删除此策略吗？'
  },

  // AI Query
  aiQuery: {
    title: 'AI 文件智能',
    subtitle: '搜索和分析备份数据',

    search: {
      placeholder: '询问关于备份数据的问题...',
      submit: '提问',
      examples: '示例查询'
    },

    examples: {
      contracts: '查找去年签署的所有合同',
      sensitive: '显示包含敏感数据的目录',
      changes: '此文件夹有什么变化？',
      summary: '总结此目录中的文档'
    },

    results: {
      title: '结果',
      files: '文件',
      folders: '文件夹',
      matches: '匹配',
      relevance: '相关性',
      preview: '预览',
      download: '下载'
    },

    empty: {
      title: '开始探索',
      description: '使用自然语言询问关于备份数据的问题'
    },

    clearConversation: '清空对话',
    analyzing: '正在分析备份数据...',

    tips: {
      title: '获取更好结果的提示',
      tip1: '具体说明文件类型或日期范围',
      tip2: '使用自然语言描述您的需求',
      tip3: '可以要求摘要或比较'
    }
  },

  // Audit Log
  auditLog: {
    title: '审计日志',
    subtitle: '跟踪系统活动',

    stats: {
      success: '成功',
      warning: '警告',
      failure: '失败'
    },

    filters: {
      user: '用户',
      action: '操作',
      resource: '资源',
      dateRange: '日期范围'
    },

    columns: {
      timestamp: '时间',
      user: '用户',
      action: '操作',
      resourceType: '资源类型',
      resourceId: '资源 ID',
      details: '详情',
      ipAddress: 'IP 地址'
    },

    actions: {
      export: '导出',
      filter: '筛选',
      backupCreate: '创建备份',
      backupExecute: '执行备份',
      recoveryCreate: '创建恢复'
    },

    empty: {
      title: '暂无审计日志',
      description: '系统活动将显示在这里'
    }
  },

  // Settings
  settings: {
    title: '设置',
    subtitle: '管理您的账户和偏好',

    sections: {
      profile: '个人资料',
      security: '安全设置',
      notifications: '通知',
      apiTokens: 'API 令牌',
      appearance: '外观',
      language: '语言'
    },

    profile: {
      title: '个人资料',
      firstName: '名',
      lastName: '姓',
      email: '邮箱',
      phone: '电话',
      avatar: '头像'
    },

    security: {
      title: '安全设置',
      changePassword: '修改密码',
      currentPassword: '当前密码',
      newPassword: '新密码',
      confirmPassword: '确认密码',
      sessions: '活跃会话',
      revokeSessions: '撤销所有会话'
    },

    appearance: {
      title: '外观',
      theme: '主题',
      light: '浅色',
      dark: '深色',
      system: '跟随系统'
    },

    language: {
      title: '语言',
      english: 'English',
      chinese: '中文'
    }
  },

  // Errors
  errors: {
    general: '发生错误',
    network: '网络错误，请检查您的连接',
    notFound: '资源未找到',
    unauthorized: '您没有权限执行此操作',
    serverError: '服务器错误，请稍后重试',
    validation: '请检查您的输入',
    required: '此字段为必填项',
    invalidEmail: '请输入有效的邮箱地址',
    passwordTooShort: '密码至少需要 8 个字符',
    passwordMismatch: '密码不匹配'
  },

  // Confirmations
  confirmations: {
    delete: '确定要删除此项吗？',
    cancel: '确定要取消此操作吗？',
    logout: '确定要退出登录吗？'
  },

  // Success messages
  success: {
    saved: '保存成功',
    deleted: '删除成功',
    created: '创建成功',
    updated: '更新成功',
    copied: '已复制到剪贴板',
    exported: '导出成功'
  },

  // Time
  time: {
    now: '刚刚',
    minutesAgo: '{n} 分钟前',
    hoursAgo: '{n} 小时前',
    daysAgo: '{n} 天前',
    weeksAgo: '{n} 周前',
    monthsAgo: '{n} 月前',
    yearsAgo: '{n} 年前'
  },

  // File sizes
  fileSize: {
    bytes: 'B',
    kilobytes: 'KB',
    megabytes: 'MB',
    gigabytes: 'GB',
    terabytes: 'TB'
  }
}
