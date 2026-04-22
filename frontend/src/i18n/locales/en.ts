export default {
  // Navigation
  nav: {
    dashboard: 'Dashboard',
    nodes: 'Nodes',
    backupTasks: 'Backup Tasks',
    recoveryTasks: 'Recovery Tasks',
    repository: 'Repository',
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
    optional: 'Optional'
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

    details: {
      hostname: 'Hostname',
      port: 'Port',
      protocol: 'Protocol',
      os: 'Operating System',
      version: 'Version',
      lastHeartbeat: 'Last Heartbeat',
      uptime: 'Uptime',
      apiKey: 'API Key',
      capabilities: 'Capabilities'
    },

    form: {
      addSourceProxy: 'Add Source Proxy',
      addTargetGateway: 'Add Target Gateway',
      editNode: 'Edit Node',
      deleteNode: 'Delete Node',
      deleteConfirm: 'Are you sure you want to delete this node?'
    },

    actions: {
      viewDetails: 'View Details',
      edit: 'Edit',
      delete: 'Delete',
      setMaintenance: 'Set Maintenance',
      setActive: 'Set Active',
      viewHeartbeats: 'View Heartbeats',
      copyApiKey: 'Copy API Key'
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

    types: {
      original: 'Original Location',
      new: 'New Location'
    },

    form: {
      taskName: 'Task Name',
      recoveryType: 'Recovery Type',
      sourceSnapshot: 'Source Snapshot',
      sourceNode: 'Source Node',
      targetGateway: 'Target Gateway',
      targetPath: 'Target Path',
      overwrite: 'Overwrite Existing'
    }
  },

  // Repository
  repository: {
    title: 'Backup Repository',
    subtitle: 'Manage backup storage',

    stats: {
      totalSize: 'Total Size',
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
      retention: 'Retention Policy'
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
    }
  },

  // Policies
  policies: {
    title: 'Backup Policies',
    subtitle: 'Define backup rules and schedules',

    form: {
      addPolicy: 'Add Policy',
      editPolicy: 'Edit Policy',
      policyName: 'Policy Name',
      description: 'Description',
      schedule: 'Schedule',
      retention: 'Retention',
      compression: 'Compression',
      encryption: 'Encryption'
    },

    empty: {
      title: 'No policies',
      description: 'Create backup policies to automate your backup operations'
    }
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
    }
  },

  // Audit Log
  auditLog: {
    title: 'Audit Log',
    subtitle: 'Track system activities',

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
      filter: 'Filter'
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
