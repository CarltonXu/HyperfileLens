export default {
  // Navigation
  nav: {
    dashboard: 'Dashboard',
    nodes: 'Nodes',
    backupTasks: 'Backup Tasks',
    recoveryTasks: 'Recovery Tasks',
    repository: 'Target Repository',
    sourceResources: 'Source Resources',
    policies: 'Policies',
    aiQuery: 'AI Query',
    auditLog: 'Audit Log',
    settings: 'Settings',
    logout: 'Logout'
  },

  // Common
  common: {
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    create: 'Create',
    add: 'Add',
    remove: 'Remove',
    search: 'Search',
    filter: 'Filter',
    reset: 'Reset',
    refresh: 'Refresh',
    download: 'Download',
    upload: 'Upload',
    copy: 'Copy',
    back: 'Back',
    next: 'Next',
    previous: 'Previous',
    loading: 'Loading...',
    noData: 'No data available',
    confirm: 'Confirm',
    yes: 'Yes',
    no: 'No',
    enabled: 'Enabled',
    disabled: 'Disabled',
    active: 'Active',
    inactive: 'Inactive',
    pending: 'Pending',
    all: 'All',
    total: 'Total',
    name: 'Name',
    status: 'Status',
    type: 'Type',
    date: 'Date',
    actions: 'Actions',
    details: 'Details',
    description: 'Description',
    required: 'Required',
    optional: 'Optional',
    settings: 'Settings',
    close: 'Close'
  },

  // Auth
  auth: {
    login: 'Login',
    logout: 'Logout',
    register: 'Register',
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm Password',
    rememberMe: 'Remember me',
    forgotPassword: 'Forgot password?',
    createAccount: 'Create an account',
    welcomeBack: 'Welcome back!',
    loginSubtitle: 'Sign in to your account to continue',
    invalidCredentials: 'Invalid email or password',
    loginSuccess: 'Login successful',
    logoutSuccess: 'Logout successful'
  },

  // Dashboard
  dashboard: {
    title: 'Dashboard',
    welcome: 'Welcome back',
    subtitle: 'Here is your system overview',

    stats: {
      totalNodes: 'Total Nodes',
      onlineNodes: 'Online Nodes',
      activeTasks: 'Active Tasks',
      storageUsed: 'Storage Used',
      totalBackups: 'Total Backups',
      successRate: 'Success Rate'
    },

    recentActivity: 'Recent Activity',
    quickActions: 'Quick Actions',
    systemStatus: 'System Status',

    actions: {
      newBackup: 'New Backup',
      newRecovery: 'New Recovery',
      viewNodes: 'View Nodes',
      viewReports: 'View Reports'
    }
  },

  // Nodes
  nodes: {
    title: 'Node Management',
    subtitle: 'Manage source proxies and target gateways',
    addNode: 'Add Node',
    online: 'Online',
    offline: 'Offline',
    checking: 'Checking...',
    neverConnected: 'Never connected',

    types: {
      source_proxy: 'Source Proxy',
      target_gateway: 'Target Gateway'
    },

    status: {
      pending: 'Pending',
      active: 'Active',
      inactive: 'Inactive',
      error: 'Error',
      maintenance: 'Maintenance'
    },

    detail: {
      connection: 'Connection',
      operatingSystem: 'Operating System',
      lastHeartbeat: 'Last Heartbeat',
      uptime: 'Uptime',
      cpuCores: 'CPU Cores',
      memory: 'Memory',
      disk: 'Disk',
      version: 'Version',
      credentials: 'Node Credentials',
      credentialsHint: 'Use these credentials to configure the agent on your server',
      recentHeartbeats: 'Recent Heartbeats'
    },

    heartbeat: {
      time: 'Time',
      cpu: 'CPU',
      memory: 'Memory',
      disk: 'Disk',
      tasks: 'Tasks'
    },

    form: {
      addSourceProxy: 'Add Source Proxy',
      addTargetGateway: 'Add Target Gateway',
      editNode: 'Edit Node',
      deleteNode: 'Delete Node',
      deleteConfirm: 'Are you sure you want to delete this node?',
      name: 'Node Name',
      namePlaceholder: 'e.g. production-server-01',
      type: 'Node Type',
      hostname: 'Hostname / IP',
      port: 'Port',
      protocol: 'Protocol',
      os: 'Operating System',
      heartbeatInterval: 'Heartbeat Interval (seconds)',
      ipAddress: 'IP Address',
      operatingSystem: 'Operating System'
    },

    actions: {
      viewDetails: 'View Details',
      edit: 'Edit',
      delete: 'Delete',
      setMaintenance: 'Set Maintenance',
      activate: 'Activate',
      setActive: 'Set Active',
      viewHeartbeats: 'View Heartbeats',
      copyApiKey: 'Copy API Key'
    },

    deleteConfirm: {
      title: 'Delete Node',
      message: 'Are you sure you want to delete "{name}"? This action cannot be undone.'
    },

    empty: {
      title: 'No nodes yet',
      description: 'Add your first source proxy or target gateway to get started'
    }
  },

  // Backup Tasks
  backupTasks: {
    title: 'Backup Tasks',
    subtitle: 'Manage backup operations',
    createTask: 'Create Backup Task',

    types: {
      full: 'Full Backup',
      incremental: 'Incremental Backup',
      differential: 'Differential Backup'
    },

    status: {
      pending: 'Pending',
      queued: 'Queued',
      running: 'Running',
      paused: 'Paused',
      completed: 'Completed',
      failed: 'Failed',
      cancelled: 'Cancelled'
    },

    form: {
      taskName: 'Task Name',
      taskType: 'Backup Type',
      sourceNode: 'Source Node',
      targetGateway: 'Target Gateway',
      repository: 'Repository',
      sourcePaths: 'Source Paths',
      excludePaths: 'Exclude Paths',
      schedule: 'Schedule',
      runNow: 'Run Now',
      scheduleForLater: 'Schedule for Later'
    },

    progress: {
      files: 'Files',
      size: 'Size',
      progress: 'Progress',
      speed: 'Speed',
      eta: 'ETA',
      errors: 'Errors',
      warnings: 'Warnings'
    },

    actions: {
      viewDetails: 'View Details',
      start: 'Start',
      pause: 'Pause',
      resume: 'Resume',
      cancel: 'Cancel',
      retry: 'Retry',
      delete: 'Delete',
      viewLogs: 'View Logs'
    },

    empty: {
      title: 'No backup tasks',
      description: 'Create your first backup task to protect your data'
    }
  },

  // Recovery Tasks
  recoveryTasks: {
    title: 'Recovery Tasks',
    subtitle: 'Manage data recovery operations',
    createTask: 'Create Recovery Task',

    types: {
      original_location: 'Original Location',
      new_location: 'New Location'
    },

    status: {
      pending: 'Pending',
      queued: 'Queued',
      running: 'Running',
      paused: 'Paused',
      completed: 'Completed',
      failed: 'Failed',
      cancelled: 'Cancelled'
    },

    form: {
      targetNode: 'Target Node',
      repository: 'Repository',
      snapshot: 'Snapshot',
      type: 'Recovery Type',
      targetPath: 'Target Path',
      filePatterns: 'File Patterns',
      priority: 'Priority'
    },

    progress: {
      progress: 'Progress',
      files: 'files',
      size: 'Size'
    },

    actions: {
      start: 'Start',
      cancel: 'Cancel',
      viewDetails: 'View Details'
    },

    empty: {
      title: 'No recovery tasks',
      description: 'Create your first recovery task to restore your data'
    }
  },

  // Repository
  repository: {
    title: 'Backup Repository',
    subtitle: 'Manage backup storage',

    stats: {
      total: 'Total Repositories',
      totalSize: 'Total Size',
      totalCapacity: 'Total Capacity',
      usedSpace: 'Used Space',
      availableSpace: 'Available Space',
      snapshots: 'Snapshots',
      lastBackup: 'Last Backup'
    },

    form: {
      addRepository: 'Add Repository',
      editRepository: 'Edit Repository',
      repositoryName: 'Repository Name',
      repositoryType: 'Repository Type',
      connectionString: 'Connection String',
      capacity: 'Capacity',
      retention: 'Retention Policy',
      path: 'Path'
    },

    types: {
      local: 'Local',
      s3: 'S3 Compatible',
      azure: 'Azure Blob',
      gcs: 'Google Cloud Storage',
      b2: 'Backblaze B2'
    },

    empty: {
      title: 'No repositories',
      description: 'Add a backup repository to store your backup data'
    },

    confirmDelete: 'Are you sure you want to delete this repository?'
  },

  // Source Resources
  sourceResources: {
    title: 'Source Resources',
    subtitle: 'Manage backup data sources (NAS, NFS, CIFS, Object Storage, Local)',

    stats: {
      total: 'Total Resources',
      active: 'Active',
      mounted: 'Mounted',
      error: 'Error'
    },

    addResource: 'Add Source Resource',
    allTypes: 'All Types',
    allStatus: 'All Status',
    noBoundNode: 'No bound node',
    notMounted: 'Not mounted',
    testConnection: 'Test Connection',
    mountStatus: 'Mount Status',
    mountPoint: 'Mount Point',
    boundNode: 'Bound Node',
    noResources: 'No source resources',
    noResourcesDesc: 'Add a source resource to start backing up data',
    deleteConfirm: 'Delete Source Resource',
    deleteConfirmDesc: 'Are you sure you want to delete "{name}"?',

    status: {
      label: 'Status',
      connected: 'Connected',
      disconnected: 'Disconnected',
      error: 'Error'
    },

    form: {
      name: 'Name',
      type: 'Resource Type',
      boundNode: 'Bound Node',
      selectNode: 'Select a node',
      server: 'Server',
      exportPath: 'Export Path',
      share: 'Share Name',
      endpoint: 'Endpoint URL',
      bucket: 'Bucket Name',
      region: 'Region',
      accessKey: 'Access Key',
      secretKey: 'Secret Key',
      username: 'Username',
      password: 'Password',
      path: 'Path'
    }
  },

  // Policies
  policies: {
    title: 'Backup Policies',
    subtitle: 'Define backup rules and schedules',

    stats: {
      total: 'Total Policies',
      enabled: 'Enabled',
      disabled: 'Disabled'
    },

    form: {
      addPolicy: 'Add Policy',
      editPolicy: 'Edit Policy',
      policyName: 'Policy Name',
      description: 'Description',
      schedule: 'Schedule',
      scheduleType: 'Schedule Type',
      retention: 'Retention (days)',
      compression: 'Compression',
      encryption: 'Encryption',
      backupTask: 'Backup Task',
      time: 'Time',
      nextRun: 'Next Run'
    },

    scheduleTypes: {
      hourly: 'Hourly',
      daily: 'Daily',
      weekly: 'Weekly',
      monthly: 'Monthly',
      manual: 'Manual'
    },

    empty: {
      title: 'No policies',
      description: 'Create backup policies to automate your backup operations'
    },

    confirmDelete: 'Are you sure you want to delete this policy?'
  },

  // AI Query
  aiQuery: {
    title: 'AI File Intelligence',
    subtitle: 'Search and analyze your backup data',

    search: {
      placeholder: 'Ask questions about your backup data...',
      submit: 'Ask',
      examples: 'Example queries'
    },

    examples: {
      contracts: 'Find all contracts signed last year',
      sensitive: 'Show directories with sensitive data',
      changes: 'What changed in this folder?',
      summary: 'Summarize documents in this directory'
    },

    results: {
      title: 'Results',
      files: 'Files',
      folders: 'Folders',
      matches: 'Matches',
      relevance: 'Relevance',
      preview: 'Preview',
      download: 'Download'
    },

    empty: {
      title: 'Start exploring',
      description: 'Ask questions about your backup data using natural language'
    },

    clearConversation: 'Clear Conversation',
    analyzing: 'Analyzing backup data...',

    tips: {
      title: 'Tips for better results',
      tip1: 'Be specific about file types or date ranges',
      tip2: 'Use natural language to describe what you need',
      tip3: 'You can ask for summaries or comparisons'
    }
  },

  // Audit Log
  auditLog: {
    title: 'Audit Log',
    subtitle: 'Track system activities',

    stats: {
      success: 'Success',
      warning: 'Warning',
      failure: 'Failure'
    },

    filters: {
      user: 'User',
      action: 'Action',
      resource: 'Resource',
      dateRange: 'Date Range'
    },

    columns: {
      timestamp: 'Timestamp',
      user: 'User',
      action: 'Action',
      resourceType: 'Resource Type',
      resourceId: 'Resource ID',
      details: 'Details',
      ipAddress: 'IP Address'
    },

    actions: {
      export: 'Export',
      filter: 'Filter',
      backupCreate: 'Backup Created',
      backupExecute: 'Backup Executed',
      recoveryCreate: 'Recovery Created'
    },

    empty: {
      title: 'No audit logs',
      description: 'System activities will appear here'
    }
  },

  // Settings
  settings: {
    title: 'Settings',
    subtitle: 'Manage your account and preferences',

    sections: {
      profile: 'Profile',
      security: 'Security',
      notifications: 'Notifications',
      apiTokens: 'API Tokens',
      appearance: 'Appearance',
      language: 'Language'
    },

    profile: {
      title: 'Profile Information',
      firstName: 'First Name',
      lastName: 'Last Name',
      email: 'Email',
      phone: 'Phone',
      avatar: 'Avatar'
    },

    security: {
      title: 'Security Settings',
      changePassword: 'Change Password',
      currentPassword: 'Current Password',
      newPassword: 'New Password',
      confirmPassword: 'Confirm Password',
      sessions: 'Active Sessions',
      revokeSessions: 'Revoke All Sessions'
    },

    appearance: {
      title: 'Appearance',
      theme: 'Theme',
      light: 'Light',
      dark: 'Dark',
      system: 'System'
    },

    language: {
      title: 'Language',
      english: 'English',
      chinese: '中文'
    }
  },

  // Errors
  errors: {
    general: 'An error occurred',
    network: 'Network error. Please check your connection.',
    notFound: 'Resource not found',
    unauthorized: 'You are not authorized to perform this action',
    serverError: 'Server error. Please try again later.',
    validation: 'Please check your input',
    required: 'This field is required',
    invalidEmail: 'Please enter a valid email address',
    passwordTooShort: 'Password must be at least 8 characters',
    passwordMismatch: 'Passwords do not match'
  },

  // Confirmations
  confirmations: {
    delete: 'Are you sure you want to delete this item?',
    cancel: 'Are you sure you want to cancel this operation?',
    logout: 'Are you sure you want to logout?'
  },

  // Success messages
  success: {
    saved: 'Saved successfully',
    deleted: 'Deleted successfully',
    created: 'Created successfully',
    updated: 'Updated successfully',
    copied: 'Copied to clipboard',
    exported: 'Exported successfully'
  },

  // Time
  time: {
    now: 'Just now',
    minutesAgo: '{n} minutes ago',
    hoursAgo: '{n} hours ago',
    daysAgo: '{n} days ago',
    weeksAgo: '{n} weeks ago',
    monthsAgo: '{n} months ago',
    yearsAgo: '{n} years ago'
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
