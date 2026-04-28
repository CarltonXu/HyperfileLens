<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import type { ProxyNode, ProxyStats, ProxyTask } from '@/types/proxy'
import Pagination from '@/components/Pagination.vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line } from 'vue-chartjs'
import {
  ServerIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  ComputerDesktopIcon,
  CircleStackIcon,
  EllipsisHorizontalIcon,
  MapPinIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  WrenchScrewdriverIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
  CpuChipIcon,
  TrashIcon,
  PencilIcon,
  PlayIcon,
  PauseIcon,
  InformationCircleIcon,
  ClipboardDocumentIcon,
  ArrowDownTrayIcon,
  DocumentDuplicateIcon,
  KeyIcon,
  Squares2X2Icon,
  Bars3Icon,
  WifiIcon,
  ClipboardDocumentListIcon,
  SignalIcon,
  CalendarIcon,
  ChartBarIcon,
} from '@heroicons/vue/24/outline'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const { t } = useI18n()

// State
const isLoading = ref(true)
const proxies = ref<ProxyNode[]>([])
const stats = ref<ProxyStats | null>(null)
const selectedRole = ref<string>('all')
const selectedStatus = ref<string>('all')
const searchQuery = ref('')
const viewMode = ref<'card' | 'list'>('card') // View mode: card or list
const showInstallInfoModal = ref(false)

// Monitor time range
const monitorTimeRange = ref<'1h' | '6h' | '24h' | '7d' | '30d' | 'custom'>('24h')
const customTimeRange = ref<{ start: string; end: string }>({ start: '', end: '' })
const showCustomDatePicker = ref(false)

// Pagination
const currentPage = ref(1)
const pageSize = ref(10)

// Installation Wizard
const showInstallWizard = ref(false)
const installStep = ref(1) // 1: select role, 2: config, 3: command, 4: waiting
const installData = ref({
  name: '',
  role: 'agent' as 'agent' | 'sync',
  os: 'linux',
  labels: [] as string[],
  newLabel: ''
})
const installResult = ref<{
  proxy_id: string
  name: string
  role: string
  install_token: string
  api_token: string
  install_command: string
  windows_command: string
  config_yaml: string
  expires_at: string
} | null>(null)
const isGeneratingInstall = ref(false)
const commandCopied = ref(false)

// Detail Drawer
const showDetailDrawer = ref(false)
const selectedProxy = ref<ProxyNode | null>(null)
const detailTab = ref<'overview' | 'install' | 'monitor' | 'tasks' | 'heartbeats'>('overview')

// Tab data states with loading and caching
const tabData = ref({
  overview: {
    data: null as any,
    loading: false,
    loaded: false,
  },
  install: {
    data: null as any,
    loading: false,
    loaded: false,
  },
  monitor: {
    data: null as any,
    loading: false,
    loaded: false,
  },
  tasks: {
    data: [] as ProxyTask[],
    stats: null as { total: number; completed: number; failed: number; running: number } | null,
    loading: false,
    loaded: false,
  },
  heartbeats: {
    data: [] as any[],
    loading: false,
    loaded: false,
    pagination: { count: 0, page: 1, pageSize: 20 },
  },
})

// Auto refresh states
const autoRefresh = ref({
  monitor: { enabled: false, interval: 30, timer: null as number | null },
  heartbeats: { enabled: false, interval: 30, timer: null as number | null },
})

// Selected network interface for detailed view
const selectedNetworkInterface = ref<string>('all')
const selectedNetIOInterface = ref<string>('')
const selectedDiskIO = ref<string>('')

// Network IO stats computed
const networkIOStats = computed(() => {
  const data = tabData.value.monitor.data?.network_io || []
  return {
    rxPackets: data.reduce((sum: number, item: { rx_packets?: number }) => sum + (item.rx_packets || 0), 0),
    txPackets: data.reduce((sum: number, item: { tx_packets?: number }) => sum + (item.tx_packets || 0), 0),
    rxDrop: data.reduce((sum: number, item: { rx_drop?: number }) => sum + (item.rx_drop || 0), 0),
    txErrs: data.reduce((sum: number, item: { tx_errs?: number }) => sum + (item.tx_errs || 0), 0)
  }
})

// Disk IO stats computed
const diskIOStats = computed(() => {
  const data = tabData.value.monitor.data?.disk_io || []
  const len = data.length || 1
  return {
    avgRs: Math.round(data.reduce((sum: number, item: { r_s?: number }) => sum + (item.r_s || 0), 0) / len),
    avgWs: Math.round(data.reduce((sum: number, item: { w_s?: number }) => sum + (item.w_s || 0), 0) / len),
    avgRkBs: Math.round(data.reduce((sum: number, item: { rkB_s?: number }) => sum + (item.rkB_s || 0), 0) / len),
    avgWkBs: Math.round(data.reduce((sum: number, item: { wkB_s?: number }) => sum + (item.wkB_s || 0), 0) / len)
  }
})

const showEditModal = ref(false)
const editFormData = ref({
  name: '',
  hostname: '',
  heartbeat_interval: 10,
  tags: {} as Record<string, string>,
  labels: [] as string[]
})

// Delete Confirm
const showDeleteConfirm = ref(false)
const proxyToDelete = ref<ProxyNode | null>(null)

// Dropdown menu
const openMenuId = ref<string | null>(null)

// Polling for status updates
let pollInterval: number | null = null

const filteredProxies = computed(() => {
  let result = proxies.value

  if (selectedRole.value !== 'all') {
    result = result.filter(p => p.role === selectedRole.value)
  }

  if (selectedStatus.value !== 'all') {
    result = result.filter(p => p.status === selectedStatus.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      p.name.toLowerCase().includes(query) ||
      (p.hostname || '').toLowerCase().includes(query)
    )
  }

  return result
})

// Paginated proxies for display
const paginatedProxies = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredProxies.value.slice(start, end)
})

// Reset page when filters change
watch([selectedRole, selectedStatus, searchQuery], () => {
  currentPage.value = 1
})

async function fetchProxies() {
  isLoading.value = true
  try {
    const [proxiesRes, statsRes] = await Promise.all([
      api.get('/api/v1/proxies/'),
      api.get('/api/v1/proxies/stats/')
    ])
    proxies.value = proxiesRes.data.results || proxiesRes.data || []
    stats.value = statsRes.data
  } catch (error) {
    console.error('Failed to fetch proxies:', error)
  } finally {
    isLoading.value = false
  }
}

// Tab data fetching functions
// silent=true 时不显示loading，静默刷新数据
async function fetchProxyOverview(proxyId: string, silent = false) {
  if (!silent) tabData.value.overview.loading = true
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId}/overview/`)
    tabData.value.overview.data = res.data
    tabData.value.overview.loaded = true
  } catch (error) {
    console.error('Failed to fetch proxy overview:', error)
  } finally {
    if (!silent) tabData.value.overview.loading = false
  }
}

async function fetchProxyTasks(proxyId: string, page = 1, silent = false) {
  if (!silent) tabData.value.tasks.loading = true
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId}/tasks/?limit=50&page=${page}`)
    // Handle new response format with stats
    if (res.data.tasks) {
      tabData.value.tasks.data = res.data.tasks
      tabData.value.tasks.stats = res.data.stats || { total: 0, completed: 0, failed: 0, running: 0 }
    } else if (res.data.results) {
      tabData.value.tasks.data = res.data.results
    } else {
      tabData.value.tasks.data = res.data
    }
    tabData.value.tasks.loaded = true
  } catch (error) {
    console.error('Failed to fetch proxy tasks:', error)
    if (!silent) tabData.value.tasks.data = []
  } finally {
    if (!silent) tabData.value.tasks.loading = false
  }
}

