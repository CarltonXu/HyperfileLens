export default {
  // Navigation
  nav: {
    dashboard: 'Dashboard',
    nodes: 'Nodes',
    proxies: 'Proxies',
    backupTasks: 'Backup Tasks',
    recoveryTasks: 'Recovery Tasks',
    repository: 'Backup Repository',
    sourceResources: 'Source Resources',
    policies: 'Policies',
    aiQuery: 'AI Query',
    auditLog: 'Audit Log',
    tenants: 'Tenants',
    users: 'Users',
    licenses: 'Licenses',
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
    copied: 'Copied!',
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
    undefined: 'Unknown',
    viewDetails: 'View Details',
    pending: 'Pending',
    all: 'All',
    total: 'Total',
    name: 'Name',
    status: 'Status',
    type: 'Type',
    role: 'Role',
    date: 'Date',
    actions: 'Actions',
    details: 'Details',
    description: 'Description',
    required: 'Required',
    optional: 'Optional',
    settings: 'Settings',
    close: 'Close',
    never: 'Never',
    justNow: 'Just now',
    minutesAgo: 'm ago',
    hoursAgo: 'h ago',
    daysAgo: 'd ago',
    createdAt: 'Created At',
    updatedAt: 'Updated At',
    unlimited: 'Unlimited',
    hide: 'Hide',
    success: 'Success',
    error: 'Error',
    warning: 'Warning',
    info: 'Info',
    confirmDelete: 'Confirm Delete',
    deleting: 'Deleting...',
    saving: 'Saving...',
    showing: 'Showing',
    to: 'to',
    of: 'of',
    results: 'results'
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

  // Proxies
  proxies: {
    title: 'Proxy Management',
    subtitle: 'Manage Agent and Sync proxies',
    installProxy: 'Install Proxy',
    online: 'Online',
    noConnection: 'No connection',

    stats: {
      total: 'Total Proxies',
      online: 'Online',
      agent: 'Agent Proxies',
      sync: 'Sync Proxies'
    },

    roles: {
      agent: 'Agent Proxy',
      sync: 'Sync Proxy'
    },

    status: {
      active: 'Active',
      pending: 'Pending',
      offline: 'Offline',
      error: 'Error',
      maintenance: 'Maintenance',
      installing: 'Installing'
    },

    actions: {
      viewDetails: 'View Details',
      edit: 'Edit',
      delete: 'Delete',
      setMaintenance: 'Set Maintenance',
      activate: 'Activate',
      regenerateToken: 'Regenerate Token',
      regenerateTokenConfirm: 'This will invalidate the current token. The proxy will need to be reconfigured. Continue?',
      viewInstall: 'View Install Command',
      viewInstallDesc: 'This proxy is not installed yet. Click to view installation command.'
    },

    form: {
      name: 'Proxy Name',
      hostname: 'Hostname',
      heartbeatInterval: 'Heartbeat Interval (seconds)',
      labels: 'Labels',
      capabilities: 'Capabilities'
    },

    list: {
      name: 'Name',
      role: 'Role',
      status: 'Status',
      hostname: 'Hostname',
      ip: 'IP Address',
      cpuCores: 'CPU',
      cores: 'cores',
      memory: 'Memory',
      disk: 'Disk',
      lastHeartbeat: 'Last Heartbeat',
      actions: 'Actions'
    },

    gridView: 'Grid View',
    listView: 'List View',

    detail: {
      hostname: 'Hostname',
      internalIp: 'Internal IP',
      operatingSystem: 'Operating System',
      version: 'Version',
      kopiaVersion: 'Kopia Version',
      uptime: 'Uptime',
      lastHeartbeat: 'Last Heartbeat',
      registeredAt: 'Registered At',
      heartbeatInterval: 'Heartbeat Interval',
      capabilities: 'Capabilities',
      labels: 'Labels',
      systemInfo: 'System Information',
      currentlyOnline: 'Currently online',
      currentlyOffline: 'Currently offline',
      recentTasks: 'Recent Tasks',
      noTasks: 'No tasks',
      noTasksHint: 'This proxy has not executed any backup or recovery tasks yet',
      noHeartbeats: 'No heartbeat records',
      noHeartbeatsHint: 'Heartbeats will be sent automatically when the proxy connects',
      noMonitorData: 'No monitor data',
      proxyId: 'Proxy ID',
      role: 'Role',
      status: 'Status',
      owner: 'Owner',
      createdAt: 'Created At',
      proxyVersion: 'Proxy Version',
      cpuCores: 'CPU Cores',
      cpuUsage: 'CPU Usage',
      memoryUsage: 'Memory Usage',
      diskUsage: 'Disk Usage',
      memoryTotal: 'Total Memory',
      diskTotal: 'Total Disk',
      memoryUsed: 'Memory Used',
      diskUsed: 'Disk Used',
      osVersion: 'OS Version',
      websocketStatus: 'WebSocket Status',
      connectionIp: 'Connection IP',
      connected: 'Connected',
      disconnected: 'Disconnected',
      notInstalled: 'Not Installed',
      installTokenUsed: 'Install Token Used',
      installTokenNotUsed: 'Install Token Not Used',
      total: 'Total',
      avg: 'Avg',
      cores: 'cores',
      cpu: 'CPU',
      memory: 'Memory',
      disk: 'Disk',
      pendingHint: 'Proxy not installed yet, please follow the installation instructions',
      tabs: {
        overview: 'Overview',
        tasks: 'Task History',
        heartbeats: 'Heartbeats',
        install: 'Install Info',
        monitor: 'Monitor'
      },
      sections: {
        basicInfo: 'Basic Information',
        systemInfo: 'System Information',
        hardwareResources: 'Hardware Resources',
        networkConnection: 'Network Connection'
      },
      heartbeatStats: 'Heartbeat Stats',
      heartbeats24h: 'Heartbeats (24h)',
      expected24h: 'Expected (24h)',
      missedHeartbeats: 'Missed Heartbeats',
      taskStats: 'Task Stats',
      totalTasks: 'Total Tasks',
      completed: 'Completed',
      failed: 'Failed',
      running: 'Running',
      totalHeartbeats: 'Total Heartbeats',
      avgCpu: 'Avg CPU',
      avgMemory: 'Avg Memory',
      taskStatus: {
        pending: 'Pending',
        dispatched: 'Dispatched',
        accepted: 'Accepted',
        running: 'Running',
        completed: 'Completed',
        failed: 'Failed',
        cancelled: 'Cancelled',
        timeout: 'Timeout'
      },
      timeRange: 'Time Range',
      custom: 'Custom',
      startTime: 'Start Time',
      endTime: 'End Time',
      apply: 'Apply',
      cpuChart: 'CPU Usage Trend',
      memoryChart: 'Memory Usage Trend',
      diskChart: 'Disk Usage Trend',
      networkInterfaces: 'Network Interfaces',
      interface: 'Interface',
      ipAddress: 'IP Address',
      macAddress: 'MAC Address',
      bytesIn: 'Bytes In',
      bytesOut: 'Bytes Out'
    },

    monitoring: {
      title: 'Monitoring',
      realtimeStatus: 'Realtime Status',
      connectionInfo: 'Connection Info',
      websocketStatus: 'WebSocket Status',
      connected: 'Connected',
      disconnected: 'Disconnected',
      heartbeatInterval: 'Heartbeat Interval',
      timeRange: 'Time Range',
      last1h: 'Last 1 Hour',
      last6h: 'Last 6 Hours',
      last24h: 'Last 24 Hours',
      last7d: 'Last 7 Days',
      last30d: 'Last 30 Days',
      custom: 'Custom',
      cpuChart: 'CPU Usage Trend',
      memoryChart: 'Memory Usage Trend',
      diskChart: 'Disk Usage Trend',
      networkChart: 'Network Traffic Trend',
      networkInterfaces: 'Network Interfaces',
      interfaceName: 'Interface Name',
      ipAddress: 'IP Address',
      macAddress: 'MAC Address',
      bytesIn: 'Bytes In',
      bytesOut: 'Bytes Out',
      noData: 'No data available',
      loading: 'Loading...',
      autoRefresh: 'Auto Refresh',
      refreshOff: 'Off',
      refresh10s: '10s',
      refresh30s: '30s',
      refresh1m: '1m',
      refresh5m: '5m',
      refreshNow: 'Refresh Now',
      // Detailed monitoring metrics
      processInfo: 'Process Info',
      processId: 'Process ID',
      processStartTime: 'Start Time',
      processMemory: 'Process Memory',
      processGoroutines: 'Goroutines',
      diskIO: 'Disk I/O',
      diskRead: 'Read Speed',
      diskWrite: 'Write Speed',
      diskReadBytes: 'Total Read',
      diskWriteBytes: 'Total Written',
      networkIO: 'Network I/O',
      networkRxSpeed: 'Receive Speed',
      networkTxSpeed: 'Transmit Speed',
      networkRxBytes: 'Total Received',
      networkTxBytes: 'Total Sent',
      networkPackets: 'Packets',
      networkRxPackets: 'Packets Received',
      networkTxPackets: 'Packets Sent',
      networkErrors: 'Network Errors',
      networkRxErrors: 'Receive Errors',
      networkTxErrors: 'Transmit Errors',
      networkDropped: 'Dropped',
      networkRxDropped: 'Receive Dropped',
      networkTxDropped: 'Transmit Dropped',
      loadAverage: 'Load Average',
      load1m: '1 min',
      load5m: '5 min',
      load15m: '15 min',
      fileDescriptors: 'File Descriptors',
      fdOpen: 'Open',
      fdMax: 'Max',
      tcpConnections: 'TCP Connections',
      tcpEstablished: 'Established',
      tcpListen: 'Listening',
      tcpTimeWait: 'Time Wait',
      tcpCloseWait: 'Close Wait',
      selectInterface: 'Select Interface',
      allInterfaces: 'All Interfaces',
      bandwidth: 'Bandwidth',
      packetsPerSec: 'Packets/s',
      errors: 'Errors',
      dropped: 'Dropped',
      packets: 'Packets',
      // Network IO Chart
      networkIOChart: 'Network Traffic Monitor',
      rxBytes: 'RX Bytes',
      txBytes: 'TX Bytes',
      rxPackets: 'RX Packets',
      txPackets: 'TX Packets',
      rxDrop: 'RX Dropped',
      txDrop: 'TX Dropped',
      rxErrs: 'RX Errors',
      txErrs: 'TX Errors',
      selectNetInterface: 'Select Interface',
      allNetInterfaces: 'All Interfaces',
      bandwidthUtil: 'Bandwidth Utilization',
      // Disk IO Chart
      diskIOChart: 'Disk I/O Performance',
      selectDisk: 'Select Disk',
      allDisks: 'All Disks',
      diskUtil: 'Utilization',
      diskAwait: 'Avg Wait Time',
      diskRs: 'Read IOPS',
      diskWs: 'Write IOPS',
      diskRkBs: 'Read Speed',
      diskWkBs: 'Write Speed',
      // System resources
      cpuCores: 'CPU Cores',
      memoryTotal: 'Total Memory',
      diskTotal: 'Total Disk',
      cpuUsage: 'CPU Usage',
      memoryUsage: 'Memory Usage',
      diskUsage: 'Disk Usage',
      total: 'Total',
      networkIn: 'Inbound',
      networkOut: 'Outbound',
      // New section titles
      systemResources: 'System Resources',
      storageSection: 'Storage',
      networkSection: 'Network',
      // Disk monitoring
      diskUtilAwait: 'Utilization & Await',
      diskIOPS: 'IOPS (Read/Write per second)',
      diskBandwidth: 'Bandwidth (Read/Write kB/s)',
      // Network monitoring
      networkBytes: 'Network Traffic (MB)'
    },

    tasks: {
      total: 'Total Tasks',
      completed: 'Completed',
      failed: 'Failed',
      running: 'Running',
      taskId: 'Task ID',
      type: 'Type',
      status: 'Status',
      progress: 'Progress',
      startTime: 'Start Time',
      duration: 'Duration'
    },

    heartbeats: {
      totalHeartbeats: 'Total Heartbeats',
      expectedHeartbeats: 'Expected Heartbeats',
      missedHeartbeats: 'Missed Heartbeats',
      heartbeatRate: 'Heartbeat Rate',
      time: 'Time',
      cpu: 'CPU',
      memory: 'Memory',
      disk: 'Disk',
      uptime: 'Uptime',
      activeTasks: 'Active Tasks'
    },

    install: {
      title: 'Install New Proxy',
      subtitle: 'Select role and generate installation command',
      agentDescription: 'Runs on business servers (Windows/Linux/macOS). Reads local filesystem, executes backups, reports status. No mount capability.',
      syncDescription: 'Runs on dedicated nodes/jump hosts. Mounts NAS, accesses object storage, provides unified data access point.',
      requirements: 'System Requirements',
      agentOS: 'Windows/Linux/macOS',
      agentCPU: '2+ cores',
      agentMemory: '4GB+ RAM',
      agentDisk: 'Based on data size',
      syncOS: 'Ubuntu 24.04 LTS',
      syncCPU: '4+ cores',
      syncMemory: '16GB+ RAM',
      syncDisk: '500GB+ cache',
      infoTitle: 'Role Guide',
      infoDescription: 'Agent proxies install on business servers to backup local data. Sync proxies install on jump hosts to mount and backup NAS/object storage.',
      proxyName: 'Proxy Name',
      namePlaceholder: 'e.g. prod-backup-proxy-01',
      targetOS: 'Target Operating System',
      syncFixedOS: 'Ubuntu 24.04 LTS (Fixed)',
      syncFixedOSNote: 'Sync proxy requires Ubuntu 24.04 LTS for NFS/SMB mount support',
      labels: 'Labels (optional)',
      labelPlaceholder: 'Add a label',
      generateCommand: 'Generate Install Command',
      generating: 'Generating...',
      installCommand: 'Installation Command',
      downloadConfig: 'Download Config',
      proxyId: 'Proxy ID',
      apiToken: 'API Token',
      ready: 'Installation Ready',
      readyDescription: 'Copy and run the command below on your target server to install the proxy.',
      step1Title: 'Run the install command on target server',
      step1Desc: 'Login to your target server and paste the command below into the terminal. The script will automatically download and configure the proxy.',
      step1Text: 'Login to your target server and paste the command into terminal',
      credentialsTitle: 'Save these credentials securely',
      credentialsDesc: 'These credentials are used for secure communication between the proxy and control plane. Please save them for future reference. You can regenerate the token in the proxy detail page.',
      proxyIdLabel: 'Proxy ID',
      proxyIdDesc: 'Unique identifier for this proxy node',
      apiTokenLabel: 'API Token',
      apiTokenDesc: 'API token for secure authentication',
      warningTitle: 'Proxy Not Yet Installed',
      warningText: 'This proxy has been created but not yet installed. Please run the installation command on your target server. Click "Regenerate Token" to get new installation info.',
      helpTitle: 'Installation Guide:',
      help1: 'The proxy will automatically connect to control plane after installation',
      help2: 'Install token is one-time use and will be invalidated after successful installation',
      help3: 'API token is for long-term authentication, please keep it secure',
      done: 'Done',
      os: {
        linux: 'Linux',
        windows: 'Windows',
        macos: 'macOS'
      }
    },

    installInfo: {
      title: 'Install Command',
      warning: 'Proxy Not Yet Installed',
      warningDesc: 'This proxy has been created but not yet installed. Copy the command below and run it on the target server.',
      installCommand: 'Install Command',
      noCommand: 'No install command available. Please regenerate token.',
      credentials: 'Installation Credentials',
      proxyId: 'Proxy ID',
      proxyIdDesc: 'Unique identifier for this proxy node',
      apiToken: 'API Token',
      apiTokenDesc: 'API token for secure authentication with control plane',
      installToken: 'Install Token',
      tokenUsed: 'Used',
      tokenAvailable: 'Available',
      help: 'Installation Guide',
      helpStep1: 'Copy the install command and run it on the target server',
      helpStep2: 'The proxy will automatically connect to control plane after installation',
      helpStep3: 'Install token is one-time use and will be invalidated after successful installation',
      regenerate: 'Regenerate Token',
      regenerateDesc: 'Regenerating will invalidate the current token'
    },

    edit: {
      title: 'Edit Proxy'
    },

    delete: {
      title: 'Delete Proxy',
      description: 'Are you sure you want to delete "{name}"? This action cannot be undone.',
      confirm: 'Are you sure you want to delete this proxy? All task history will be lost.'
    },

    empty: {
      title: 'No proxies installed',
      description: 'Install a proxy to start managing backup nodes'
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
    subtitle: 'Manage backup repositories',

    stats: {
      total: 'Total Repositories',
      totalSize: 'Total Size',
      totalCapacity: 'Total Capacity',
      usedSpace: 'Used Space',
      availableSpace: 'Available Space',
      snapshots: 'Snapshots',
      lastBackup: 'Last Backup',
      active: 'Active'
    },

    form: {
      addRepository: 'Add Repository',
      editRepository: 'Edit Repository',
      repositoryName: 'Repository Name',
      repositoryType: 'Repository Type',
      connectionString: 'Connection String',
      capacity: 'Storage Quota',
      capacityUnit: 'GB',
      capacityPlaceholder: '0 for unlimited',
      capacityHint: 'For capacity planning and alerts, 0 means unlimited',
      retention: 'Retention Policy',
      path: 'Path',
      namePlaceholder: 'Enter repository name',
      descPlaceholder: 'Enter description (optional)'
    },

    types: {
      local: 'Local Filesystem',
      s3: 'S3 Object Storage',
      nas: 'NAS/NFS/CIFS',
      azure: 'Azure Blob',
      gcs: 'Google Cloud Storage',
      b2: 'Backblaze B2'
    },

    s3: {
      hint: 'S3 Compatible Object Storage Configuration',
      hintDetail: 'Supports Amazon S3, MinIO, Alibaba OSS, Tencent COS and other S3-compatible storage',
      endpoint: 'Endpoint',
      endpointHint: 'Object storage service URL, e.g. https://s3.amazonaws.com',
      bucket: 'Bucket',
      region: 'Region',
      prefix: 'Prefix',
      prefixHint: 'Optional, backup storage path prefix',
      accessKey: 'Access Key',
      secretKey: 'Secret Key',
      secretKeyPlaceholder: 'Enter secret key',
      secretKeyEditHint: 'Leave empty to keep existing key',
      credentials: 'Access Credentials',
      bucketSelection: 'Bucket Selection',
      existingBucket: 'Select Existing Bucket',
      newBucket: 'Create New Bucket',
      existingBucketWarning: 'Important Notice',
      existingBucketWarningDetail: 'Selecting an existing bucket will perform Kopia initialization. Any existing data in the bucket may be overwritten or lost. Please ensure the bucket is empty or data can be safely removed.',
      fetchBucketList: 'Fetch Bucket List',
      loadingBuckets: 'Loading...',
      selectBucket: 'Select Bucket',
      selectBucketPlaceholder: 'Please select a bucket',
      bucketName: 'Bucket Name',
      bucketNameRules: 'Bucket Name Rules',
      bucketNameRule1: '3-63 characters',
      bucketNameRule2: 'Only lowercase letters, numbers, and hyphens (-)',
      bucketNameRule3: 'Must start and end with a letter or number',
      bucketNameRule4: 'Cannot use IP address format (e.g. 192.168.1.1)',
      bucketNameRule5: 'Cannot start with xn-- (reserved for internationalized domains)',
      check: 'Check',
      checking: 'Checking...',
      bucketNameAvailable: 'Bucket name is available',
      bucketNameUnavailable: 'Bucket name is unavailable',
      bucketNameInvalid: 'Invalid bucket name format',
      bucketNameInvalidChars: 'Bucket name contains invalid characters. Only lowercase letters, numbers, hyphens (-), and periods (.) are allowed',
      bucketNameStartEnd: 'Bucket name must start and end with a letter or number',
      bucketNameIPFormat: 'Bucket name cannot be formatted as an IP address (e.g., 192.168.1.1)',
      bucketNameConsecutive: 'Bucket name cannot contain consecutive periods or hyphens next to periods',
      bucketNameTooShort: 'Bucket name must be at least 3 characters long',
      bucketNameTooLong: 'Bucket name must not exceed 63 characters',
      bucketNameXnPrefix: 'Bucket name cannot start with "xn--" (reserved for internationalized domains)',
      bucketListError: 'Failed to fetch bucket list',
      noBucketsFound: 'No buckets available in this account',
      fetchBucketsFailed: 'Failed to fetch bucket list. Please check your credentials.',
      fillCredentialsFirst: 'Please fill in Endpoint and credentials first',
      validateFailed: 'Bucket name validation failed',
      checkSuccess: 'Bucket name is available',
      checkBucketFailed: 'Failed to check bucket name',
      connectionTimeout: 'Connection timeout. Please check if the endpoint URL is correct and the service is accessible',
      networkError: 'Network connection failed. Please check your network or endpoint URL',
      invalidEndpoint: 'Invalid endpoint format. Please enter a valid URL',
      urlStyle: 'URL Style',
      urlStyleVirtual: 'Virtual Hosted Style',
      urlStylePath: 'Path Style',
      urlStyleHint: 'Virtual Hosted Style uses bucket name as subdomain (bucket.endpoint). Path Style uses bucket as path (endpoint/bucket).',
      useTLS: 'Use TLS',
      useTLSHint: 'Enable HTTPS for secure connection. Disable for HTTP or self-signed certificates.',
      createBucketSuccess: 'Bucket created successfully',
      createBucketFailed: 'Failed to create bucket',
      bucketNameRequired: 'Bucket name is required'
    },

    nas: {
      hint: 'NAS Network Storage Configuration',
      hintDetail: 'Mount remote network storage via NFS or CIFS/SMB protocol',
      mountType: 'Mount Type',
      server: 'Server Address',
      exportPath: 'Export Path',
      mountOptions: 'Mount Options',
      mountOptionsHint: 'Optional, e.g. rw,hard,intr (NFS) or vers=3.0,iocharset=utf8 (CIFS)',
      username: 'Username',
      password: 'Password'
    },

    local: {
      hint: 'Local Filesystem Configuration',
      hintDetail: 'Use a local directory on Sync Proxy as backup storage. Must select an online Sync Proxy.',
      selectDirectory: 'Select Directory',
      goUp: 'Go Up',
      noSubdirectories: 'No subdirectories',
      useCurrentPath: 'Use current path',
      selectedPath: 'Selected path',
      noSyncProxy: 'No Sync Proxy Available',
      noSyncProxyHint: 'Please add a Sync Proxy first and ensure it is online'
    },

    boundSyncProxy: 'Bind Sync Proxy',
    selectSyncProxy: 'Select Sync Proxy',
    boundSyncProxyHint: 'Only Sync Proxy can operate this repository',
    initKopia: 'Initialize Kopia',
    kopiaInitialized: 'Kopia Initialized',
    kopiaNotInitialized: 'Kopia Not Initialized',

    empty: {
      title: 'No repositories',
      description: 'Add a backup repository to store your backup data'
    },

    validation: {
      nameRequired: 'Repository name is required',
      endpointRequired: 'Endpoint URL is required',
      bucketRequired: 'Bucket name is required',
      accessKeyRequired: 'Access Key is required',
      secretKeyRequired: 'Secret Key is required',
      serverRequired: 'Server address is required',
      exportPathRequired: 'Export path is required',
      usernameRequired: 'Username is required',
      passwordRequired: 'Password is required',
      proxyRequired: 'Sync Proxy is required',
      pathRequired: 'Target path is required',
      formInvalid: 'Form validation failed',
      checkFields: 'Please check required fields'
    },

    list: {
      name: 'Name',
      type: 'Type',
      status: 'Status',
      connection: 'Connection',
      boundNode: 'Bound Node',
      capacity: 'Capacity',
      kopia: 'Kopia Status',
      actions: 'Actions'
    },

    testConnection: 'Test Connection',
    testingConnection: 'Testing...',
    connectionTestSuccess: 'Connection test successful',
    connectionTestFailed: 'Connection test failed',
    lastConnectionTest: 'Last Test',
    connectionTestNever: 'Never tested',
    connectionTestResult: 'Test Result',
    createSuccess: 'Repository created successfully',
    createFailed: 'Failed to create repository',
    deleteSuccess: 'Repository deleted successfully',
    deleteFailed: 'Failed to delete repository',
    updateSuccess: 'Repository updated successfully',
    updateFailed: 'Failed to update repository',

    errors: {
      endpointUnreachable: 'Unable to connect to the endpoint. Please check the URL and network connectivity.'
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
      avatar: 'Avatar',
      username: 'Username',
      role: 'Role',
      createdAt: 'Created At',
      accountInfo: 'Account Information',
      roles: {
        admin: 'Administrator',
        operator: 'Operator',
        viewer: 'Viewer'
      }
    },

    security: {
      title: 'Security Settings',
      changePassword: 'Change Password',
      currentPassword: 'Current Password',
      newPassword: 'New Password',
      confirmPassword: 'Confirm Password',
      passwordHint: 'Password must be at least 8 characters',
      sessions: 'Active Sessions',
      revokeSessions: 'Revoke All Sessions',
      errors: {
        currentRequired: 'Current password is required',
        minLength: 'Password must be at least 8 characters',
        mismatch: 'Passwords do not match'
      },
      success: 'Password changed successfully'
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
  },

  // Pagination
  pagination: {
    showing: 'Showing',
    to: 'to',
    of: 'of',
    items: 'items',
    pageSize: 'Per page',
    page: 'Page',
    firstPage: 'First page',
    lastPage: 'Last page',
    prevPage: 'Previous page',
    nextPage: 'Next page',
    goToPage: 'Go to page {page}'
  },

  // Tenants
  tenants: {
    title: 'Tenant Management',
    createTenant: 'Create Tenant',
    editTenant: 'Edit Tenant',
    tenantName: 'Tenant Name',
    tenantSlug: 'Tenant Slug',
    description: 'Description',
    status: 'Status',
    active: 'Active',
    inactive: 'Inactive',
    suspended: 'Suspended',
    undefined: 'Unknown',
    maxUsers: 'Max Users',
    maxProxies: 'Max Proxies',
    maxRepositories: 'Max Repositories',
    maxStorageGb: 'Max Storage (GB)',
    userCount: 'Users',
    proxyCount: 'Proxies',
    repositoryCount: 'Repositories',
    storageUsed: 'Storage Used',
    createdAt: 'Created At',
    updatedAt: 'Updated At',
    users: 'Users',
    addUser: 'Add User',
    removeUser: 'Remove User',
    role: 'Role',
    admin: 'Admin',
    member: 'Member',
    owner: 'Owner',
    activate: 'Activate',
    deactivate: 'Deactivate',
    confirmDelete: 'Are you sure you want to delete tenant "{name}"? This action cannot be undone.',
    stats: 'Statistics',
    resources: 'Resource Usage',
    limit: 'Limit',
    tenantNamePlaceholder: 'Enter tenant name',
    tenantSlugPlaceholder: 'e.g., my-company',
    tenantSlugHelp: 'Only lowercase letters, numbers, and hyphens',
    descriptionPlaceholder: 'Enter tenant description (optional)'
  },

  // Users
  users: {
    title: 'User Management',
    description: 'Manage users within your tenant',
    createUser: 'Create User',
    inviteUser: 'Invite User',
    user: 'User',
    email: 'Email',
    password: 'Password',
    firstName: 'First Name',
    lastName: 'Last Name',
    role: 'Role',
    status: 'Status',
    active: 'Active',
    inactive: 'Inactive',
    lastLogin: 'Last Login',
    createdAt: 'Created At',
    disableUser: 'Disable User',
    enableUser: 'Enable User',
    changeRole: 'Change Role',
    changeRoleHint: 'Change role for user {user}',
    sendInvite: 'Send Invite',
    sending: 'Sending...',
    emailPlaceholder: 'Enter email address',
    passwordPlaceholder: 'Enter password',
    roles: {
      admin: 'Tenant Admin',
      member: 'Tenant User',
      superAdmin: 'Platform Admin',
      undefined: 'Not Set'
    },
    isSuperuser: 'Platform Admin Privilege',
    platformAdmin: 'Platform Admin',
    setPlatformAdmin: 'Set as Platform Admin',
    removePlatformAdmin: 'Remove Platform Admin',
    platformAdminHint: 'Platform admins can manage all tenants and users',
    onlyPlatformAdminCanSet: 'Only platform admins can set this permission',
    editUser: 'Edit User',
    editUserHint: 'Edit user {user} information',
    updateUser: 'Update User',
    updateSuccess: 'User updated successfully',
    updateFailed: 'Failed to update user',
    username: 'Username',
    phone: 'Phone',
    tenant: 'Tenant',
    selectTenant: 'Select tenant',
    superuser: 'Superuser',
    createSuccess: 'User created successfully',
    createFailed: 'Failed to create user',
    inviteSuccess: 'Invitation sent successfully',
    inviteFailed: 'Failed to send invitation',
    roleChangeSuccess: 'Role changed successfully',
    roleChangeFailed: 'Failed to change role',
    enableSuccess: 'User enabled',
    disableSuccess: 'User disabled'
  },

  // Licenses
  licenses: {
    title: 'License Management',
    description: 'Manage product licenses and authorization',
    
    // Machine Code
    getMachineCode: 'Get Machine Code',
    exportMachineCode: 'Export Machine Code',
    machineCodeTitle: 'Machine Code',
    machineCodeDescription: 'Unique identifier for this environment',
    machineCodeInstructions: 'This code is unique to your environment. The activation code generated from this code can only be used here.',
    machineCodeGenerated: 'Machine code generated',
    generateMachineCode: 'Generate Machine Code',
    clickToGenerate: 'Click the button below to generate machine code',
    machineCodeInfo: 'Machine Code',
    machineCodeHelp: 'Send this code to the sales team to generate your activation code:',
    yourMachineCode: 'Your Machine Code',
    machineCodeNote: 'This code is uniquely generated for your environment and tenant. It will not change unless you reinstall the system.',
    howToActivate: 'How to activate:',
    step1CopyCode: 'Copy the machine code below',
    step2SendToSales: 'Send it to our sales team',
    step3ReceiveActivation: 'Receive your activation code',
    step4Activate: 'Click "Activate License" to enter the code',
    
    // Activation
    activateLicense: 'Activate License',
    activateDescription: 'Enter the activation code you received from the sales team.',
    activationCode: 'Activation Code',
    activationCodePlaceholder: 'HFL-ACT-...',
    activating: 'Activating...',
    activate: 'Activate',
    activateSuccess: 'License activated successfully',
    activateFailed: 'License activation failed',
    enterActivationCode: 'Enter the activation code provided by the sales team',
    
    // Current License
    currentLicense: 'Current License',
    noLicense: 'No Active License',
    noLicenseDescription: 'Please activate a license to use this product.',
    limitsAndUsage: 'Limits & Usage',
    
    // Stats
    totalLicenses: 'Total Licenses',
    validLicenses: 'Valid Licenses',
    expiredLicenses: 'Expired',
    activeFeatures: 'Active Features',
    
    // Status
    status: 'Status',
    valid: 'Valid',
    expired: 'Expired',
    invalid: 'Invalid',
    revoked: 'Revoked',
    active: 'Active',
    inactive: 'Inactive',
    
    // Fields
    tenant: 'Tenant',
    issuedAt: 'Issued At',
    expiresAt: 'Expires At',
    daysRemaining: '{n} days remaining',
    machineId: 'Machine Code',
    machineCode: 'Machine Code',
    licenseKey: 'License Key',
    activatedAt: 'Activated At',
    
    // Limits - all quota types
    maxTenants: 'Max Tenants',
    maxUsers: 'Max Users',
    maxProxies: 'Max Proxies',
    maxStorage: 'Storage (GB)',
    maxGateways: 'Max Gateways',
    aiInsightsQuota: 'AI Insights',
    maxBackupTasks: 'Backup Tasks',
    maxRecoveryTasks: 'Recovery Tasks',
    maxSourceResources: 'Source Resources',
    maxPolicies: 'Policies',
    maxRepositories: 'Repositories',
    
    // History
    history: 'License History',
    changeType: 'Change Type',
    changedAt: 'Changed At',
    previousExpiry: 'Previous Expiry',
    reason: 'Reason',
    changeInitial: 'Initial',
    changeRenewal: 'Renewal',
    changeUpgrade: 'Upgrade',
    changeDowngrade: 'Downgrade',
    changeExpired: 'Expired',
    
    // Quota errors
    quotaExceeded: 'Quota Exceeded',
    quotaExceededFor: '{resource} quota exceeded',
    currentUsage: 'Current usage: {current}/{max}',
    pleaseUpgrade: 'Please upgrade your license for more quota',
    resourceProxies: 'Proxies',
    resourceRepositories: 'Repositories',
    resourceUsers: 'Users',
    resourceBackupTasks: 'Backup Tasks',
    resourceRecoveryTasks: 'Recovery Tasks',
    resourceSourceResources: 'Source Resources',
    resourcePolicies: 'Backup Policies',
    resourceGateways: 'Gateways',
    resourceTenants: 'Tenants',
    resourceStorage: 'Storage',
    resourceAiInsights: 'AI Insights',
  }
}
