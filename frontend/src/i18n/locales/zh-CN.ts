export default {
  // Navigation
  nav: {
    dashboard: '仪表盘',
    nodes: '节点管理',
    backupTasks: '备份任务',
    recoveryTasks: '恢复任务',
    repository: '存储库',
    policies: '策略管理',
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
    inactive: '未激活',
    pending: '待处理',
    all: '全部',
    total: '总计',
    name: '名称',
    status: '状态',
    type: '类型',
    date: '日期',
    actions: '操作',
    details: '详情',
    description: '描述',
    required: '必填',
    optional: '可选'
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
    createAccount: '创建账号',
    welcomeBack: '欢迎回来',
    loginSubtitle: '登录账号以继续',
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
      activeTasks: '进行中任务',
      storageUsed: '存储使用量',
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

    types: {
      source_proxy: '源端代理',
      target_gateway: '目标网关'
    },

    status: {
      pending: '待激活',
      active: '在线',
      inactive: '离线',
      error: '错误',
      maintenance: '维护中'
    },

    details: {
      hostname: '主机名',
      port: '端口',
      protocol: '协议',
      os: '操作系统',
      version: '版本',
      lastHeartbeat: '最后心跳',
      uptime: '运行时间',
      apiKey: 'API密钥',
      capabilities: '能力'
    },

    form: {
      addSourceProxy: '添加源端代理',
      addTargetGateway: '添加目标网关',
      editNode: '编辑节点',
      deleteNode: '删除节点',
      deleteConfirm: '确定要删除此节点吗？'
    },

    actions: {
      viewDetails: '查看详情',
      edit: '编辑',
      delete: '删除',
      setMaintenance: '设为维护',
      setActive: '设为活跃',
      viewHeartbeats: '查看心跳',
      copyApiKey: '复制API密钥'
    },

    empty: {
      title: '暂无节点',
      description: '添加您的第一个源端代理或目标网关以开始使用'
    }
  },

  // Backup Tasks
  backupTasks: {
    title: '备份任务',
    subtitle: '管理备份操作',
    createTask: '创建备份任务',

    types: {
      full: '完全备份',
      incremental: '增量备份',
      differential: '差异备份'
    },

    status: {
      pending: '待执行',
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
      repository: '存储库',
      sourcePaths: '源路径',
      excludePaths: '排除路径',
      schedule: '计划',
      runNow: '立即执行',
      scheduleForLater: '计划稍后执行'
    },

    progress: {
      files: '文件数',
      size: '大小',
      progress: '进度',
      speed: '速度',
      eta: '预计剩余',
      errors: '错误',
      warnings: '警告'
    },

    actions: {
      viewDetails: '查看详情',
      start: '开始',
      pause: '暂停',
      resume: '继续',
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
    newRecovery: '新建恢复',
    node: '目标节点',
    repository: '存储库',
    snapshot: '快照',
    types: {
      original_location: '原位置恢复',
      new_location: '新位置恢复'
    },
    status: {
      pending: '等待中',
      queued: '排队中',
      running: '运行中',
      paused: '已暂停',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消'
    },
    originalLocation: '恢复到原位置',
    newLocation: '恢复到新位置',
    targetPath: '目标路径',
    priority: '优先级',
    priorityLow: '低',
    priorityNormal: '普通',
    priorityHigh: '高',
    priorityCritical: '紧急',
    start: '开始',
    cancel: '取消',
    error: '错误',
    createdAt: '创建时间',
    completedAt: '完成时间',
    totalTasks: '总任务数',
    pendingTasks: '等待中',
    completedTasks: '已完成',
    failedTasks: '失败'
  },

  // Repository
  repository: {
    title: '备份存储库',
    subtitle: '管理备份存储',

    stats: {
      totalSize: '总容量',
      usedSpace: '已用空间',
      availableSpace: '可用空间',
      snapshots: '快照数',
      lastBackup: '最后备份'
    },

    form: {
      addRepository: '添加存储库',
      editRepository: '编辑存储库',
      repositoryName: '存储库名称',
      repositoryType: '存储库类型',
      connectionString: '连接字符串',
      capacity: '容量',
      retention: '保留策略'
    },

    types: {
      local: '本地存储',
      s3: 'S3兼容存储',
      azure: 'Azure Blob',
      gcs: 'Google Cloud Storage',
      b2: 'Backblaze B2'
    },

    empty: {
      title: '暂无存储库',
      description: '添加备份存储库以存储备份数据'
    }
  },

  // Policies
  policies: {
    title: '备份策略',
    subtitle: '定义备份规则和计划',

    form: {
      addPolicy: '添加策略',
      editPolicy: '编辑策略',
      policyName: '策略名称',
      description: '描述',
      schedule: '计划',
      retention: '保留',
      compression: '压缩',
      encryption: '加密'
    },

    empty: {
      title: '暂无策略',
      description: '创建备份策略以自动化备份操作'
    }
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
      changes: '此文件夹发生了什么变化？',
      summary: '总结此目录中的文档'
    },

    results: {
      title: '结果',
      files: '文件',
      folders: '文件夹',
      matches: '匹配项',
      relevance: '相关性',
      preview: '预览',
      download: '下载'
    },

    empty: {
      title: '开始探索',
      description: '使用自然语言询问关于备份数据的问题'
    }
  },

  // Audit Log
  auditLog: {
    title: '审计日志',
    subtitle: '追踪系统活动',

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
      resourceId: '资源ID',
      details: '详情',
      ipAddress: 'IP地址'
    },

    actions: {
      export: '导出',
      filter: '筛选'
    },

    empty: {
      title: '暂无审计日志',
      description: '系统活动将显示在这里'
    }
  },

  // Settings
  settings: {
    title: '设置',
    subtitle: '管理您的账户和偏好设置',

    sections: {
      profile: '个人资料',
      security: '安全',
      notifications: '通知',
      apiTokens: 'API令牌',
      appearance: '外观',
      language: '语言'
    },

    profile: {
      title: '个人信息',
      firstName: '名字',
      lastName: '姓氏',
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
    notFound: '未找到资源',
    unauthorized: '您无权执行此操作',
    serverError: '服务器错误，请稍后重试',
    validation: '请检查输入',
    required: '此字段为必填项',
    invalidEmail: '请输入有效的邮箱地址',
    passwordTooShort: '密码至少8个字符',
    passwordMismatch: '两次输入的密码不一致'
  },

  // Confirmations
  confirmations: {
    delete: '确定要删除此项目吗？',
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
    minutesAgo: '{n}分钟前',
    hoursAgo: '{n}小时前',
    daysAgo: '{n}天前',
    weeksAgo: '{n}周前',
    monthsAgo: '{n}月前',
    yearsAgo: '{n}年前'
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