async function fetchProxyHeartbeats(proxyId: string, page = 1, silent = false) {
  if (!silent) tabData.value.heartbeats.loading = true
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId}/heartbeats/?hours=24&page=${page}&page_size=${tabData.value.heartbeats.pagination.pageSize}`)
    // Handle paginated response
    if (res.data.results) {
      tabData.value.heartbeats.data = res.data.results
      tabData.value.heartbeats.pagination.count = res.data.count
    } else {
      tabData.value.heartbeats.data = res.data
    }
    tabData.value.heartbeats.loaded = true
  } catch (error) {
    console.error('Failed to fetch proxy heartbeats:', error)
    if (!silent) tabData.value.heartbeats.data = []
  } finally {
    if (!silent) tabData.value.heartbeats.loading = false
  }
}

async function fetchProxyMonitor(proxyId: string, silent = false) {
  if (!silent) tabData.value.monitor.loading = true
  try {
    // Convert time range to hours
    let hours = 24
    if (monitorTimeRange.value === '1h') hours = 1
    else if (monitorTimeRange.value === '6h') hours = 6
    else if (monitorTimeRange.value === '24h') hours = 24
    else if (monitorTimeRange.value === '7d') hours = 168
    else if (monitorTimeRange.value === '30d') hours = 720
    
    const res = await api.get(`/api/v1/proxies/${proxyId}/monitor/?hours=${hours}`)
    tabData.value.monitor.data = res.data
    tabData.value.monitor.loaded = true
  } catch (error) {
    console.error('Failed to fetch proxy monitor:', error)
    if (!silent) tabData.value.monitor.data = null
  } finally {
    if (!silent) tabData.value.monitor.loading = false
  }
}

function setTimeRange(range: '1h' | '6h' | '24h' | '7d' | '30d' | 'custom') {
  monitorTimeRange.value = range
  if (range !== 'custom' && selectedProxy.value) {
    tabData.value.monitor.loaded = false
    fetchProxyMonitor(selectedProxy.value.id)
  }
  showCustomDatePicker.value = range === 'custom'
}

function applyCustomTimeRange() {
  if (customTimeRange.value.start && customTimeRange.value.end && selectedProxy.value) {
    // Calculate hours from the date range
    const start = new Date(customTimeRange.value.start)
    const end = new Date(customTimeRange.value.end)
    const hours = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60))
    if (hours > 0) {
      tabData.value.monitor.loaded = false
      fetchProxyMonitor(selectedProxy.value.id)
    }
  }
}

// Installation Wizard Functions
function openInstallWizard() {
  installStep.value = 1
  installData.value = {
    name: '',
    role: 'agent',
    os: 'linux',
    labels: [],
    newLabel: ''
  }
  installResult.value = null
  showInstallWizard.value = true
}

function addLabel() {
  if (installData.value.newLabel && !installData.value.labels.includes(installData.value.newLabel)) {
    installData.value.labels.push(installData.value.newLabel)
    installData.value.newLabel = ''
  }
}

function removeLabel(label: string) {
  installData.value.labels = installData.value.labels.filter(l => l !== label)
}

async function generateInstallCommand() {
  if (!installData.value.name) return

  isGeneratingInstall.value = true
  try {
    const res = await api.post('/api/v1/proxies/generate_install/', {
      name: installData.value.name,
      role: installData.value.role,
      os: installData.value.os,
      labels: installData.value.labels
    })
    installResult.value = res.data
    installStep.value = 3
  } catch (error: any) {
    console.error('Failed to generate install command:', error)
    alert(error.response?.data?.error || 'Failed to generate install command')
  } finally {
    isGeneratingInstall.value = false
  }
}

async function copyCommand(command: string) {
  try {
    await navigator.clipboard.writeText(command)
    commandCopied.value = true
    setTimeout(() => {
      commandCopied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}

async function copyToClipboard(text: string, label: string = 'Text') {
  try {
    await navigator.clipboard.writeText(text)
    // Could add toast notification here
    console.log(`${label} copied to clipboard`)
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}

function downloadConfig() {
  if (!installResult.value) return

  const blob = new Blob([installResult.value.config_yaml], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `hyperfilelens-proxy-${installData.value.name}.yaml`
  a.click()
  URL.revokeObjectURL(url)
}

function getCommandForOS(): string {
  if (!installResult.value) return ''
  return installData.value.os === 'windows'
    ? installResult.value.windows_command
    : installResult.value.install_command
}

// Proxy Actions
function viewProxyDetail(proxy: ProxyNode) {
  selectedProxy.value = proxy
  showDetailDrawer.value = true
  detailTab.value = 'overview'
  
  // Reset tab data cache
  Object.keys(tabData.value).forEach(key => {
    const k = key as keyof typeof tabData.value
    tabData.value[k].loading = false
    tabData.value[k].loaded = false
    if (k === 'tasks' || k === 'heartbeats') {
      tabData.value[k].data = []
    } else {
      tabData.value[k].data = null
    }
  })
  
  // Load overview data immediately (方案A)
  fetchProxyOverview(proxy.id)
  
  openMenuId.value = null
}

// Watch tab changes to load data on demand
watch(detailTab, (newTab) => {
  if (!selectedProxy.value) return
  
  const proxyId = selectedProxy.value.id
  const tab = tabData.value[newTab]
  
  // Only fetch if not already loaded
  if (!tab.loaded && !tab.loading) {
    switch (newTab) {
      case 'overview':
        fetchProxyOverview(proxyId)
        break
      case 'monitor':
        fetchProxyMonitor(proxyId)
        break
      case 'tasks':
        fetchProxyTasks(proxyId)
        break
      case 'heartbeats':
        fetchProxyHeartbeats(proxyId)
        break
    }
  }
})

// Auto refresh functions
function setAutoRefresh(tab: 'monitor' | 'heartbeats', enabled: boolean, intervalSeconds: number) {
  const refresh = autoRefresh.value[tab]
  
  // Clear existing timer
  if (refresh.timer) {
    clearInterval(refresh.timer)
    refresh.timer = null
  }
  
  refresh.enabled = enabled
  refresh.interval = intervalSeconds
  
  if (enabled && selectedProxy.value) {
    refresh.timer = window.setInterval(() => {
      if (selectedProxy.value) {
        if (tab === 'monitor') {
          fetchProxyMonitor(selectedProxy.value.id, true)  // 静默刷新
        } else {
          fetchProxyHeartbeats(selectedProxy.value.id, 1, true)  // 静默刷新
        }
      }
    }, intervalSeconds * 1000)
  }
}

// Refresh current tab
function refreshCurrentTab() {
  if (!selectedProxy.value) return
  
  const proxyId = selectedProxy.value.id
  // 静默刷新，不显示loading，只更新数据
  switch (detailTab.value) {
    case 'overview':
      fetchProxyOverview(proxyId, true)
      break
    case 'monitor':
      fetchProxyMonitor(proxyId, true)
      break
    case 'tasks':
      fetchProxyTasks(proxyId, 1, true)
      break
    case 'heartbeats':
      fetchProxyHeartbeats(proxyId, 1, true)
      fetchProxyOverview(proxyId, true)  // Also refresh overview for stats
      break
  }
}

// Close drawer and cleanup
function closeDetailDrawer() {
  // Stop all auto refresh timers
  if (autoRefresh.value.monitor.timer) {
    clearInterval(autoRefresh.value.monitor.timer)
    autoRefresh.value.monitor.timer = null
  }
  if (autoRefresh.value.heartbeats.timer) {
    clearInterval(autoRefresh.value.heartbeats.timer)
    autoRefresh.value.heartbeats.timer = null
  }
  autoRefresh.value.monitor.enabled = false
  autoRefresh.value.heartbeats.enabled = false
  
  showDetailDrawer.value = false
}

async function viewInstallInfo(proxy: ProxyNode) {
  // Fetch fresh proxy data with install info
  try {
    const response = await api.get(`/api/v1/proxies/${proxy.id}/`)
    selectedProxy.value = response.data
    showInstallInfoModal.value = true
    openMenuId.value = null
  } catch (error) {
    console.error('Failed to fetch proxy install info:', error)
  }
}

function editProxy(proxy: ProxyNode) {
  selectedProxy.value = proxy
  editFormData.value = {
    name: proxy.name,
    hostname: proxy.hostname || '',
    heartbeat_interval: proxy.heartbeat_interval,
    tags: proxy.tags || {},
    labels: proxy.labels || []
  }
  showEditModal.value = true
  openMenuId.value = null
}

async function updateProxy() {
  if (!selectedProxy.value) return
  try {
    await api.patch(`/api/v1/proxies/${selectedProxy.value.id}/`, editFormData.value)
    showEditModal.value = false
    await fetchProxies()
  } catch (error) {
    console.error('Failed to update proxy:', error)
  }
}

function confirmDeleteProxy(proxy: ProxyNode) {
  proxyToDelete.value = proxy
  showDeleteConfirm.value = true
  openMenuId.value = null
}

async function deleteProxy() {
  if (!proxyToDelete.value) return
  try {
    await api.delete(`/api/v1/proxies/${proxyToDelete.value.id}/`)
    showDeleteConfirm.value = false
    proxyToDelete.value = null
    await fetchProxies()
  } catch (error) {
    console.error('Failed to delete proxy:', error)
  }
}

async function updateProxyStatus(proxy: ProxyNode, newStatus: string) {
  try {
    await api.post(`/api/v1/proxies/${proxy.id}/set_status/`, { status: newStatus })
    await fetchProxies()
    openMenuId.value = null
  } catch (error) {
    console.error('Failed to update status:', error)
  }
}

async function regenerateToken(proxy: ProxyNode) {
  if (!confirm(t('proxies.actions.regenerateTokenConfirm'))) return
  try {
    await api.post(`/api/v1/proxies/${proxy.id}/regenerate_token/`)
    await fetchProxies()
    openMenuId.value = null
  } catch (error) {
    console.error('Failed to regenerate token:', error)
  }
}

async function regenerateTokenFromModal() {
  const proxyId = selectedProxy.value?.id
  if (!proxyId) {
    console.error('No proxy ID found')
    return
  }
  if (!confirm(t('proxies.actions.regenerateTokenConfirm'))) return
  
  try {
    const response = await api.post(`/api/v1/proxies/${proxyId}/regenerate_token/`)
    console.log('Regenerate response:', response.data)
    // Update selectedProxy with the new data, ensuring id is preserved
    selectedProxy.value = {
      ...selectedProxy.value,
      ...response.data,
      id: response.data.id || response.data.proxy_id || proxyId // Ensure id is always set
    }
    await fetchProxies()
  } catch (error) {
    console.error('Failed to regenerate token:', error)
    alert(t('proxies.actions.regenerateTokenFailed') || 'Failed to regenerate token')
  }
}

// 菜单位置样式
const menuStyle = ref<Record<string, string>>({})

function toggleMenu(proxyId: string, event?: Event) {
  if (openMenuId.value === proxyId) {
    openMenuId.value = null
    return
  }
  openMenuId.value = proxyId
  
  // 计算菜单位置
  if (event?.target) {
    const target = event.target as HTMLElement
    const rect = target.getBoundingClientRect()
    menuStyle.value = {
      top: `${rect.bottom + 8}px`,
      right: `${window.innerWidth - rect.right}px`,
      width: '192px'
    }
  }
}

// Status helpers
function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700',
    inactive: 'bg-slate-100 text-slate-600',
    offline: 'bg-slate-100 text-slate-600',
    error: 'bg-red-100 text-red-700',
    maintenance: 'bg-amber-100 text-amber-700',
    pending: 'bg-blue-100 text-blue-700',
    installing: 'bg-indigo-100 text-indigo-700'
  }
  return colors[status] || 'bg-slate-100 text-slate-600'
}

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    active: CheckCircleIcon,
    inactive: XCircleIcon,
    offline: XCircleIcon,
    error: XCircleIcon,
    maintenance: WrenchScrewdriverIcon,
    pending: ClockIcon,
    installing: ArrowPathIcon
  }
  return icons[status] || CircleStackIcon
}

function getRoleColor(role: string): string {
  return role === 'agent'
    ? 'bg-indigo-100 text-indigo-700'
    : 'bg-purple-100 text-purple-700'
}

function formatUptime(seconds: number | null): string {
  if (!seconds) return 'N/A'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return timestamp
  }
}

function timeSince(date: string | null): string {
  if (!date) return t('common.never')
  const seconds = Math.floor((new Date().getTime() - new Date(date).getTime()) / 1000)
  if (seconds < 60) return t('common.justNow')
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}${t('common.minutesAgo')}`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}${t('common.hoursAgo')}`
  const days = Math.floor(hours / 24)
  return `${days}${t('common.daysAgo')}`
}

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatBandwidth(bytesIn: number, bytesOut: number, uptimeSeconds: number | null): string {
  if (!uptimeSeconds || uptimeSeconds <= 0) return '-'
  const totalBytes = (bytesIn || 0) + (bytesOut || 0)
  const bytesPerSecond = totalBytes / uptimeSeconds
  if (bytesPerSecond < 1024) return `${bytesPerSecond.toFixed(0)} B/s`
  if (bytesPerSecond < 1024 * 1024) return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`
  return `${(bytesPerSecond / (1024 * 1024)).toFixed(2)} MB/s`
}

// Chart data and options generators
// Chart helper functions
const chartColors = {
  cpu: '#6366f1',
  memory: '#10b981',
  disk: '#f59e0b'
}

function getChartData(type: 'cpu' | 'memory' | 'disk') {
  const monitorData = tabData.value.monitor.data
  if (!monitorData) {
    return { labels: [], datasets: [] }
  }
  
  let data: { timestamp: string; value: number }[] = []
  let label = ''
  const color = chartColors[type]
  
  if (type === 'cpu') {
    data = monitorData.cpu_usage || []
    label = 'CPU'
  } else if (type === 'memory') {
    data = monitorData.memory_usage || []
    label = 'Memory'
  } else {
    data = monitorData.disk_usage || []
    label = 'Disk'
  }
  
  return {
    labels: data.map(d => new Date(d.timestamp).toLocaleTimeString()),
    datasets: [{
      label,
      data: data.map(d => d.value),
      borderColor: color,
      backgroundColor: color + '20',
      fill: true,
      tension: 0.4,
      pointRadius: 2,
      pointHoverRadius: 4,
    }]
  }
}

function getChartOptions(type: 'cpu' | 'memory' | 'disk') {
  let label = ''
  if (type === 'cpu') label = 'CPU'
  else if (type === 'memory') label = 'Memory'
  else label = 'Disk'
  
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          label: (context: { parsed: { y: number | null } }) => 
            `${label}: ${context.parsed.y !== null ? context.parsed.y.toFixed(1) : 0}%`
        }
      }
    },
    scales: {
      x: {
        display: true,
        grid: { display: false },
        ticks: { maxTicksLimit: 8, font: { size: 10 } }
      },
      y: {
        display: true,
        min: 0,
        max: 100,
        grid: { color: '#e5e7eb' },
        ticks: {
          callback: (value: number | string) => value + '%',
          font: { size: 10 }
        }
      }
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false
    }
  }
}

// Get unique network interfaces from network_io data
function getUniqueNetworkInterfaces(): string[] {
  const monitorData = tabData.value.monitor.data
  if (!monitorData?.network_io) return []
  const interfaces = new Set<string>()
  monitorData.network_io.forEach((item: { interface?: string }) => {
    if (item.interface) interfaces.add(item.interface)
  })
  return Array.from(interfaces)
}

// Get unique disks from disk_io data
function getUniqueDisks(): string[] {
  const monitorData = tabData.value.monitor.data
  if (!monitorData?.disk_io) return []
  const disks = new Set<string>()
  monitorData.disk_io.forEach((item: { disk?: string }) => {
    if (item.disk) disks.add(item.disk)
  })
  return Array.from(disks)
}

// Get network I/O chart data
function getNetworkIOChartData(type: 'rx_bytes' | 'tx_bytes' | 'rx_packets' | 'tx_packets' | 'rx_drop' | 'tx_drop' | 'rx_errs' | 'tx_errs') {
  const monitorData = tabData.value.monitor.data
  if (!monitorData?.network_io) return { labels: [], datasets: [] }
  
  let filtered = monitorData.network_io
  if (selectedNetIOInterface.value) {
    filtered = filtered.filter((item: { interface?: string }) => item.interface === selectedNetIOInterface.value)
  }
  
  // Group by timestamp
  const grouped = new Map<string, number>()
  filtered.forEach((item: { timestamp: string; [key: string]: unknown }) => {
    const value = item[type] as number | undefined
    if (value !== undefined) {
      const existing = grouped.get(item.timestamp) || 0
      grouped.set(item.timestamp, existing + value)
    }
  })
  
  const sorted = Array.from(grouped.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  
  return {
    labels: sorted.map(([ts]) => formatTime(ts)),
    datasets: [{
      label: type,
      data: sorted.map(([, v]) => type.includes('bytes') ? v / (1024 * 1024) : v), // Convert to MB for bytes
      borderColor: type.includes('rx') ? '#3b82f6' : '#10b981',
      backgroundColor: type.includes('rx') ? 'rgba(59, 130, 246, 0.1)' : 'rgba(16, 185, 129, 0.1)',
      fill: true,
      tension: 0.4
    }]
  }
}

// Get disk I/O chart data
function getDiskIOChartData(type: 'util' | 'await' | 'r_s' | 'w_s' | 'rkB_s' | 'wkB_s') {
  const monitorData = tabData.value.monitor.data
  if (!monitorData?.disk_io) return { labels: [], datasets: [] }
  
  let filtered = monitorData.disk_io
  if (selectedDiskIO.value) {
    filtered = filtered.filter((item: { disk?: string }) => item.disk === selectedDiskIO.value)
  }
  
  // Group by timestamp
  const grouped = new Map<string, number>()
  filtered.forEach((item: { timestamp: string; [key: string]: unknown }) => {
    const value = item[type] as number | undefined
    if (value !== undefined) {
      const existing = grouped.get(item.timestamp) || 0
      grouped.set(item.timestamp, existing + value)
    }
  })
  
  const sorted = Array.from(grouped.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  
  const colors: Record<string, string> = {
    util: '#ef4444',
    await: '#f59e0b',
    r_s: '#3b82f6',
    w_s: '#10b981',
    rkB_s: '#8b5cf6',
    wkB_s: '#ec4899'
  }
  
  return {
    labels: sorted.map(([ts]) => formatTime(ts)),
    datasets: [{
      label: type,
      data: sorted.map(([, v]) => v),
      borderColor: colors[type] || '#6b7280',
      backgroundColor: (colors[type] || '#6b7280') + '20',
      fill: true,
      tension: 0.4
    }]
  }
}

// Network I/O chart options
function getNetworkIOChartOptions(type: 'rx_bytes' | 'tx_bytes' | 'rx_packets' | 'tx_packets' | 'rx_drop' | 'tx_drop' | 'rx_errs' | 'tx_errs') {
  const isBytes = type.includes('bytes')
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: 'index' as const,
        intersect: false
      }
    },
    scales: {
      x: { display: true, grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
      y: { 
        display: true, 
        beginAtZero: true,
        grid: { color: '#e5e7eb' }, 
        ticks: { 
          callback: (value: number | string) => isBytes ? `${Number(value).toFixed(1)} MB` : value,
          font: { size: 10 } 
        } 
      }
    }
  }
}

// Disk I/O chart options
function getDiskIOChartOptions(type: 'util' | 'await' | 'r_s' | 'w_s' | 'rkB_s' | 'wkB_s') {
  const units: Record<string, string> = { util: '%', await: 'ms', r_s: '/s', w_s: '/s', rkB_s: 'kB/s', wkB_s: 'kB/s' }
  const maxes: Record<string, number | undefined> = { util: 100, await: undefined, r_s: undefined, w_s: undefined, rkB_s: undefined, wkB_s: undefined }
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: 'index' as const,
        intersect: false
      }
    },
    scales: {
      x: { display: true, grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
      y: { 
        display: true, 
        min: 0,
        max: maxes[type],
        grid: { color: '#e5e7eb' }, 
        ticks: { 
          callback: (value: number | string) => `${value}${units[type] || ''}`,
          font: { size: 10 } 
        } 
      }
    }
  }
}

// Calculate heartbeat rate from overview stats
function calculateHeartbeatRate(stats: { heartbeats_24h?: number; expected_24h?: number } | null | undefined): number {
  if (!stats || !stats.expected_24h || stats.expected_24h === 0) return 100
  return Math.round(((stats.heartbeats_24h || 0) / stats.expected_24h) * 100)
}

// Close menu when clicking outside
function closeMenu() {
  openMenuId.value = null
}

// Role icons
const AgentIcon = ComputerDesktopIcon
const SyncIcon = CircleStackIcon

onMounted(() => {
  fetchProxies()
  document.addEventListener('click', closeMenu)

  // Poll for updates every 30 seconds
  pollInterval = window.setInterval(fetchProxies, 30000)
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<template>
  <div class="space-y-6" @click.stop>
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">{{ t('proxies.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('proxies.subtitle') }}</p>
      </div>
      <button
        @click="openInstallWizard"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('proxies.installProxy') }}
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-gradient-to-br from-slate-100 to-slate-200 rounded-lg flex items-center justify-center">
            <ServerIcon class="w-5 h-5 text-slate-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('proxies.stats.total') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.total_proxies || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
            <CheckCircleIcon class="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('proxies.stats.online') }}</p>
            <p class="text-xl font-bold text-emerald-600">{{ stats?.online_proxies || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
            <ComputerDesktopIcon class="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('proxies.roles.agent') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.agent_proxies || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <CircleStackIcon class="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('proxies.roles.sync') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.sync_proxies || 0 }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative flex-1 min-w-[200px]">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('common.search')"
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
        <select
          v-model="selectedRole"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">{{ t('common.role') }}: {{ t('common.all') }}</option>
          <option value="agent">{{ t('proxies.roles.agent') }}</option>
          <option value="sync">{{ t('proxies.roles.sync') }}</option>
        </select>
        <select
          v-model="selectedStatus"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">{{ t('common.status') }}: {{ t('common.all') }}</option>
          <option value="active">{{ t('proxies.status.active') }}</option>
          <option value="pending">{{ t('proxies.status.pending') }}</option>
          <option value="offline">{{ t('proxies.status.offline') }}</option>
          <option value="error">{{ t('proxies.status.error') }}</option>
          <option value="maintenance">{{ t('proxies.status.maintenance') }}</option>
        </select>
        <button
          @click="fetchProxies"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
        <!-- View Toggle -->
        <div class="flex items-center gap-1 border border-slate-200 rounded-lg p-1">
          <button
            @click="viewMode = 'card'"
            :class="[
              'p-2 rounded-md transition-colors',
              viewMode === 'card' ? 'bg-indigo-100 text-indigo-600' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
            ]"
            :title="t('proxies.viewModes.card')"
          >
            <Squares2X2Icon class="w-4 h-4" />
          </button>
          <button
            @click="viewMode = 'list'"
            :class="[
              'p-2 rounded-md transition-colors',
              viewMode === 'list' ? 'bg-indigo-100 text-indigo-600' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
            ]"
            :title="t('proxies.viewModes.list')"
          >
            <Bars3Icon class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Proxies Card View -->
    <template v-if="viewMode === 'card'">
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
    </div>

    <div v-else-if="filteredProxies.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <ServerIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('proxies.empty.title') }}</h3>
      <p class="text-slate-500">{{ t('proxies.empty.description') }}</p>
      <button
        @click="openInstallWizard"
        class="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('proxies.installProxy') }}
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="proxy in paginatedProxies"
        :key="proxy.id"
        class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-slate-300 transition-all group"
      >
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div :class="[
              'w-11 h-11 rounded-xl flex items-center justify-center',
              proxy.role === 'agent'
                ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                : 'bg-gradient-to-br from-purple-500 to-violet-600'
            ]">
              <component :is="proxy.role === 'agent' ? AgentIcon : SyncIcon" class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 class="font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors">{{ proxy.name }}</h3>
              <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-1', getRoleColor(proxy.role)]">
                {{ t(`proxies.roles.${proxy.role}`) }}
              </span>
            </div>
          </div>
          <div class="relative" @click.stop>
            <button
              @click="toggleMenu(proxy.id, $event)"
              class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <EllipsisHorizontalIcon class="w-5 h-5" />
            </button>
            <!-- Dropdown Menu - 使用 Teleport 确保菜单显示在最上层 -->
            <Teleport to="body">
              <div
                v-if="openMenuId === proxy.id"
                class="fixed bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-[9999]"
                :style="menuStyle"
              >
                <button
                  @click="viewProxyDetail(proxy); openMenuId = null"
                  class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                >
                  <InformationCircleIcon class="w-4 h-4" />
                  {{ t('proxies.actions.viewDetails') }}
                </button>
                <button
                  @click="editProxy(proxy); openMenuId = null"
                  class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                >
                  <PencilIcon class="w-4 h-4" />
                  {{ t('proxies.actions.edit') }}
                </button>
                <button
                  @click="regenerateToken(proxy); openMenuId = null"
                  class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                >
                  <ArrowPathIcon class="w-4 h-4" />
                  {{ t('proxies.actions.regenerateToken') }}
                </button>
                <hr class="my-1 border-slate-100" />
                <button
                  v-if="proxy.status === 'active'"
                  @click="updateProxyStatus(proxy, 'maintenance'); openMenuId = null"
                  class="w-full px-4 py-2 text-left text-sm text-amber-600 hover:bg-amber-50 flex items-center gap-2"
                >
                  <PauseIcon class="w-4 h-4" />
                  {{ t('proxies.actions.setMaintenance') }}
                </button>
                <button
                  v-else-if="proxy.status === 'maintenance'"
                  @click="updateProxyStatus(proxy, 'active'); openMenuId = null"
                  class="w-full px-4 py-2 text-left text-sm text-emerald-600 hover:bg-emerald-50 flex items-center gap-2"
                >
                  <PlayIcon class="w-4 h-4" />
                  {{ t('proxies.actions.activate') }}
                </button>
                <hr class="my-1 border-slate-100" />
                <button
                  @click="confirmDeleteProxy(proxy); openMenuId = null"
                  class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                >
                  <TrashIcon class="w-4 h-4" />
                  {{ t('proxies.actions.delete') }}
                </button>
              </div>
            </Teleport>
          </div>
        </div>

        <div class="space-y-3 text-sm">
          <div class="flex items-center gap-2 text-slate-500">
            <MapPinIcon class="w-4 h-4 flex-shrink-0" />
            <span class="truncate">{{ proxy.hostname || proxy.internal_ip || t('proxies.noConnection') }}</span>
          </div>
          <div class="flex items-center gap-2 text-slate-500">
            <ClockIcon class="w-4 h-4 flex-shrink-0" />
            <span>{{ timeSince(proxy.last_heartbeat) }}</span>
          </div>
          <div class="flex items-center gap-2 text-slate-500">
            <CpuChipIcon class="w-4 h-4 flex-shrink-0" />
            <span>
              {{ proxy.operating_system || 'Unknown' }}
              {{ proxy.cpu_cores ? `(${proxy.cpu_cores} cores)` : '' }}
            </span>
          </div>
        </div>

        <!-- Resource Usage -->
        <div v-if="proxy.cpu_usage !== null" class="mt-4 grid grid-cols-3 gap-2 text-center">
          <div class="bg-slate-50 rounded-lg p-2">
            <p class="text-xs text-slate-500">CPU</p>
            <p class="text-sm font-medium text-slate-800">{{ proxy.cpu_usage?.toFixed(1) }}%</p>
          </div>
          <div class="bg-slate-50 rounded-lg p-2">
            <p class="text-xs text-slate-500">Memory</p>
            <p class="text-sm font-medium text-slate-800">{{ proxy.memory_usage?.toFixed(1) }}%</p>
          </div>
          <div class="bg-slate-50 rounded-lg p-2">
            <p class="text-xs text-slate-500">Disk</p>
            <p class="text-sm font-medium text-slate-800">{{ proxy.disk_usage?.toFixed(1) }}%</p>
          </div>
        </div>

        <div class="flex items-center justify-between mt-4 pt-4 border-t border-slate-100">
          <div class="flex items-center gap-1.5">
            <component
              :is="getStatusIcon(proxy.status)"
              :class="[
                'w-4 h-4',
                proxy.status === 'active' ? 'text-emerald-500' :
                proxy.status === 'error' ? 'text-red-500' : 'text-slate-400'
              ]"
            />
            <span :class="['text-xs font-medium', getStatusColor(proxy.status).split(' ').slice(1).join(' ')]">
              {{ t(`proxies.status.${proxy.status}`) }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="proxy.status === 'pending'"
              @click="viewInstallInfo(proxy)"
              class="text-sm font-medium text-amber-600 hover:text-amber-700 flex items-center gap-1"
            >
              <ExclamationTriangleIcon class="w-4 h-4" />
              {{ t('proxies.actions.viewInstall') }}
            </button>
            <button
              @click="viewProxyDetail(proxy)"
              class="text-sm font-medium text-indigo-600 hover:text-indigo-700"
            >
              {{ t('proxies.actions.viewDetails') }} →
            </button>
          </div>
        </div>
      </div>
    </div>
    </template>

    <!-- Proxies List View -->
    <template v-else>
      <div v-if="isLoading" class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
      </div>

      <div v-else-if="filteredProxies.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <ServerIcon class="w-8 h-8 text-slate-400" />
        </div>
        <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('proxies.empty.title') }}</h3>
        <p class="text-slate-500">{{ t('proxies.empty.description') }}</p>
        <button
          @click="openInstallWizard"
          class="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <PlusIcon class="w-4 h-4" />
          {{ t('proxies.installProxy') }}
        </button>
      </div>

      <div v-else class="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-[900px] w-full divide-y divide-slate-200">
            <thead class="bg-slate-50">
              <tr>
                <th class="sticky left-0 bg-slate-50 px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider z-10">{{ t('proxies.list.name') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('proxies.list.role') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('proxies.list.status') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('proxies.list.hostname') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('proxies.list.ip') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('proxies.list.cpuCores') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('proxies.list.memory') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('proxies.list.disk') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('proxies.list.lastHeartbeat') }}</th>
                <th class="sticky right-0 bg-slate-50 px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider z-10">{{ t('proxies.list.actions') }}</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-slate-200">
              <tr
                v-for="proxy in paginatedProxies"
                :key="proxy.id"
                class="hover:bg-slate-50 transition-colors"
              >
                <td class="sticky left-0 bg-white px-4 py-3 whitespace-nowrap z-10 group-hover:bg-slate-50">
                  <div class="flex items-center gap-3">
                    <div :class="[
                      'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                      proxy.role === 'agent'
                        ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                        : 'bg-gradient-to-br from-purple-500 to-violet-600'
                    ]">
                      <component :is="proxy.role === 'agent' ? AgentIcon : SyncIcon" class="w-4 h-4 text-white" />
                    </div>
                    <button
                      @click="viewProxyDetail(proxy)"
                      class="font-medium text-slate-800 hover:text-indigo-600 cursor-pointer transition-colors text-left"
                    >
                      {{ proxy.name }}
                    </button>
                  </div>
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getRoleColor(proxy.role)]">
                    {{ t(`proxies.roles.${proxy.role}`) }}
                  </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <span :class="['inline-flex items-center px-2 py-1 rounded-full text-xs font-medium', getStatusColor(proxy.status)]">
                    {{ t(`proxies.status.${proxy.status}`) }}
                  </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                  {{ proxy.hostname || '-' }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                  {{ proxy.internal_ip || '-' }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                  {{ proxy.cpu_cores ? `${proxy.cpu_cores} ${t('proxies.list.cores')}` : '-' }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <div v-if="proxy.memory_usage !== null" class="flex items-center gap-2">
                    <div class="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all"
                        :class="proxy.memory_usage > 80 ? 'bg-red-500' : proxy.memory_usage > 60 ? 'bg-amber-500' : 'bg-emerald-500'"
                        :style="{ width: `${Math.min(proxy.memory_usage, 100)}%` }"
                      />
                    </div>
                    <span class="text-xs text-slate-500 w-10">{{ proxy.memory_usage?.toFixed(0) }}%</span>
                  </div>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <div v-if="proxy.disk_usage !== null" class="flex items-center gap-2">
                    <div class="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all"
                        :class="proxy.disk_usage > 80 ? 'bg-red-500' : proxy.disk_usage > 60 ? 'bg-amber-500' : 'bg-emerald-500'"
                        :style="{ width: `${Math.min(proxy.disk_usage, 100)}%` }"
                      />
                    </div>
                    <span class="text-xs text-slate-500 w-10">{{ proxy.disk_usage?.toFixed(0) }}%</span>
                  </div>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-500">
                  {{ timeSince(proxy.last_heartbeat) }}
                </td>
                <td class="sticky right-0 bg-white px-4 py-3 whitespace-nowrap z-10 group-hover:bg-slate-50">
                  <div class="flex items-center justify-end gap-2">
                    <button
                      v-if="proxy.status === 'pending'"
                      @click="viewInstallInfo(proxy)"
                      class="p-1.5 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                      :title="t('proxies.actions.viewInstall')"
                    >
                      <ExclamationTriangleIcon class="w-4 h-4" />
                    </button>
                    <button
                      @click="viewProxyDetail(proxy)"
                      class="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                      :title="t('proxies.actions.viewDetails')"
                    >
                      <InformationCircleIcon class="w-4 h-4" />
                    </button>
                    <div class="relative" @click.stop>
                      <button
                        @click="toggleMenu(proxy.id, $event)"
                        class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                      >
                        <EllipsisHorizontalIcon class="w-4 h-4" />
                      </button>
                      <!-- Dropdown Menu - 使用 fixed 定位避免被 sticky 列遮挡 -->
                      <Teleport to="body">
                        <div
                          v-if="openMenuId === proxy.id"
                          ref="menuRef"
                          class="fixed bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-[9999]"
                          :style="menuStyle"
                        >
                          <button
                            @click="viewProxyDetail(proxy); openMenuId = null"
                            class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                          >
                            <InformationCircleIcon class="w-4 h-4" />
                            {{ t('proxies.actions.viewDetails') }}
                          </button>
                          <button
                            @click="editProxy(proxy); openMenuId = null"
                            class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                          >
                            <PencilIcon class="w-4 h-4" />
                            {{ t('proxies.actions.edit') }}
                          </button>
                          <button
                            @click="regenerateToken(proxy); openMenuId = null"
                            class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                          >
                            <ArrowPathIcon class="w-4 h-4" />
                            {{ t('proxies.actions.regenerateToken') }}
                          </button>
                          <hr class="my-1 border-slate-100" />
                          <button
                            v-if="proxy.status === 'active'"
                            @click="updateProxyStatus(proxy, 'maintenance'); openMenuId = null"
                            class="w-full px-4 py-2 text-left text-sm text-amber-600 hover:bg-amber-50 flex items-center gap-2"
                          >
                            <PauseIcon class="w-4 h-4" />
                            {{ t('proxies.actions.setMaintenance') }}
                          </button>
                          <button
                            v-else-if="proxy.status === 'maintenance'"
                            @click="updateProxyStatus(proxy, 'active'); openMenuId = null"
                            class="w-full px-4 py-2 text-left text-sm text-emerald-600 hover:bg-emerald-50 flex items-center gap-2"
                          >
                            <PlayIcon class="w-4 h-4" />
                            {{ t('proxies.actions.activate') }}
                          </button>
                          <hr class="my-1 border-slate-100" />
                          <button
                            @click="confirmDeleteProxy(proxy); openMenuId = null"
                            class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                          >
                            <TrashIcon class="w-4 h-4" />
                            {{ t('proxies.actions.delete') }}
                          </button>
                        </div>
                      </Teleport>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Pagination -->
        <Pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total-items="filteredProxies.length"
        />
      </div>
    </template>

    <!-- Install Wizard Modal -->
    <div v-if="showInstallWizard" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div class="bg-white rounded-2xl shadow-xl max-w-2xl w-full my-8">
        <!-- Header -->
        <div class="flex items-center justify-between p-5 border-b border-slate-100">
          <div>
            <h2 class="text-lg font-semibold text-slate-800">{{ t('proxies.install.title') }}</h2>
            <p class="text-sm text-slate-500 mt-1">{{ t('proxies.install.subtitle') }}</p>
          </div>
          <button @click="showInstallWizard = false" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <!-- Steps -->
        <div class="p-5">
          <!-- Step 1: Select Role -->
          <div v-if="installStep === 1" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Agent Proxy -->
              <button
                @click="installData.role = 'agent'; installStep = 2"
                :class="[
                  'p-6 rounded-xl border-2 text-left transition-all',
                  installData.role === 'agent'
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-slate-200 hover:border-slate-300'
                ]"
              >
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center mb-4">
                  <ComputerDesktopIcon class="w-6 h-6 text-white" />
                </div>
                <h3 class="font-semibold text-slate-800">{{ t('proxies.roles.agent') }}</h3>
                <p class="text-sm text-slate-500 mt-2">{{ t('proxies.install.agentDescription') }}</p>
                
                <!-- Agent Requirements -->
                <div class="mt-4 pt-4 border-t border-slate-200">
                  <p class="text-xs font-medium text-slate-600 mb-2">{{ t('proxies.install.requirements') }}</p>
                  <div class="space-y-1.5 text-xs text-slate-500">
                    <div class="flex items-center gap-2">
                      <ComputerDesktopIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.agentOS') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <CpuChipIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.agentCPU') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <CircleStackIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.agentMemory') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <ServerIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.agentDisk') }}</span>
                    </div>
                  </div>
                </div>
              </button>

              <!-- Sync Proxy -->
              <button
                @click="installData.role = 'sync'; installData.os = 'linux'; installStep = 2"
                :class="[
                  'p-6 rounded-xl border-2 text-left transition-all',
                  installData.role === 'sync'
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-slate-200 hover:border-slate-300'
                ]"
              >
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center mb-4">
                  <CircleStackIcon class="w-6 h-6 text-white" />
                </div>
                <h3 class="font-semibold text-slate-800">{{ t('proxies.roles.sync') }}</h3>
                <p class="text-sm text-slate-500 mt-2">{{ t('proxies.install.syncDescription') }}</p>
                
                <!-- Sync Requirements -->
                <div class="mt-4 pt-4 border-t border-slate-200">
                  <p class="text-xs font-medium text-slate-600 mb-2">{{ t('proxies.install.requirements') }}</p>
                  <div class="space-y-1.5 text-xs text-slate-500">
                    <div class="flex items-center gap-2">
                      <ComputerDesktopIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.syncOS') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <CpuChipIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.syncCPU') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <CircleStackIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.syncMemory') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <ServerIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.syncDisk') }}</span>
                    </div>
                  </div>
                </div>
              </button>
            </div>
            
            <!-- Info Banner -->
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
              <InformationCircleIcon class="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div class="text-sm text-blue-700">
                <p class="font-medium">{{ t('proxies.install.infoTitle') }}</p>
                <p class="mt-1">{{ t('proxies.install.infoDescription') }}</p>
              </div>
            </div>
          </div>

          <!-- Step 2: Configuration -->
          <div v-if="installStep === 2" class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">
                {{ t('proxies.install.proxyName') }}
              </label>
              <input
                v-model="installData.name"
                type="text"
                required
                :placeholder="t('proxies.install.namePlaceholder')"
                class="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <!-- OS Selection - Only for Agent Proxy -->
            <div v-if="installData.role === 'agent'">
              <label class="block text-sm font-medium text-slate-700 mb-1">
                {{ t('proxies.install.targetOS') }}
              </label>
              <div class="grid grid-cols-3 gap-3">
                <button
                  v-for="os in ['linux', 'windows', 'macos']"
                  :key="os"
                  @click="installData.os = os"
                  :class="[
                    'px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
                    installData.os === os
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  ]"
                >
                  {{ t(`proxies.install.os.${os}`) }}
                </button>
              </div>
            </div>

            <!-- Sync Proxy - Fixed OS Info -->
            <div v-else class="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <ComputerDesktopIcon class="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p class="text-sm font-medium text-purple-800">{{ t('proxies.install.syncFixedOS') }}</p>
                  <p class="text-xs text-purple-600">{{ t('proxies.install.syncFixedOSNote') }}</p>
                </div>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">
                {{ t('proxies.install.labels') }}
              </label>
              <div class="flex gap-2 mb-2">
                <input
                  v-model="installData.newLabel"
                  type="text"
                  :placeholder="t('proxies.install.labelPlaceholder')"
                  class="flex-1 px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  @keyup.enter="addLabel"
                />
                <button
                  @click="addLabel"
                  class="px-4 py-2 text-sm font-medium text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50"
                >
                  {{ t('common.add') }}
                </button>
              </div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="label in installData.labels"
                  :key="label"
                  class="inline-flex items-center gap-1 px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-sm"
                >
                  {{ label }}
                  <button @click="removeLabel(label)" class="hover:text-red-500">
                    <XMarkIcon class="w-3.5 h-3.5" />
                  </button>
                </span>
              </div>
            </div>

            <div class="flex justify-between pt-4">
              <button
                @click="installStep = 1"
                class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                {{ t('common.back') }}
              </button>
              <button
                @click="generateInstallCommand"
                :disabled="!installData.name || isGeneratingInstall"
                class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ isGeneratingInstall ? t('proxies.install.generating') : t('proxies.install.generateCommand') }}
              </button>
            </div>
          </div>

          <!-- Step 3: Install Command -->
          <div v-if="installStep === 3 && installResult" class="space-y-5">
            <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-4 flex items-start gap-3">
              <CheckCircleIcon class="w-5 h-5 text-emerald-500 mt-0.5" />
              <div>
                <p class="text-sm font-medium text-emerald-800">{{ t('proxies.install.ready') }}</p>
                <p class="text-sm text-emerald-600 mt-1">{{ t('proxies.install.readyDescription') }}</p>
              </div>
            </div>

            <!-- Installation Instructions -->
            <div class="space-y-4">
              <!-- Step 1: Run Command -->
              <div class="bg-slate-50 rounded-lg p-4">
                <div class="flex items-center gap-2 mb-3">
                  <span class="w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold flex items-center justify-center">1</span>
                  <span class="text-sm font-medium text-slate-700">{{ t('proxies.install.step1Title') }}</span>
                </div>
                <p class="text-xs text-slate-500 mb-3">{{ t('proxies.install.step1Desc') }}</p>
                <div class="relative">
                  <pre class="bg-slate-900 text-slate-100 p-4 rounded-lg text-sm overflow-x-auto whitespace-pre-wrap font-mono">{{ getCommandForOS() }}</pre>
                  <div class="absolute top-2 right-2 flex gap-2">
                    <button
                      @click="downloadConfig"
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-700 rounded-lg hover:bg-slate-600"
                    >
                      <ArrowDownTrayIcon class="w-3.5 h-3.5" />
                      {{ t('proxies.install.downloadConfig') }}
                    </button>
                    <button
                      @click="copyCommand(getCommandForOS())"
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500"
                    >
                      <ClipboardDocumentIcon class="w-3.5 h-3.5" />
                      {{ commandCopied ? t('common.copied') : t('common.copy') }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- Step 2: Keep Credentials -->
              <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div class="flex items-start gap-3">
                  <ExclamationTriangleIcon class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                  <div class="flex-1">
                    <p class="text-sm font-medium text-amber-800">{{ t('proxies.install.credentialsTitle') }}</p>
                    <p class="text-xs text-amber-600 mt-1">{{ t('proxies.install.credentialsDesc') }}</p>
                  </div>
                </div>
              </div>

              <!-- Credentials -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-white border border-slate-200 rounded-lg p-4">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="w-6 h-6 rounded-full bg-slate-100 text-slate-600 text-xs font-bold flex items-center justify-center">ID</span>
                    <span class="text-sm font-medium text-slate-700">{{ t('proxies.install.proxyId') }}</span>
                  </div>
                  <p class="text-xs text-slate-500 mb-2">{{ t('proxies.install.proxyIdDesc') }}</p>
                  <div class="flex items-center gap-2 bg-slate-50 rounded px-3 py-2">
                    <p class="text-sm font-mono text-slate-800 flex-1 truncate">{{ installResult.proxy_id }}</p>
                    <button @click="copyCommand(installResult.proxy_id)" class="text-slate-400 hover:text-slate-600">
                      <DocumentDuplicateIcon class="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div class="bg-white border border-slate-200 rounded-lg p-4">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="w-6 h-6 rounded-full bg-slate-100 text-slate-600 text-xs font-bold flex items-center justify-center">
                      <KeyIcon class="w-3.5 h-3.5" />
                    </span>
                    <span class="text-sm font-medium text-slate-700">{{ t('proxies.install.apiToken') }}</span>
                  </div>
                  <p class="text-xs text-slate-500 mb-2">{{ t('proxies.install.apiTokenDesc') }}</p>
                  <div class="flex items-center gap-2 bg-slate-50 rounded px-3 py-2">
                    <p class="text-sm font-mono text-slate-800 flex-1 break-all">{{ installResult.api_token || 'N/A' }}</p>
                    <button @click="copyCommand(installResult.api_token)" class="text-slate-400 hover:text-slate-600 flex-shrink-0">
                      <DocumentDuplicateIcon class="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex justify-between pt-4">
              <button
                @click="installStep = 2"
                class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                {{ t('common.back') }}
              </button>
              <button
                @click="showInstallWizard = false; fetchProxies()"
                class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                {{ t('proxies.install.done') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Install Info Modal -->
    <div v-if="showInstallInfoModal && selectedProxy" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div class="bg-white rounded-2xl shadow-xl max-w-2xl w-full my-8">
        <!-- Header -->
        <div class="flex items-center justify-between p-5 border-b border-slate-100">
          <div>
            <h2 class="text-lg font-semibold text-slate-800">{{ t('proxies.installInfo.title') }}</h2>
            <p class="text-sm text-slate-500 mt-1">{{ selectedProxy.name }} - {{ t(`proxies.roles.${selectedProxy.role}`) }}</p>
          </div>
          <button @click="showInstallInfoModal = false" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <!-- Warning Banner -->
        <div class="mx-5 mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
          <ExclamationTriangleIcon class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p class="text-sm font-medium text-amber-800">{{ t('proxies.installInfo.warning') }}</p>
            <p class="text-xs text-amber-600 mt-1">{{ t('proxies.installInfo.warningDesc') }}</p>
          </div>
        </div>

        <!-- Content -->
        <div class="p-5 space-y-5">
          <!-- Step 1: Install Command -->
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <span class="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-sm font-medium">1</span>
              <h3 class="font-medium text-slate-800">{{ t('proxies.installInfo.installCommand') }}</h3>
            </div>
            <div class="relative bg-slate-900 rounded-lg p-4">
              <code class="text-sm text-slate-300 break-all whitespace-pre-wrap">{{ selectedProxy.install_command || t('proxies.installInfo.noCommand') }}</code>
              <div class="absolute top-2 right-2 flex gap-2">
                <button
                  @click="selectedProxy.install_command && copyToClipboard(selectedProxy.install_command, 'Command')"
                  class="p-1.5 bg-slate-700 hover:bg-slate-600 rounded text-slate-300 hover:text-white transition-colors"
                  :title="t('common.copy')"
                  :disabled="!selectedProxy.install_command"
                >
                  <DocumentDuplicateIcon class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          <!-- Step 2: Credentials -->
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <span class="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-sm font-medium">2</span>
              <h3 class="font-medium text-slate-800">{{ t('proxies.installInfo.credentials') }}</h3>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Proxy ID -->
              <div class="bg-slate-50 rounded-lg p-4">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs font-medium text-slate-500 uppercase">{{ t('proxies.installInfo.proxyId') }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <code class="text-sm text-slate-700 break-all">{{ selectedProxy.id }}</code>
                  <button
                    @click="copyToClipboard(selectedProxy.id, 'Proxy ID')"
                    class="ml-2 p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-600"
                  >
                    <DocumentDuplicateIcon class="w-4 h-4" />
                  </button>
                </div>
                <p class="text-xs text-slate-400 mt-2">{{ t('proxies.installInfo.proxyIdDesc') }}</p>
              </div>

              <!-- API Token -->
              <div class="bg-slate-50 rounded-lg p-4">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs font-medium text-slate-500 uppercase">{{ t('proxies.installInfo.apiToken') }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <code class="text-sm text-slate-700 break-all">{{ selectedProxy.api_token || 'N/A' }}</code>
                  <button
                    v-if="selectedProxy.api_token"
                    @click="copyToClipboard(selectedProxy.api_token, 'API Token')"
                    class="ml-2 p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-600"
                  >
                    <DocumentDuplicateIcon class="w-4 h-4" />
                  </button>
                </div>
                <p class="text-xs text-slate-400 mt-2">{{ t('proxies.installInfo.apiTokenDesc') }}</p>
              </div>
            </div>

            <!-- Install Token Status -->
            <div class="bg-slate-50 rounded-lg p-4">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <KeyIcon class="w-4 h-4 text-slate-400" />
                  <span class="text-sm font-medium text-slate-700">{{ t('proxies.installInfo.installToken') }}</span>
                </div>
                <span :class="[
                  'text-xs font-medium px-2 py-1 rounded',
                  selectedProxy.install_token_used 
                    ? 'bg-slate-200 text-slate-600' 
                    : 'bg-emerald-100 text-emerald-700'
                ]">
                  {{ selectedProxy.install_token_used ? t('proxies.installInfo.tokenUsed') : t('proxies.installInfo.tokenAvailable') }}
                </span>
              </div>
            </div>
          </div>

          <!-- Help Section -->
          <div class="bg-blue-50 rounded-lg p-4">
            <h4 class="text-sm font-medium text-blue-800 mb-2">{{ t('proxies.installInfo.help') }}</h4>
            <ul class="text-xs text-blue-600 space-y-1 list-disc list-inside">
              <li>{{ t('proxies.installInfo.helpStep1') }}</li>
              <li>{{ t('proxies.installInfo.helpStep2') }}</li>
              <li>{{ t('proxies.installInfo.helpStep3') }}</li>
            </ul>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between p-5 border-t border-slate-100">
          <button
            @click="regenerateTokenFromModal"
            class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-600 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors"
          >
            <ArrowPathIcon class="w-4 h-4" />
            {{ t('proxies.actions.regenerateToken') }}
          </button>
          <button
            @click="showInstallInfoModal = false"
            class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            {{ t('common.close') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Proxy Detail Drawer -->
    <Transition name="drawer">
      <div v-if="showDetailDrawer" class="fixed inset-0 z-50">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/50" @click="closeDetailDrawer"></div>
        
        <!-- Drawer Panel -->
        <div class="absolute top-0 right-0 h-full w-[75%] bg-white shadow-2xl flex flex-col">
          <!-- Header -->
          <div class="flex items-center justify-between p-5 border-b border-slate-100 bg-white flex-shrink-0">
            <div class="flex items-center gap-3">
              <div :class="[
                'w-10 h-10 rounded-xl flex items-center justify-center',
                selectedProxy?.role === 'agent'
                  ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                  : 'bg-gradient-to-br from-purple-500 to-violet-600'
              ]">
                <component :is="selectedProxy?.role === 'agent' ? AgentIcon : SyncIcon" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 class="text-lg font-semibold text-slate-800">{{ selectedProxy?.name }}</h2>
                <div class="flex items-center gap-2 mt-1">
                  <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getRoleColor(selectedProxy?.role || 'agent')]">
                    {{ t(`proxies.roles.${selectedProxy?.role}`) }}
                  </span>
                  <span :class="['px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(selectedProxy?.status || 'pending')]">
                    {{ t(`proxies.status.${selectedProxy?.status}`) }}
                  </span>
                  <span v-if="selectedProxy?.is_online" class="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-medium">
                    {{ t('proxies.online') }}
                  </span>
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button @click="refreshCurrentTab" class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg" :title="t('common.refresh')">
                <ArrowPathIcon class="w-5 h-5" />
              </button>
              <button @click="closeDetailDrawer" class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
                <XMarkIcon class="w-5 h-5" />
              </button>
            </div>
          </div>

          <!-- Tabs -->
          <div class="border-b border-slate-100 bg-slate-50 px-5 flex-shrink-0">
            <nav class="flex gap-1 -mb-px">
              <button
                @click="detailTab = 'overview'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'overview'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                ]"
              >
                {{ t('proxies.detail.tabs.overview') }}
              </button>
              <button
                v-if="selectedProxy?.status === 'pending'"
                @click="detailTab = 'install'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'install'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                ]"
              >
                {{ t('proxies.detail.tabs.install') }}
              </button>
              <button
                @click="detailTab = 'monitor'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'monitor'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                ]"
              >
                {{ t('proxies.detail.tabs.monitor') }}
              </button>
              <button
                @click="detailTab = 'tasks'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'tasks'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                ]"
              >
                {{ t('proxies.detail.tabs.tasks') }}
              </button>
              <button
                @click="detailTab = 'heartbeats'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'heartbeats'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                ]"
              >
                {{ t('proxies.detail.tabs.heartbeats') }}
              </button>
            </nav>
          </div>

          <!-- Tab Content -->
          <div class="flex-1 overflow-y-auto p-5">
            <!-- Loading indicator for current tab -->
            <div v-if="tabData[detailTab]?.loading" class="flex items-center justify-center py-12">
              <ArrowPathIcon class="w-6 h-6 text-indigo-500 animate-spin" />
            </div>
            
            <!-- Overview Tab -->
            <div v-else-if="detailTab === 'overview'" class="space-y-6">
              <template v-if="tabData.overview.data">
                <!-- Basic Info Section -->
                <div>
                  <h3 class="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
                    <InformationCircleIcon class="w-4 h-4 text-indigo-500" />
                    {{ t('proxies.detail.sections.basicInfo') }}
                  </h3>
                  <div class="bg-slate-50 rounded-xl p-4">
                    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.proxyId') }}</p>
                        <div class="flex items-center gap-1">
                          <p class="text-sm font-mono text-slate-800 truncate">{{ tabData.overview.data.id }}</p>
                          <button @click="copyToClipboard(tabData.overview.data.id, 'Proxy ID')" class="p-1 text-slate-400 hover:text-indigo-600">
                            <ClipboardDocumentIcon class="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.role') }}</p>
                        <p class="text-sm font-medium text-slate-800">{{ t(`proxies.roles.${tabData.overview.data.role}`) }}</p>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.status') }}</p>
                        <span :class="['px-2 py-0.5 rounded text-xs font-medium', getStatusColor(tabData.overview.data.status)]">
                          {{ t(`proxies.status.${tabData.overview.data.status}`) }}
                        </span>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.createdAt') }}</p>
                        <p class="text-sm text-slate-800">{{ new Date(tabData.overview.data.created_at).toLocaleString() }}</p>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.owner') }}</p>
                        <p class="text-sm text-slate-800">{{ tabData.overview.data.owner_name || '-' }}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- System Info Section -->
                <div>
                  <h3 class="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
                    <ComputerDesktopIcon class="w-4 h-4 text-emerald-500" />
                    {{ t('proxies.detail.sections.systemInfo') }}
                  </h3>
                  <div class="bg-slate-50 rounded-xl p-4">
                    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.hostname') }}</p>
                        <p class="text-sm font-medium text-slate-800">{{ tabData.overview.data.hostname || '-' }}</p>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.internalIp') }}</p>
                        <p class="text-sm font-medium text-slate-800">{{ tabData.overview.data.internal_ip || '-' }}</p>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.operatingSystem') }}</p>
                        <p class="text-sm font-medium text-slate-800">{{ tabData.overview.data.operating_system || '-' }}</p>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.proxyVersion') }}</p>
                        <p class="text-sm font-medium text-slate-800">{{ tabData.overview.data.version || '-' }}</p>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.kopiaVersion') }}</p>
                        <p class="text-sm font-medium text-slate-800">{{ tabData.overview.data.kopia_version || '-' }}</p>
                      </div>
                      <div>
                        <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.uptime') }}</p>
                        <p class="text-sm font-medium text-slate-800">{{ formatUptime(tabData.overview.data.uptime_seconds) }}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Hardware Resources Section -->
                <div>
                  <h3 class="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
                    <CpuChipIcon class="w-4 h-4 text-amber-500" />
                    {{ t('proxies.detail.sections.hardwareResources') }}
                  </h3>
                  <div class="grid grid-cols-3 gap-4">
                    <div class="bg-slate-50 rounded-xl p-4 text-center">
                      <p class="text-xs text-slate-500 mb-2">{{ t('proxies.detail.cpu') }}</p>
                      <p class="text-3xl font-bold text-slate-800">{{ (tabData.overview.data.cpu_usage || 0).toFixed(1) }}<span class="text-lg">%</span></p>
                      <div class="w-full h-2 bg-slate-200 rounded-full mt-2 overflow-hidden">
                        <div class="h-full bg-indigo-500 rounded-full transition-all" :style="{ width: `${tabData.overview.data.cpu_usage || 0}%` }" />
                      </div>
                      <p class="text-xs text-slate-400 mt-2">{{ tabData.overview.data.cpu_cores || '-' }} {{ t('proxies.detail.cores') }}</p>
                    </div>
                    <div class="bg-slate-50 rounded-xl p-4 text-center">
                      <p class="text-xs text-slate-500 mb-2">{{ t('proxies.detail.memory') }}</p>
                      <p class="text-3xl font-bold text-slate-800">{{ (tabData.overview.data.memory_usage || 0).toFixed(1) }}<span class="text-lg">%</span></p>
                      <div class="w-full h-2 bg-slate-200 rounded-full mt-2 overflow-hidden">
                        <div class="h-full bg-emerald-500 rounded-full transition-all" :style="{ width: `${tabData.overview.data.memory_usage || 0}%` }" />
                      </div>
                      <p class="text-xs text-slate-400 mt-2">{{ tabData.overview.data.memory_total ? `${(tabData.overview.data.memory_total / 1024**3).toFixed(1)} GB` : '-' }}</p>
                    </div>
                    <div class="bg-slate-50 rounded-xl p-4 text-center">
                      <p class="text-xs text-slate-500 mb-2">{{ t('proxies.detail.disk') }}</p>
                      <p class="text-3xl font-bold text-slate-800">{{ (tabData.overview.data.disk_usage || 0).toFixed(1) }}<span class="text-lg">%</span></p>
                      <div class="w-full h-2 bg-slate-200 rounded-full mt-2 overflow-hidden">
                        <div class="h-full bg-amber-500 rounded-full transition-all" :style="{ width: `${tabData.overview.data.disk_usage || 0}%` }" />
                      </div>
                      <p class="text-xs text-slate-400 mt-2">{{ tabData.overview.data.disk_total ? `${(tabData.overview.data.disk_total / 1024**3).toFixed(1)} GB` : '-' }}</p>
                    </div>
                  </div>
                </div>

                <!-- Stats Section -->
                <div class="grid grid-cols-2 gap-4">
                  <div class="bg-slate-50 rounded-xl p-4">
                    <h4 class="text-sm font-semibold text-slate-800 mb-3">{{ t('proxies.detail.heartbeatStats') }}</h4>
                    <div class="space-y-2">
                      <div class="flex justify-between">
                        <span class="text-xs text-slate-500">{{ t('proxies.detail.heartbeats24h') }}</span>
                        <span class="text-sm font-medium text-slate-800">{{ tabData.overview.data.stats?.heartbeats_24h || 0 }}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-xs text-slate-500">{{ t('proxies.detail.expected24h') }}</span>
                        <span class="text-sm font-medium text-slate-800">{{ tabData.overview.data.stats?.expected_24h || 0 }}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-xs text-slate-500">{{ t('proxies.detail.missedHeartbeats') }}</span>
                        <span class="text-sm font-medium" :class="tabData.overview.data.stats?.missed_heartbeats > 0 ? 'text-amber-600' : 'text-slate-800'">
                          {{ tabData.overview.data.stats?.missed_heartbeats || 0 }}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div class="bg-slate-50 rounded-xl p-4">
                    <h4 class="text-sm font-semibold text-slate-800 mb-3">{{ t('proxies.detail.taskStats') }}</h4>
                    <div class="space-y-2">
                      <div class="flex justify-between">
                        <span class="text-xs text-slate-500">{{ t('proxies.detail.totalTasks') }}</span>
                        <span class="text-sm font-medium text-slate-800">{{ tabData.overview.data.task_stats?.total || 0 }}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-xs text-slate-500">{{ t('proxies.detail.completed') }}</span>
                        <span class="text-sm font-medium text-emerald-600">{{ tabData.overview.data.task_stats?.completed || 0 }}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-xs text-slate-500">{{ t('proxies.detail.failed') }}</span>
                        <span class="text-sm font-medium text-red-600">{{ tabData.overview.data.task_stats?.failed || 0 }}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-xs text-slate-500">{{ t('proxies.detail.running') }}</span>
                        <span class="text-sm font-medium text-blue-600">{{ tabData.overview.data.task_stats?.running || 0 }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <!-- Install Tab -->
            <div v-else-if="detailTab === 'install' && selectedProxy?.status === 'pending'" class="space-y-4">
              <!-- Warning Banner -->
              <div class="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
                <ExclamationTriangleIcon class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p class="text-sm font-medium text-amber-800">{{ t('proxies.installInfo.warning') }}</p>
                  <p class="text-xs text-amber-600 mt-1">{{ t('proxies.installInfo.warningDesc') }}</p>
                </div>
              </div>

              <!-- Install Command -->
              <div class="bg-slate-900 rounded-xl p-4">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs text-slate-400">{{ t('proxies.installInfo.installCommand') }}</span>
                  <button
                    @click="selectedProxy?.install_command && copyToClipboard(selectedProxy.install_command, 'Command')"
                    class="text-slate-400 hover:text-white"
                    :disabled="!selectedProxy?.install_command"
                  >
                    <DocumentDuplicateIcon class="w-4 h-4" />
                  </button>
                </div>
                <pre class="text-sm text-slate-300 whitespace-pre-wrap break-all">{{ selectedProxy?.install_command || '-' }}</pre>
              </div>

              <!-- Credentials -->
              <div class="grid grid-cols-2 gap-4">
                <div class="bg-slate-50 rounded-lg p-4">
                  <p class="text-xs text-slate-500 mb-1">{{ t('proxies.install.proxyId') }}</p>
                  <div class="flex items-center gap-2">
                    <code class="text-sm text-slate-800 font-mono truncate">{{ selectedProxy?.id }}</code>
                    <button @click="copyToClipboard(selectedProxy?.id, 'Proxy ID')" class="text-slate-400 hover:text-indigo-600">
                      <ClipboardDocumentIcon class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                <div class="bg-slate-50 rounded-lg p-4">
                  <p class="text-xs text-slate-500 mb-1">{{ t('proxies.install.apiToken') }}</p>
                  <div class="flex items-center gap-2">
                    <code class="text-sm text-slate-800 font-mono truncate">{{ selectedProxy?.api_token ? `${selectedProxy.api_token.substring(0, 12)}...` : '-' }}</code>
                    <button v-if="selectedProxy?.api_token" @click="copyToClipboard(selectedProxy.api_token, 'API Token')" class="text-slate-400 hover:text-indigo-600">
                      <ClipboardDocumentIcon class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- Token Status -->
              <div class="flex items-center gap-2">
                <span :class="[
                  'px-3 py-1 rounded-full text-xs font-medium',
                  selectedProxy?.install_token_used ? 'bg-slate-100 text-slate-500' : 'bg-emerald-100 text-emerald-700'
                ]">
                  {{ selectedProxy?.install_token_used ? t('proxies.installInfo.tokenUsed') : t('proxies.installInfo.tokenUnused') }}
                </span>
              </div>

              <!-- Regenerate Token Button -->
              <button
                @click="regenerateTokenFromModal"
                class="w-full px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors flex items-center justify-center gap-2"
              >
                <KeyIcon class="w-4 h-4" />
                {{ t('proxies.actions.regenerateToken') }}
              </button>
            </div>

            <!-- Monitor Tab -->
            <div v-else-if="detailTab === 'monitor'" class="space-y-4">
              <!-- Auto Refresh Control -->
              <div class="flex items-center justify-between bg-slate-50 rounded-xl p-3">
                <div class="flex items-center gap-2">
                  <ClockIcon class="w-4 h-4 text-slate-500" />
                  <span class="text-sm text-slate-600">{{ t('proxies.monitoring.autoRefresh') }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <select
                    v-model="autoRefresh.monitor.interval"
                    @change="setAutoRefresh('monitor', autoRefresh.monitor.interval > 0, autoRefresh.monitor.interval)"
                    class="text-sm border border-slate-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option :value="0">{{ t('proxies.monitoring.refreshOff') }}</option>
                    <option :value="10">{{ t('proxies.monitoring.refresh10s') }}</option>
                    <option :value="30">{{ t('proxies.monitoring.refresh30s') }}</option>
                    <option :value="60">{{ t('proxies.monitoring.refresh1m') }}</option>
                    <option :value="300">{{ t('proxies.monitoring.refresh5m') }}</option>
                  </select>
                  <button @click="refreshCurrentTab" class="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-white rounded-lg" :title="t('proxies.monitoring.refreshNow')">
                    <ArrowPathIcon class="w-4 h-4" />
                  </button>
                </div>
              </div>

              <template v-if="tabData.monitor.data">
                <!-- Time Range Selector -->
                <div class="flex items-center justify-between bg-slate-50 rounded-xl p-4">
                  <div class="flex items-center gap-2">
                    <CalendarIcon class="w-5 h-5 text-slate-500" />
                    <span class="text-sm font-medium text-slate-700">{{ t('proxies.monitoring.timeRange') }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      v-for="range in ['1h', '6h', '24h', '7d', '30d']"
                      :key="range"
                      @click="setTimeRange(range as any)"
                      :class="[
                        'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                        monitorTimeRange === range
                          ? 'bg-indigo-500 text-white'
                          : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                      ]"
                    >
                      {{ range }}
                    </button>
                    <button
                      @click="setTimeRange('custom')"
                      :class="[
                        'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                        monitorTimeRange === 'custom'
                          ? 'bg-indigo-500 text-white'
                          : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                      ]"
                    >
                      {{ t('proxies.monitoring.custom') }}
                    </button>
                  </div>
                </div>

                <!-- Custom Date Picker -->
                <div v-if="showCustomDatePicker" class="bg-slate-50 rounded-xl p-4">
                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <label class="block text-xs text-slate-500 mb-1">{{ t('proxies.detail.startTime') }}</label>
                      <input
                        type="datetime-local"
                        v-model="customTimeRange.start"
                        class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label class="block text-xs text-slate-500 mb-1">{{ t('proxies.detail.endTime') }}</label>
                      <input
                        type="datetime-local"
                        v-model="customTimeRange.end"
                        class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                  <button
                    @click="applyCustomTimeRange"
                    class="mt-3 px-4 py-2 text-sm font-medium bg-indigo-500 text-white rounded-lg hover:bg-indigo-600"
                  >
                    {{ t('proxies.detail.apply') }}
                  </button>
                </div>

                <!-- System Overview Cards -->
                <div class="grid grid-cols-6 gap-3">
                  <div class="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-xl p-3">
                    <p class="text-xs opacity-80">{{ t('proxies.monitoring.cpuUsage') }}</p>
                    <p class="text-xl font-bold text-indigo-700 mt-1">{{ (tabData.monitor.data.current?.cpu_usage || 0).toFixed(1) }}%</p>
                    <p class="text-xs opacity-70 mt-1">{{ t('proxies.monitoring.cpuCores') }}: {{ tabData.monitor.data.current?.cpu_cores || '-' }}</p>
                  </div>
                  <div class="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-xl p-3">
                    <p class="text-xs opacity-80">{{ t('proxies.monitoring.memoryUsage') }}</p>
                    <p class="text-xl font-bold text-emerald-700 mt-1">{{ (tabData.monitor.data.current?.memory_usage || 0).toFixed(1) }}%</p>
                    <p class="text-xs opacity-70 mt-1">{{ t('proxies.monitoring.memoryTotal') }}: {{ tabData.monitor.data.current?.memory_total_gb || '-' }} GB</p>
                  </div>
                  <div class="bg-gradient-to-br from-amber-50 to-amber-100 rounded-xl p-3">
                    <p class="text-xs opacity-80">{{ t('proxies.monitoring.diskUsage') }}</p>
                    <p class="text-xl font-bold text-amber-700 mt-1">{{ (tabData.monitor.data.current?.disk_usage || 0).toFixed(1) }}%</p>
                    <p class="text-xs opacity-70 mt-1">{{ t('proxies.monitoring.diskTotal') }}: {{ tabData.monitor.data.current?.disk_total_gb || '-' }} GB</p>
                  </div>
                  <div class="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-3">
                    <p class="text-xs opacity-80">{{ t('proxies.detail.uptime') }}</p>
                    <p class="text-xl font-bold text-blue-700 mt-1">{{ formatUptime(tabData.monitor.data.uptime_seconds) }}</p>
                    <p class="text-xs opacity-70 mt-1">{{ t('proxies.detail.lastHeartbeat') }}: {{ tabData.monitor.data.last_heartbeat ? new Date(tabData.monitor.data.last_heartbeat).toLocaleTimeString() : '-' }}</p>
                  </div>
                  <div class="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-3">
                    <p class="text-xs opacity-80">{{ t('proxies.monitoring.networkIn') }}</p>
                    <p class="text-xl font-bold text-purple-700 mt-1">{{ formatBytes(tabData.monitor.data.network_stats?.bytes_recv) }}</p>
                    <p class="text-xs opacity-70 mt-1">{{ tabData.monitor.data.network_stats?.bytes_recv_gb?.toFixed(2) || 0 }} GB</p>
                  </div>
                  <div class="bg-gradient-to-br from-cyan-50 to-cyan-100 rounded-xl p-3">
                    <p class="text-xs opacity-80">{{ t('proxies.monitoring.networkOut') }}</p>
                    <p class="text-xl font-bold text-cyan-700 mt-1">{{ formatBytes(tabData.monitor.data.network_stats?.bytes_sent) }}</p>
                    <p class="text-xs opacity-70 mt-1">{{ tabData.monitor.data.network_stats?.bytes_sent_gb?.toFixed(2) || 0 }} GB</p>
                  </div>
                </div>

                <!-- Charts Row 1: CPU, Memory, Disk -->
                <div class="grid grid-cols-3 gap-4">
                  <div class="bg-white border border-slate-200 rounded-xl p-4">
                    <h4 class="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
                      <CpuChipIcon class="w-4 h-4 text-indigo-500" />
                      {{ t('proxies.monitoring.cpuChart') }}
                    </h4>
                    <div class="h-40">
                      <Line :data="getChartData('cpu')" :options="getChartOptions('cpu')" />
                    </div>
                  </div>
                  <div class="bg-white border border-slate-200 rounded-xl p-4">
                    <h4 class="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
                      <ServerIcon class="w-4 h-4 text-emerald-500" />
                      {{ t('proxies.monitoring.memoryChart') }}
                    </h4>
                    <div class="h-40">
                      <Line :data="getChartData('memory')" :options="getChartOptions('memory')" />
                    </div>
                  </div>
                  <div class="bg-white border border-slate-200 rounded-xl p-4">
                    <h4 class="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
                      <CircleStackIcon class="w-4 h-4 text-amber-500" />
                      {{ t('proxies.monitoring.diskChart') }}
                    </h4>
                    <div class="h-40">
                      <Line :data="getChartData('disk')" :options="getChartOptions('disk')" />
                    </div>
                  </div>
                </div>

                <!-- Network Interfaces Section -->
                <div v-if="tabData.monitor.data.network_interfaces && tabData.monitor.data.network_interfaces.length > 0" class="bg-white border border-slate-200 rounded-xl p-4">
                  <div class="flex items-center justify-between mb-4">
                    <h4 class="text-sm font-semibold text-slate-800 flex items-center gap-2">
                      <WifiIcon class="w-4 h-4 text-blue-500" />
                      {{ t('proxies.monitoring.networkInterfaces') }}
                    </h4>
                    <select
                      v-model="selectedNetworkInterface"
                      class="text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="all">{{ t('proxies.monitoring.allInterfaces') }}</option>
                      <option v-for="(iface, index) in tabData.monitor.data.network_interfaces" :key="index" :value="iface.name">
                        {{ iface.name }} ({{ iface.ip_address || 'No IP' }})
                      </option>
                    </select>
                  </div>

                  <!-- Network Interface Details -->
                  <div v-if="selectedNetworkInterface === 'all'" class="overflow-x-auto">
                    <table class="w-full text-sm">
                      <thead>
                        <tr class="border-b border-slate-200">
                          <th class="text-left py-2 px-3 text-slate-600 font-medium">{{ t('proxies.detail.interface') }}</th>
                          <th class="text-left py-2 px-3 text-slate-600 font-medium">{{ t('proxies.monitoring.ipAddress') }}</th>
                          <th class="text-left py-2 px-3 text-slate-600 font-medium">{{ t('proxies.monitoring.macAddress') }}</th>
                          <th class="text-right py-2 px-3 text-slate-600 font-medium">{{ t('proxies.monitoring.bytesIn') }}</th>
                          <th class="text-right py-2 px-3 text-slate-600 font-medium">{{ t('proxies.monitoring.bytesOut') }}</th>
                          <th class="text-right py-2 px-3 text-slate-600 font-medium">{{ t('proxies.monitoring.bandwidth') }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(iface, index) in tabData.monitor.data.network_interfaces" :key="index" class="border-b border-slate-100 hover:bg-slate-50">
                          <td class="py-2 px-3 font-medium text-slate-800">
                            <div class="flex items-center gap-2">
                              <span class="w-2 h-2 rounded-full bg-green-500"></span>
                              {{ iface.name }}
                            </div>
                          </td>
                          <td class="py-2 px-3 text-slate-600 font-mono text-xs">{{ iface.ip_address || '-' }}</td>
                          <td class="py-2 px-3 text-slate-600 font-mono text-xs">{{ iface.mac_address || '-' }}</td>
                          <td class="py-2 px-3 text-right text-slate-600">{{ formatBytes(iface.bytes_in) }}</td>
                          <td class="py-2 px-3 text-right text-slate-600">{{ formatBytes(iface.bytes_out) }}</td>
                          <td class="py-2 px-3 text-right text-slate-600">{{ formatBandwidth(iface.bytes_in, iface.bytes_out, tabData.monitor.data.uptime_seconds) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- Single Interface Detail -->
                  <div v-else class="space-y-4">
                    <div v-for="(iface, index) in tabData.monitor.data.network_interfaces" :key="index">
                      <div v-if="iface.name === selectedNetworkInterface" class="grid grid-cols-4 gap-4">
                        <div class="bg-slate-50 rounded-lg p-3">
                          <p class="text-xs text-slate-500">{{ t('proxies.monitoring.ipAddress') }}</p>
                          <p class="text-sm font-medium text-slate-800 mt-1 font-mono">{{ iface.ip_address || '-' }}</p>
                        </div>
                        <div class="bg-slate-50 rounded-lg p-3">
                          <p class="text-xs text-slate-500">{{ t('proxies.monitoring.macAddress') }}</p>
                          <p class="text-sm font-medium text-slate-800 mt-1 font-mono">{{ iface.mac_address || '-' }}</p>
                        </div>
                        <div class="bg-slate-50 rounded-lg p-3">
                          <p class="text-xs text-slate-500">{{ t('proxies.monitoring.networkIn') }}</p>
                          <p class="text-sm font-medium text-purple-700 mt-1">{{ formatBytes(iface.bytes_in) }}</p>
                        </div>
                        <div class="bg-slate-50 rounded-lg p-3">
                          <p class="text-xs text-slate-500">{{ t('proxies.monitoring.networkOut') }}</p>
                          <p class="text-sm font-medium text-cyan-700 mt-1">{{ formatBytes(iface.bytes_out) }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Network I/O Chart Section -->
                <div v-if="tabData.monitor.data.network_io && tabData.monitor.data.network_io.length > 0" class="bg-white border border-slate-200 rounded-xl p-4">
                    <div class="flex items-center justify-between mb-4">
                      <h4 class="text-sm font-semibold text-slate-800 flex items-center gap-2">
                        <ChartBarIcon class="w-4 h-4 text-blue-500" />
                        {{ t('proxies.monitoring.networkIOChart') }}
                      </h4>
                      <select
                        v-model="selectedNetIOInterface"
                        class="text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="">{{ t('proxies.monitoring.allNetInterfaces') }}</option>
                        <option v-for="iface in getUniqueNetworkInterfaces()" :key="iface" :value="iface">{{ iface }}</option>
                      </select>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="h-48">
                        <p class="text-xs text-slate-500 mb-2">{{ t('proxies.monitoring.rxBytes') }} (MB)</p>
                        <Line :data="getNetworkIOChartData('rx_bytes')" :options="getNetworkIOChartOptions('rx_bytes')" />
                      </div>
                      <div class="h-48">
                        <p class="text-xs text-slate-500 mb-2">{{ t('proxies.monitoring.txBytes') }} (MB)</p>
                        <Line :data="getNetworkIOChartData('tx_bytes')" :options="getNetworkIOChartOptions('tx_bytes')" />
                      </div>
                    </div>
                    <div class="grid grid-cols-4 gap-4 mt-4">
                      <div class="bg-blue-50 rounded-lg p-2">
                        <p class="text-xs text-slate-500">{{ t('proxies.monitoring.rxPackets') }}</p>
                        <p class="text-sm font-medium text-blue-700">{{ formatBytes(networkIOStats.rxPackets) }}</p>
                      </div>
                      <div class="bg-green-50 rounded-lg p-2">
                        <p class="text-xs text-slate-500">{{ t('proxies.monitoring.txPackets') }}</p>
                        <p class="text-sm font-medium text-green-700">{{ formatBytes(networkIOStats.txPackets) }}</p>
                      </div>
                      <div class="bg-red-50 rounded-lg p-2">
                        <p class="text-xs text-slate-500">{{ t('proxies.monitoring.rxDrop') }}</p>
                        <p class="text-sm font-medium text-red-700">{{ networkIOStats.rxDrop }}</p>
                      </div>
                      <div class="bg-orange-50 rounded-lg p-2">
                        <p class="text-xs text-slate-500">{{ t('proxies.monitoring.txErrs') }}</p>
                        <p class="text-sm font-medium text-orange-700">{{ networkIOStats.txErrs }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- Disk I/O Chart Section -->
                  <div v-if="tabData.monitor.data.disk_io && tabData.monitor.data.disk_io.length > 0" class="bg-white border border-slate-200 rounded-xl p-4">
                    <div class="flex items-center justify-between mb-4">
                      <h4 class="text-sm font-semibold text-slate-800 flex items-center gap-2">
                        <ServerIcon class="w-4 h-4 text-orange-500" />
                        {{ t('proxies.monitoring.diskIOChart') }}
                      </h4>
                      <select
                        v-model="selectedDiskIO"
                        class="text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="">{{ t('proxies.monitoring.allDisks') }}</option>
                        <option v-for="disk in getUniqueDisks()" :key="disk" :value="disk">{{ disk }}</option>
                      </select>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="h-48">
                        <p class="text-xs text-slate-500 mb-2">{{ t('proxies.monitoring.diskUtil') }} (%)</p>
                        <Line :data="getDiskIOChartData('util')" :options="getDiskIOChartOptions('util')" />
                      </div>
                      <div class="h-48">
                        <p class="text-xs text-slate-500 mb-2">{{ t('proxies.monitoring.diskAwait') }} (ms)</p>
                        <Line :data="getDiskIOChartData('await')" :options="getDiskIOChartOptions('await')" />
                      </div>
                    </div>
                    <div class="grid grid-cols-4 gap-4 mt-4">
                      <div class="bg-blue-50 rounded-lg p-2">
                        <p class="text-xs text-slate-500">{{ t('proxies.monitoring.diskRs') }}</p>
                        <p class="text-sm font-medium text-blue-700">{{ diskIOStats.avgRs }}/s</p>
                      </div>
                      <div class="bg-green-50 rounded-lg p-2">
                        <p class="text-xs text-slate-500">{{ t('proxies.monitoring.diskWs') }}</p>
                        <p class="text-sm font-medium text-green-700">{{ diskIOStats.avgWs }}/s</p>
                      </div>
                      <div class="bg-purple-50 rounded-lg p-2">
                        <p class="text-xs text-slate-500">{{ t('proxies.monitoring.diskRkBs') }}</p>
                        <p class="text-sm font-medium text-purple-700">{{ diskIOStats.avgRkBs }} kB/s</p>
                      </div>
                      <div class="bg-pink-50 rounded-lg p-2">
                        <p class="text-xs text-slate-500">{{ t('proxies.monitoring.diskWkBs') }}</p>
                        <p class="text-sm font-medium text-pink-700">{{ diskIOStats.avgWkBs }} kB/s</p>
                      </div>
                    </div>
                  </div>

              </template>
            </div>

            <!-- Tasks Tab -->
            <div v-else-if="detailTab === 'tasks'" class="space-y-4">
              <!-- Task Stats -->
              <div class="grid grid-cols-4 gap-4">
                <div class="bg-slate-50 rounded-xl p-4">
                  <p class="text-xs text-slate-500">{{ t('proxies.tasks.total') }}</p>
                  <p class="text-2xl font-bold text-slate-800 mt-1">{{ tabData.tasks.stats?.total || 0 }}</p>
                </div>
                <div class="bg-emerald-50 rounded-xl p-4">
                  <p class="text-xs text-slate-500">{{ t('proxies.tasks.completed') }}</p>
                  <p class="text-2xl font-bold text-emerald-700 mt-1">{{ tabData.tasks.stats?.completed || 0 }}</p>
                </div>
                <div class="bg-red-50 rounded-xl p-4">
                  <p class="text-xs text-slate-500">{{ t('proxies.tasks.failed') }}</p>
                  <p class="text-2xl font-bold text-red-700 mt-1">{{ tabData.tasks.stats?.failed || 0 }}</p>
                </div>
                <div class="bg-blue-50 rounded-xl p-4">
                  <p class="text-xs text-slate-500">{{ t('proxies.tasks.running') }}</p>
                  <p class="text-2xl font-bold text-blue-700 mt-1">{{ tabData.tasks.stats?.running || 0 }}</p>
                </div>
              </div>

              <div v-if="tabData.tasks.data.length === 0" class="bg-slate-50 rounded-xl p-8 text-center">
                <ClipboardDocumentListIcon class="w-16 h-16 mx-auto mb-4 text-slate-300" />
                <p class="text-slate-500 font-medium">{{ t('proxies.detail.noTasks') }}</p>
                <p class="text-sm text-slate-400 mt-1">{{ t('proxies.detail.noTasksHint') }}</p>
              </div>
              <div v-else class="space-y-3">
                <div v-for="task in tabData.tasks.data" :key="task.id" class="bg-slate-50 rounded-xl p-4">
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-3">
                      <span :class="[
                        'px-2 py-1 rounded text-xs font-medium',
                        task.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                        task.status === 'running' ? 'bg-blue-100 text-blue-700' :
                        task.status === 'failed' ? 'bg-red-100 text-red-700' :
                        'bg-slate-100 text-slate-700'
                      ]">
                        {{ t(`proxies.detail.taskStatus.${task.status}`) || task.status }}
                      </span>
                      <span class="text-sm font-medium text-slate-800">{{ task.task_type }}</span>
                    </div>
                    <span class="text-xs text-slate-500">{{ new Date(task.created_at).toLocaleString() }}</span>
                  </div>
                  <div v-if="task.progress !== null && task.progress !== undefined" class="mt-2">
                    <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                      <span>{{ task.progress_message || '' }}</span>
                      <span>{{ task.progress }}%</span>
                    </div>
                    <div class="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div class="h-full bg-indigo-500 rounded-full transition-all" :style="{ width: `${task.progress}%` }" />
                    </div>
                  </div>
                  <p v-if="task.error_message" class="mt-2 text-xs text-red-600">{{ task.error_message }}</p>
                </div>
              </div>
            </div>

            <!-- Heartbeats Tab -->
            <div v-else-if="detailTab === 'heartbeats'" class="space-y-4">
              <!-- Auto Refresh Control -->
              <div class="flex items-center justify-between bg-slate-50 rounded-xl p-3">
                <div class="flex items-center gap-2">
                  <SignalIcon class="w-4 h-4 text-slate-500" />
                  <span class="text-sm text-slate-600">{{ t('proxies.monitoring.autoRefresh') }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <select
                    v-model="autoRefresh.heartbeats.interval"
                    @change="setAutoRefresh('heartbeats', autoRefresh.heartbeats.interval > 0, autoRefresh.heartbeats.interval)"
                    class="text-sm border border-slate-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option :value="0">{{ t('proxies.monitoring.refreshOff') }}</option>
                    <option :value="10">{{ t('proxies.monitoring.refresh10s') }}</option>
                    <option :value="30">{{ t('proxies.monitoring.refresh30s') }}</option>
                    <option :value="60">{{ t('proxies.monitoring.refresh1m') }}</option>
                    <option :value="300">{{ t('proxies.monitoring.refresh5m') }}</option>
                  </select>
                  <button @click="refreshCurrentTab" class="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-white rounded-lg">
                    <ArrowPathIcon class="w-4 h-4" />
                  </button>
                </div>
              </div>

              <!-- Stats - Use overview data for consistency -->
              <div class="grid grid-cols-4 gap-4">
                <div class="bg-slate-50 rounded-xl p-4">
                  <p class="text-xs text-slate-500">{{ t('proxies.heartbeats.totalHeartbeats') }}</p>
                  <p class="text-2xl font-bold text-slate-800 mt-1">{{ tabData.overview.data?.stats?.heartbeats_24h || 0 }}</p>
                  <p class="text-xs text-slate-400 mt-1">24h {{ t('proxies.heartbeats.totalHeartbeats') }}</p>
                </div>
                <div class="bg-slate-50 rounded-xl p-4">
                  <p class="text-xs text-slate-500">{{ t('proxies.heartbeats.expectedHeartbeats') }}</p>
                  <p class="text-2xl font-bold text-indigo-600 mt-1">{{ tabData.overview.data?.stats?.expected_24h || 0 }}</p>
                  <p class="text-xs text-slate-400 mt-1">24h {{ t('proxies.heartbeats.expectedHeartbeats') }}</p>
                </div>
                <div class="bg-slate-50 rounded-xl p-4">
                  <p class="text-xs text-slate-500">{{ t('proxies.heartbeats.missedHeartbeats') }}</p>
                  <p class="text-2xl font-bold" :class="(tabData.overview.data?.stats?.missed_heartbeats || 0) > 0 ? 'text-red-600' : 'text-slate-800'" >{{ tabData.overview.data?.stats?.missed_heartbeats || 0 }}</p>
                  <p class="text-xs text-slate-400 mt-1">{{ t('proxies.heartbeats.missedHeartbeats') }}</p>
                </div>
                <div class="bg-slate-50 rounded-xl p-4">
                  <p class="text-xs text-slate-500">{{ t('proxies.heartbeats.heartbeatRate') }}</p>
                  <p class="text-2xl font-bold text-emerald-600 mt-1">{{ calculateHeartbeatRate(tabData.overview.data?.stats) }}%</p>
                  <p class="text-xs text-slate-400 mt-1">{{ t('proxies.heartbeats.heartbeatRate') }}</p>
                </div>
              </div>

              <div v-if="tabData.heartbeats.data.length === 0" class="bg-slate-50 rounded-xl p-8 text-center">
                <SignalIcon class="w-16 h-16 mx-auto mb-4 text-slate-300" />
                <p class="text-slate-500 font-medium">{{ t('proxies.detail.noHeartbeats') }}</p>
                <p class="text-sm text-slate-400 mt-1">{{ t('proxies.detail.noHeartbeatsHint') }}</p>
              </div>
              <div v-else class="space-y-2">
                <div v-for="heartbeat in tabData.heartbeats.data" :key="heartbeat.id" class="bg-slate-50 rounded-lg p-3">
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-slate-500">{{ new Date(heartbeat.timestamp).toLocaleString() }}</span>
                    <div class="flex items-center gap-3 text-xs">
                      <span class="text-indigo-600">CPU: {{ (heartbeat.cpu_usage || 0).toFixed(1) }}%</span>
                      <span class="text-emerald-600">Mem: {{ (heartbeat.memory_usage || 0).toFixed(1) }}%</span>
                      <span class="text-amber-600">Disk: {{ (heartbeat.disk_usage || 0).toFixed(1) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
    <!-- Edit Modal -->
    <div v-if="showEditModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-lg w-full">
        <div class="flex items-center justify-between p-5 border-b border-slate-100">
          <h2 class="text-lg font-semibold text-slate-800">{{ t('proxies.edit.title') }}</h2>
          <button @click="showEditModal = false" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>
        <form @submit.prevent="updateProxy" class="p-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('proxies.form.name') }}</label>
            <input
              v-model="editFormData.name"
              type="text"
              required
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('proxies.form.hostname') }}</label>
            <input
              v-model="editFormData.hostname"
              type="text"
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('proxies.form.heartbeatInterval') }}</label>
            <input
              v-model.number="editFormData.heartbeat_interval"
              type="number"
              min="5"
              max="300"
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div class="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              @click="showEditModal = false"
              class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              type="submit"
              class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              {{ t('common.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirm -->
    <div v-if="showDeleteConfirm && proxyToDelete" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-md w-full">
        <div class="p-6">
          <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <ExclamationTriangleIcon class="w-6 h-6 text-red-600" />
          </div>
          <h3 class="text-lg font-semibold text-slate-800 text-center mb-2">{{ t('proxies.delete.title') }}</h3>
          <p class="text-sm text-slate-500 text-center">{{ t('proxies.delete.description', { name: proxyToDelete.name }) }}</p>
        </div>
        <div class="flex justify-center gap-3 p-5 border-t border-slate-100">
          <button
            @click="showDeleteConfirm = false; proxyToDelete = null"
            class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            @click="deleteProxy"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
          >
            {{ t('common.delete') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Drawer transition */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-enter-active .absolute.top-0.right-0,
.drawer-leave-active .absolute.top-0.right-0 {
  transition: transform 0.3s ease;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .absolute.top-0.right-0,
.drawer-leave-to .absolute.top-0.right-0 {
  transform: translateX(100%);
}

/* Ensure drawer panel doesn't transition */
.drawer-enter-active .absolute.inset-0.bg-black\/50,
.drawer-leave-active .absolute.inset-0.bg-black\/50 {
  transition: opacity 0.3s ease;
}
</style>
