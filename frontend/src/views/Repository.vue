<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { repositoriesApi, nodesApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { Repository } from '@/types/repository'
import type { ProxyNode } from '@/types/proxy'
import Pagination from '@/components/Pagination.vue'
import {
  PlusIcon,
  CircleStackIcon,
  CloudIcon,
  ServerIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  TrashIcon,
  CheckCircleIcon,
  LinkIcon,
  PlayIcon,
  ChevronRightIcon,
  ExclamationCircleIcon,
  Squares2X2Icon,
  Bars3Icon,
  InformationCircleIcon,
  XCircleIcon,
  PencilIcon,
  SignalIcon
} from '@heroicons/vue/24/outline'
import { GlobeAltIcon, PlusCircleIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/solid'

const { t } = useI18n()

const isLoading = ref(true)
const repositories = ref<Repository[]>([])
const nodes = ref<ProxyNode[]>([])
const searchQuery = ref('')
const typeFilter = ref('')
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedRepo = ref<Repository | null>(null)
const isEditMode = ref(false)
const editingRepoId = ref<string | null>(null)

// Connection test states
const testingConnection = ref<string | null>(null)
const creatingBucket = ref(false)
const connectionTestResult = ref<Record<string, { success: boolean; message: string }>>({})

// View mode
const viewMode = ref<'card' | 'list'>('card')

// Pagination
const currentPage = ref(1)
const pageSize = ref(10)

// Repository type selection
const repoTypes = [
  { value: 's3', label: 'S3 对象存储', icon: CloudIcon, color: 'orange' },
  { value: 'nas', label: 'NAS/NFS/CIFS', icon: ServerIcon, color: 'purple' },
  { value: 'local', label: '本地文件系统', icon: FolderIcon, color: 'blue' }
]

// New repository form
const newRepo = ref({
  name: '',
  repo_type: 's3' as 's3' | 'nas' | 'local',
  description: '',
  capacity: 0 as number,  // 存储配额，单位 GB，0 表示无限制
  bound_node: '' as string | null,
  // S3 config
  s3_config: {
    endpoint: '',
    bucket: '',
    region: '',
    prefix: '',
    access_key: '',
    secret_key: '',
    use_tls: true,
    url_style: 'virtual' as 'virtual' | 'path',  // URL 访问风格：virtual (Virtual Hosted) 或 path (Path Style)
    bucket_mode: 'existing' as 'existing' | 'new'  // 选择已有或新建
  },
  // NAS config
  nas_config: {
    server: '',
    export_path: '',
    mount_type: 'nfs' as 'nfs' | 'cifs',
    mount_options: '',
    username: '',
    password: ''
  },
  // Local config
  local_config: {
    path: ''
  }
})

// Form validation errors
const formErrors = ref<Record<string, string>>({})

// S3 Bucket related states
const s3BucketList = ref<Array<{ name: string; creation_date?: string; size?: number }>>([])
const isLoadingBuckets = ref(false)
const bucketListError = ref('')
const checkingBucketName = ref(false)
const bucketNameAvailable = ref<boolean | null>(null)
const bucketNameMessage = ref('')

// Bucket name validation rules (S3 standard)
const BUCKET_NAME_RULES = {
  minLength: 3,
  maxLength: 63,
  // Must start and end with letter or number
  // Can contain lowercase letters, numbers, hyphens, and periods
  pattern: /^[a-z0-9][a-z0-9.-]*[a-z0-9]$|^[a-z0-9]$/,
  // Cannot be IP address format
  ipPattern: /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/,
  // Cannot contain consecutive periods or hyphens next to periods
  consecutivePattern: /\.\.|\.-|-\./
}

// Validate bucket name according to S3 rules
function validateBucketName(name: string): { valid: boolean; message: string } {
  if (!name) {
    return { valid: false, message: t('repository.s3.bucketNameRequired') }
  }
  
  if (name.length < BUCKET_NAME_RULES.minLength) {
    return { valid: false, message: t('repository.s3.bucketNameTooShort', { min: BUCKET_NAME_RULES.minLength }) }
  }
  
  if (name.length > BUCKET_NAME_RULES.maxLength) {
    return { valid: false, message: t('repository.s3.bucketNameTooLong', { max: BUCKET_NAME_RULES.maxLength }) }
  }
  
  // Check for valid characters (lowercase letters, numbers, hyphens, periods)
  if (!/^[a-z0-9.-]+$/.test(name)) {
    return { valid: false, message: t('repository.s3.bucketNameInvalidChars') }
  }
  
  // Check start and end
  if (!/^[a-z0-9]/.test(name) || !/[a-z0-9]$/.test(name)) {
    return { valid: false, message: t('repository.s3.bucketNameStartEnd') }
  }
  
  // Check for IP address format
  if (BUCKET_NAME_RULES.ipPattern.test(name)) {
    return { valid: false, message: t('repository.s3.bucketNameIPFormat') }
  }
  
  // Check for consecutive periods or hyphens next to periods
  if (BUCKET_NAME_RULES.consecutivePattern.test(name)) {
    return { valid: false, message: t('repository.s3.bucketNameConsecutive') }
  }
  
  return { valid: true, message: '' }
}

// Fetch S3 bucket list
async function fetchBucketList() {
  const { endpoint, access_key, secret_key, use_tls } = newRepo.value.s3_config
  
  // Check required fields first
  if (!endpoint || !access_key || !secret_key) {
    bucketListError.value = t('repository.s3.fillCredentialsFirst')
    return
  }
  
  // Validate endpoint format
  try {
    const url = new URL(endpoint)
    if (!url.hostname) {
      bucketListError.value = t('repository.s3.invalidEndpoint')
      return
    }
  } catch {
    bucketListError.value = t('repository.s3.invalidEndpoint')
    return
  }
  
  isLoadingBuckets.value = true
  bucketListError.value = ''
  s3BucketList.value = []
  
  try {
    const response = await repositoriesApi.listBuckets({
      endpoint,
      region: newRepo.value.s3_config.region || undefined,
      access_key,
      secret_key,
      use_tls,
      filter_by_region: true  // Filter buckets by configured region
    })
    
    if (response.data.buckets) {
      s3BucketList.value = response.data.buckets
    }
    
    // Show suggestion if no buckets match the configured region
    if (response.data.suggestion && response.data.matched_count === 0) {
      bucketListError.value = response.data.suggestion
    }
  } catch (error: any) {
    console.error('[S3] Failed to fetch bucket list:', error)
    
    // Handle timeout specifically
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      bucketListError.value = t('repository.s3.connectionTimeout')
      return
    }
    
    // Handle network errors
    if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
      bucketListError.value = t('repository.s3.networkError')
      return
    }
    
    // Extract detailed error message from backend
    const errorData = error.response?.data || {}
    let errorMessage = t('repository.s3.fetchBucketsFailed')
    
    if (errorData.message) {
      errorMessage = errorData.message
    }
    
    // Add hint if available
    if (errorData.hint) {
      errorMessage += ` ${errorData.hint}`
    }
    
    // Add error code for debugging
    if (errorData.error_code) {
      console.error(`[S3] Error code: ${errorData.error_code}, HTTP: ${errorData.http_status}`)
      errorMessage += ` (${errorData.error_code})`
    }
    
    // Add details
    if (errorData.details) {
      console.error(`[S3] Details: ${errorData.details}`)
    }
    
    bucketListError.value = errorMessage
  } finally {
    isLoadingBuckets.value = false
  }
}

// Check bucket name availability
async function checkBucketNameAvailability() {
  const { endpoint, access_key, secret_key, bucket, use_tls } = newRepo.value.s3_config
  
  // Validate bucket name format first
  const validation = validateBucketName(bucket)
  if (!validation.valid) {
    bucketNameAvailable.value = false
    bucketNameMessage.value = validation.message
    return
  }
  
  // Check required fields
  if (!endpoint || !access_key || !secret_key) {
    bucketNameMessage.value = t('repository.s3.fillCredentialsFirst')
    return
  }
  
  checkingBucketName.value = true
  bucketNameMessage.value = ''
  
  try {
    const response = await repositoriesApi.checkBucketName({
      endpoint,
      region: newRepo.value.s3_config.region || undefined,
      access_key,
      secret_key,
      bucket_name: bucket,
      use_tls
    })
    
    bucketNameAvailable.value = response.data.available
    bucketNameMessage.value = response.data.message
  } catch (error: any) {
    console.error('[S3] Failed to check bucket name:', error)
    
    const errorData = error.response?.data || {}
    let errorMessage = t('repository.s3.checkBucketFailed')
    
    if (errorData.message) {
      errorMessage = errorData.message
    }
    
    if (errorData.hint) {
      errorMessage += ` ${errorData.hint}`
    }
    
    if (errorData.error_code) {
      console.error(`[S3] Error code: ${errorData.error_code}`)
    }
    
    bucketNameAvailable.value = false
    bucketNameMessage.value = errorMessage
  } finally {
    checkingBucketName.value = false
  }
}

// Watch bucket mode changes
watch(() => newRepo.value.s3_config.bucket_mode, () => {
  // Reset bucket related states
  newRepo.value.s3_config.bucket = ''
  s3BucketList.value = []
  bucketListError.value = ''
  bucketNameAvailable.value = null
  bucketNameMessage.value = ''
  clearError('bucket')
})

// Watch bucket name changes for new bucket mode
watch(() => newRepo.value.s3_config.bucket, (newName) => {
  if (newRepo.value.s3_config.bucket_mode === 'new') {
    // Reset availability status when name changes
    bucketNameAvailable.value = null
    bucketNameMessage.value = ''
    
    // Real-time validation
    if (newName) {
      const validation = validateBucketName(newName)
      if (!validation.valid) {
        bucketNameMessage.value = validation.message
      }
    }
  }
})

// Watch credentials changes to reset bucket list
watch([
  () => newRepo.value.s3_config.endpoint,
  () => newRepo.value.s3_config.access_key,
  () => newRepo.value.s3_config.secret_key
], () => {
  s3BucketList.value = []
  bucketListError.value = ''
  bucketNameAvailable.value = null
  bucketNameMessage.value = ''
})

// Validate form before submission
function validateForm(): boolean {
  formErrors.value = {}
  
  // Name is required
  if (!newRepo.value.name.trim()) {
    formErrors.value.name = t('repository.validation.nameRequired')
  }
  
  // Validate based on repository type
  if (newRepo.value.repo_type === 's3') {
    if (!newRepo.value.s3_config.endpoint.trim()) {
      formErrors.value.endpoint = t('repository.validation.endpointRequired')
    }
    if (!newRepo.value.s3_config.bucket.trim()) {
      formErrors.value.bucket = t('repository.validation.bucketRequired')
    }
    if (!newRepo.value.s3_config.access_key.trim()) {
      formErrors.value.access_key = t('repository.validation.accessKeyRequired')
    }
    if (!newRepo.value.s3_config.secret_key.trim()) {
      formErrors.value.secret_key = t('repository.validation.secretKeyRequired')
    }
  } else if (newRepo.value.repo_type === 'nas') {
    if (!newRepo.value.nas_config.server.trim()) {
      formErrors.value.server = t('repository.validation.serverRequired')
    }
    if (!newRepo.value.nas_config.export_path.trim()) {
      formErrors.value.export_path = t('repository.validation.exportPathRequired')
    }
    if (newRepo.value.nas_config.mount_type === 'cifs') {
      if (!newRepo.value.nas_config.username.trim()) {
        formErrors.value.username = t('repository.validation.usernameRequired')
      }
      if (!newRepo.value.nas_config.password.trim()) {
        formErrors.value.password = t('repository.validation.passwordRequired')
      }
    }
    if (!newRepo.value.bound_node) {
      formErrors.value.bound_node = t('repository.validation.proxyRequired')
    }
  } else if (newRepo.value.repo_type === 'local') {
    if (!newRepo.value.bound_node) {
      formErrors.value.bound_node = t('repository.validation.proxyRequired')
    }
    if (!newRepo.value.local_config.path.trim()) {
      formErrors.value.path = t('repository.validation.pathRequired')
    }
  }
  
  return Object.keys(formErrors.value).length === 0
}

// Check if form is valid and complete
const isFormValid = computed(() => {
  // Name is always required
  if (!newRepo.value.name.trim()) return false
  
  const type = newRepo.value.repo_type
  
  if (type === 's3') {
    return !!(
      newRepo.value.s3_config.endpoint.trim() &&
      newRepo.value.s3_config.bucket.trim() &&
      newRepo.value.s3_config.access_key.trim() &&
      newRepo.value.s3_config.secret_key.trim()
    )
  }
  
  if (type === 'nas') {
    const hasBasic = !!(
      newRepo.value.nas_config.server.trim() &&
      newRepo.value.nas_config.export_path.trim() &&
      newRepo.value.bound_node
    )
    if (newRepo.value.nas_config.mount_type === 'cifs') {
      return hasBasic && !!(
        newRepo.value.nas_config.username.trim() &&
        newRepo.value.nas_config.password.trim()
      )
    }
    return hasBasic
  }
  
  if (type === 'local') {
    return !!(
      newRepo.value.bound_node &&
      newRepo.value.local_config.path.trim()
    )
  }
  
  return false
})

// Clear error for a field
function clearError(field: string) {
  delete formErrors.value[field]
}

// Reset form to initial state
function resetForm() {
  isEditMode.value = false
  editingRepoId.value = null
  formErrors.value = {}
  connectionTestResult.value = {}
  s3BucketList.value = []
  bucketListError.value = ''
  bucketNameAvailable.value = null
  bucketNameMessage.value = ''
  
  // Reset form data
  newRepo.value = {
    name: '',
    repo_type: 's3',
    description: '',
    capacity: 0,
    bound_node: null,
    s3_config: {
      endpoint: '',
      bucket: '',
      region: '',
      prefix: '',
      access_key: '',
      secret_key: '',
      use_tls: true,
      url_style: 'virtual',
      bucket_mode: 'existing'
    },
    nas_config: {
      server: '',
      export_path: '',
      mount_type: 'nfs',
      mount_options: '',
      username: '',
      password: ''
    },
    local_config: {
      path: ''
    }
  }
  
  // Reset local directory browsing
  selectedProxy.value = null
  proxyDirectories.value = []
  currentPath.value = ''
}

// Available Sync Proxies (online + sync role)
const availableSyncProxies = computed(() => {
  return nodes.value.filter(node => 
    node.role === 'sync' && node.status === 'active'
  )
})

// Selected proxy for local filesystem
const selectedProxy = ref<ProxyNode | null>(null)
const proxyDirectories = ref<string[]>([])
const isLoadingDirectories = ref(false)
const currentPath = ref('')

// Fetch Sync Proxy directories
async function fetchProxyDirectories(proxyId: string, path: string = '/') {
  if (!proxyId) return
  isLoadingDirectories.value = true
  try {
    const response = await nodesApi.getDirectories(proxyId, path)
    proxyDirectories.value = response.data.directories || []
    currentPath.value = path
  } catch (error) {
    console.error('Failed to fetch directories:', error)
    proxyDirectories.value = []
  } finally {
    isLoadingDirectories.value = false
  }
}

// Handle proxy selection for local type
function handleProxySelect(proxyId: string) {
  newRepo.value.bound_node = proxyId
  selectedProxy.value = availableSyncProxies.value.find(p => p.id === proxyId) || null
  if (proxyId) {
    fetchProxyDirectories(proxyId, '/')
  } else {
    proxyDirectories.value = []
    currentPath.value = ''
  }
}

// Navigate to subdirectory
function navigateToDirectory(dir: string) {
  const newPath = currentPath.value === '/' ? `/${dir}` : `${currentPath.value}/${dir}`
  fetchProxyDirectories(newRepo.value.bound_node!, newPath)
}

// Navigate up
function navigateUp() {
  if (currentPath.value === '/' || !currentPath.value) return
  const parts = currentPath.value.split('/').filter(Boolean)
  parts.pop()
  const newPath = parts.length === 0 ? '/' : '/' + parts.join('/')
  fetchProxyDirectories(newRepo.value.bound_node!, newPath)
}

// Select current directory as backup path
function selectCurrentPath() {
  newRepo.value.local_config.path = currentPath.value
}

const filteredRepos = computed(() => {
  let result = repositories.value
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(r => 
      r.name.toLowerCase().includes(query) ||
      r.repo_type?.toLowerCase().includes(query)
    )
  }
  if (typeFilter.value) {
    result = result.filter(r => r.repo_type === typeFilter.value)
  }
  return result
})

// Paginated repos for display
const paginatedRepos = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredRepos.value.slice(start, end)
})

// Reset page when filters change
watch([searchQuery, typeFilter], () => {
  currentPage.value = 1
})

// Reset form when repo type changes
watch(() => newRepo.value.repo_type, () => {
  // Reset bound_node when switching away from local
  if (newRepo.value.repo_type !== 'local') {
    newRepo.value.bound_node = null
    selectedProxy.value = null
    proxyDirectories.value = []
    currentPath.value = ''
  }
})

const stats = computed(() => {
  const total = repositories.value.length
  const active = repositories.value.filter(r => r.status === 'active').length
  const initialized = repositories.value.filter(r => r.kopia_initialized).length
  const totalCapacity = repositories.value.reduce((sum, r) => sum + (r.capacity || 0), 0)
  const totalUsed = repositories.value.reduce((sum, r) => sum + (r.used_space || 0), 0)
  return { total, active, initialized, totalCapacity, totalUsed }
})

async function fetchRepositories() {
  isLoading.value = true
  try {
    const response = await repositoriesApi.list()
    repositories.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch repositories:', error)
  } finally {
    isLoading.value = false
  }
}

async function fetchNodes() {
  try {
    const response = await nodesApi.list()
    nodes.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch nodes:', error)
  }
}

// Get app store for toast
const appStore = useAppStore()

async function createRepository() {
  // Validate form first
  if (!validateForm()) {
    appStore.error(t('repository.validation.formInvalid'), t('repository.validation.checkFields'))
    return
  }
  
  try {
    // If creating a new S3 bucket, create it first
    if (newRepo.value.repo_type === 's3' && newRepo.value.s3_config.bucket_mode === 'new') {
      if (!newRepo.value.s3_config.bucket) {
        formErrors.value.bucket = t('repository.s3.bucketNameRequired')
        return
      }
      
      creatingBucket.value = true
      try {
        const createBucketResponse = await repositoriesApi.createBucket({
          endpoint: newRepo.value.s3_config.endpoint,
          bucket_name: newRepo.value.s3_config.bucket,
          region: newRepo.value.s3_config.region,
          access_key: newRepo.value.s3_config.access_key,
          secret_key: newRepo.value.s3_config.secret_key,
          use_tls: newRepo.value.s3_config.use_tls
        })
        
        if (!createBucketResponse.data.success) {
          appStore.error(`${t('repository.s3.createBucketFailed')}: ${createBucketResponse.data.message}`)
          creatingBucket.value = false
          return
        }
        
        appStore.success(t('repository.s3.createBucketSuccess'))
      } catch (bucketError: any) {
        console.error('Failed to create bucket:', bucketError)
        const errorData = bucketError.response?.data || {}
        const errorMsg = errorData.message || errorData.detail || bucketError.message || t('common.unknownError')
        appStore.error(`${t('repository.s3.createBucketFailed')}: ${errorMsg}`)
        creatingBucket.value = false
        return
      }
      creatingBucket.value = false
    }
    
    let payload: any = {
      name: newRepo.value.name,
      repo_type: newRepo.value.repo_type,
      description: newRepo.value.description,
      capacity: newRepo.value.capacity ? newRepo.value.capacity * 1024 * 1024 * 1024 : 0,  // Convert GB to bytes
      bound_node: newRepo.value.bound_node || null
    }

    // Build config based on type
    if (newRepo.value.repo_type === 's3') {
      payload.config = {
        endpoint: newRepo.value.s3_config.endpoint,
        bucket: newRepo.value.s3_config.bucket,
        region: newRepo.value.s3_config.region,
        prefix: newRepo.value.s3_config.prefix,
        use_tls: newRepo.value.s3_config.use_tls,
        url_style: newRepo.value.s3_config.url_style
      }
      payload.credentials = {
        access_key: newRepo.value.s3_config.access_key,
        secret_key: newRepo.value.s3_config.secret_key
      }
    } else if (newRepo.value.repo_type === 'nas') {
      payload.config = {
        server: newRepo.value.nas_config.server,
        export_path: newRepo.value.nas_config.export_path,
        mount_type: newRepo.value.nas_config.mount_type,
        mount_options: newRepo.value.nas_config.mount_options
      }
      if (newRepo.value.nas_config.mount_type === 'cifs') {
        payload.credentials = {
          username: newRepo.value.nas_config.username,
          password: newRepo.value.nas_config.password
        }
      }
    } else if (newRepo.value.repo_type === 'local') {
      payload.config = {
        path: newRepo.value.local_config.path
      }
    }

    if (isEditMode.value && editingRepoId.value) {
      await repositoriesApi.update(editingRepoId.value, payload)
      appStore.success(t('repository.updateSuccess'))
    } else {
      await repositoriesApi.create(payload)
      appStore.success(t('repository.createSuccess'))
    }
    showCreateModal.value = false
    resetForm()
    await fetchRepositories()
  } catch (error: any) {
    console.error('Failed to create repository:', error)
    // Handle backend validation errors
    const errorData = error?.response?.data
    if (errorData) {
      if (errorData.name) {
        formErrors.value.name = errorData.name[0] || errorData.name
      }
      if (errorData.config) {
        // Map config errors to specific fields
        const configError = errorData.config
        if (typeof configError === 'string') {
          appStore.error(t('repository.validation.configError'), configError)
        }
      }
      if (errorData.credentials) {
        appStore.error(t('repository.validation.credentialsError'), errorData.credentials)
      }
      if (errorData.detail || errorData.non_field_errors) {
        appStore.error(t('common.error'), errorData.detail || errorData.non_field_errors)
      }
    } else {
      appStore.error(t('repository.createFailed'))
    }
  }
}

async function deleteRepository(repo: Repository) {
  if (!confirm(t('repository.confirmDelete'))) return
  try {
    await repositoriesApi.delete(repo.id)
    await fetchRepositories()
    appStore.success(t('repository.deleteSuccess'))
  } catch (error) {
    console.error('Failed to delete repository:', error)
    appStore.error(t('repository.deleteFailed'))
  }
}

async function testConnection(repo: Repository) {
  testingConnection.value = repo.id
  connectionTestResult.value[repo.id] = { success: false, message: '' }
  
  try {
    const response = await repositoriesApi.testConnection(repo.id)
    const result = response.data
    
    connectionTestResult.value[repo.id] = {
      success: result.success,
      message: result.message
    }
    
    if (result.success) {
      appStore.success(t('repository.connectionTestSuccess'))
      // Auto-sync usage for S3 repositories (async, don't wait)
      if (repo.repo_type === 's3') {
        syncUsage(repo)
      }
    } else {
      appStore.error(`${t('repository.connectionTestFailed')}: ${result.message}`)
    }
    
    // Refresh repository data
    await fetchRepositories()
  } catch (error: any) {
    console.error('Connection test failed:', error)
    // 处理后端返回的错误信息
    const errorData = error.response?.data || {}
    const errorMsg = errorData.message || errorData.detail || error.message || t('common.unknownError')
    const errorCode = errorData.error_code || ''
    
    connectionTestResult.value[repo.id] = {
      success: false,
      message: errorMsg
    }
    
    // 根据错误代码显示不同的提示
    let displayMsg = errorMsg
    if (errorCode === 'NO_BOUND_NODE') {
      displayMsg = t('repository.errors.noBoundNode')
    } else if (errorCode === 'NODE_NOT_ACTIVE') {
      displayMsg = t('repository.errors.nodeNotActive')
    } else if (errorCode === 'MISSING_CONFIG') {
      displayMsg = t('repository.errors.missingConfig')
    } else if (errorCode === 'ENDPOINT_UNREACHABLE') {
      displayMsg = t('repository.errors.endpointUnreachable')
    } else if (errorCode === 'CONNECTION_TIMEOUT') {
      displayMsg = t('repository.errors.connectionTimeout')
    }
    
    appStore.error(`${t('repository.connectionTestFailed')}: ${displayMsg}`)
  } finally {
    testingConnection.value = null
  }
}

async function initKopia(repo: Repository) {
  if (!confirm(t('repository.confirmInitKopia'))) return
  
  try {
    await repositoriesApi.initKopia(repo.id)
    appStore.success(t('repository.kopiaInitialized'))
    await fetchRepositories()
  } catch (error: any) {
    console.error('Failed to initialize Kopia:', error)
    const errorMsg = error.response?.data?.detail || error.message
    appStore.error(`${t('repository.kopiaInitFailed')}: ${errorMsg}`)
  }
}

// Sync repository usage
async function syncUsage(repo: Repository) {
  try {
    const response = await repositoriesApi.syncUsage(repo.id)
    if (response.data.success) {
      const usage = response.data.usage
      console.log(`[Usage Sync] ${repo.name}: ${usage.object_count} objects, ${usage.total_size_gb} GB`)
      // Refresh repository data to show updated usage
      await fetchRepositories()
    }
  } catch (error: any) {
    console.error('Failed to sync usage:', error)
    // Don't show error to user - this is a background operation
  }
}

// 编辑仓库
function openEditModal(repo: Repository) {
  isEditMode.value = true
  editingRepoId.value = repo.id
  
  // 填充基本信息
  newRepo.value.name = repo.name
  newRepo.value.description = repo.description || ''
  newRepo.value.repo_type = (repo.repo_type === 'nfs' ? 'nas' : repo.repo_type) as 's3' | 'nas' | 'local'
  newRepo.value.bound_node = repo.bound_node ?? null
  // 回填容量配额，将字节转换为 GB
  newRepo.value.capacity = repo.capacity ? Math.round(repo.capacity / (1024 * 1024 * 1024)) : 0
  
  // 根据类型填充配置
  if (repo.repo_type === 's3' && repo.config) {
    newRepo.value.s3_config = {
      endpoint: repo.config.endpoint || '',
      bucket: repo.config.bucket || '',
      region: repo.config.region || '',
      prefix: repo.config.prefix || '',
      access_key: repo.credentials_masked?.access_key || '',
      secret_key: '', // 密钥不回显，需要用户重新输入
      use_tls: repo.config.use_tls !== false,
      url_style: repo.config.url_style || 'virtual',
      bucket_mode: 'existing' as 'existing' | 'new'
    }
  } else if ((repo.repo_type === 'nas' || repo.repo_type === 'nfs') && repo.config) {
    newRepo.value.nas_config = {
      server: repo.config.server || '',
      export_path: repo.config.export_path || '',
      mount_type: repo.config.nas_type || 'nfs',
      mount_options: repo.config.mount_options || '',
      username: repo.credentials_masked?.username || '',
      password: '' // 密码不回显
    }
  } else if (repo.repo_type === 'local' && repo.config) {
    newRepo.value.local_config = {
      path: repo.config.path || ''
    }
  }
  
  showCreateModal.value = true
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getRepoTypeIcon(type: string) {
  const icons: Record<string, any> = {
    s3: CloudIcon,
    local: FolderIcon,
    nas: ServerIcon,
    nfs: ServerIcon,
    azure: CloudIcon,
    gcs: CloudIcon
  }
  return icons[type] || CircleStackIcon
}

function getRepoTypeColor(type: string): string {
  const colors: Record<string, string> = {
    s3: 'bg-orange-100 text-orange-600',
    local: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    nas: 'bg-purple-100 text-purple-600',
    nfs: 'bg-purple-100 text-purple-600',
    azure: 'bg-sky-100 text-sky-600',
    gcs: 'bg-red-100 text-red-600'
  }
  return colors[type] || 'bg-slate-100 dark:bg-slate-700 text-slate-600'
}

function getRepoTypeLabel(type: string | undefined | null): string {
  if (!type) return '-'
  const labels: Record<string, string> = {
    s3: 'S3',
    local: t('repository.types.local'),
    nas: 'NAS',
    nfs: 'NFS',
    azure: 'Azure',
    gcs: 'GCS'
  }
  return labels[type] || type?.toUpperCase() || '-'
}

function getNodeName(nodeId: string | null | undefined): string {
  if (!nodeId) return t('sourceResources.noBoundNode')
  const node = nodes.value.find((n: ProxyNode) => String(n.id) === nodeId)
  return node?.name || nodeId
}

function getNode(nodeId: string | null | undefined): ProxyNode | undefined {
  if (!nodeId) return undefined
  return nodes.value.find((n: ProxyNode) => String(n.id) === nodeId)
}

function getNodeStatus(nodeId: string | null | undefined): string {
  const node = getNode(nodeId)
  return node?.status || 'unknown'
}

onMounted(() => {
  fetchRepositories()
  fetchNodes()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800 dark:text-white">{{ t('repository.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('repository.subtitle') }}</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg hover:from-blue-600 hover:to-cyan-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('repository.form.addRepository') }}
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.stats.total') }}</p>
        <p class="text-xl font-bold text-slate-800 dark:text-white mt-1">{{ stats.total }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.stats.active') }}</p>
        <p class="text-xl font-bold text-emerald-600 mt-1">{{ stats.active }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.stats.totalCapacity') }}</p>
        <p class="text-xl font-bold text-slate-800 dark:text-white mt-1">{{ formatBytes(stats.totalCapacity) }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.stats.usedSpace') }}</p>
        <p class="text-xl font-bold text-blue-600 mt-1">{{ formatBytes(stats.totalUsed) }}</p>
      </div>
    </div>

    <!-- Search & Filters -->
    <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative flex-1 min-w-[200px]">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('common.search')"
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          v-model="typeFilter"
          class="px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option class="bg-white dark:bg-slate-700" value="">{{ t('sourceResources.allTypes') }}</option>
          <option class="bg-white dark:bg-slate-700" value="s3">S3</option>
          <option class="bg-white dark:bg-slate-700" value="local">{{ t('repository.types.local') }}</option>
          <option class="bg-white dark:bg-slate-700" value="nas">NAS/NFS</option>
        </select>
        <button
          @click="fetchRepositories"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
        <!-- View Toggle -->
        <div class="flex items-center border border-slate-200 dark:border-slate-600 rounded-md">
          <button
            @click="viewMode = 'card'"
            :class="[
              'p-2 rounded-md transition-colors',
              viewMode === 'card' ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
            ]"
            :title="t('repository.viewModes.card')"
          >
            <Squares2X2Icon class="w-4 h-4" />
          </button>
          <button
            @click="viewMode = 'list'"
            :class="[
              'p-2 rounded-md transition-colors',
              viewMode === 'list' ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
            ]"
            :title="t('repository.viewModes.list')"
          >
            <Bars3Icon class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Card View -->
    <template v-if="viewMode === 'card'">
      <div v-if="isLoading" class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      </div>

      <div v-else-if="filteredRepos.length === 0" class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-12 text-center">
        <div class="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <CircleStackIcon class="w-8 h-8 text-slate-400" />
        </div>
        <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('repository.empty.title') }}</h3>
        <p class="text-slate-500 dark:text-slate-400">{{ t('repository.empty.description') }}</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="repo in paginatedRepos"
          :key="repo.id"
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md transition-shadow"
        >
        <div class="flex items-start justify-between mb-3">
          <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', getRepoTypeColor(repo.repo_type)]">
            <component :is="getRepoTypeIcon(repo.repo_type)" class="w-5 h-5" />
          </div>
          <div class="flex items-center gap-2">
            <span v-if="repo.kopia_initialized" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
              <CheckCircleIcon class="w-3 h-3" />
              Kopia
            </span>
            <span :class="[
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              repo.status === 'active' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-700 text-slate-600'
            ]">
              {{ repo.status === 'active' ? t('common.active') : t('common.inactive') }}
            </span>
          </div>
        </div>
        
        <h3 class="text-base font-semibold text-slate-800 mb-1">{{ repo.name }}</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 dark:text-slate-400 mb-3">{{ repo.description || getRepoTypeLabel(repo.repo_type) }}</p>
        
        <!-- Connection Info -->
        <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 mb-3 space-y-2">
          <!-- S3 Info -->
          <template v-if="repo.repo_type === 's3'">
            <div class="flex items-center gap-2 text-sm">
              <GlobeAltIcon class="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span class="text-slate-600 truncate" :title="repo.config?.endpoint">{{ repo.config?.endpoint || '-' }}</span>
            </div>
            <div class="flex items-center gap-2 text-sm">
              <FolderIcon class="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span class="text-slate-600 dark:text-slate-300">{{ repo.config?.bucket || '-' }}</span>
              <span v-if="repo.config?.prefix" class="text-slate-400">/{{ repo.config?.prefix }}</span>
            </div>
          </template>
          
          <!-- NAS Info -->
          <template v-else-if="repo.repo_type === 'nas'">
            <div class="flex items-center gap-2 text-sm">
              <ServerIcon class="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span class="text-slate-600 dark:text-slate-300">{{ repo.config?.server || '-' }}</span>
            </div>
            <div class="flex items-center gap-2 text-sm">
              <FolderIcon class="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span class="text-slate-600 dark:text-slate-300">{{ repo.config?.export_path || '-' }}</span>
            </div>
            <div class="flex items-center gap-2 text-sm">
              <span class="text-xs text-slate-400 dark:text-slate-500 uppercase px-1.5 py-0.5 bg-slate-200 rounded">{{ repo.config?.nas_type?.toUpperCase() || 'NFS' }}</span>
            </div>
          </template>
          
          <!-- Local Info -->
          <template v-else-if="repo.repo_type === 'local'">
            <div class="flex items-center gap-2 text-sm">
              <FolderIcon class="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span class="text-slate-600 truncate" :title="repo.config?.path">{{ repo.config?.path || '-' }}</span>
            </div>
          </template>
          
          <!-- Bound Node -->
          <div class="flex items-center gap-2 text-sm pt-2 border-t border-slate-200 dark:border-slate-700">
            <LinkIcon class="w-4 h-4 text-slate-400 flex-shrink-0" />
            <span class="text-slate-600 dark:text-slate-300">{{ getNodeName(repo.bound_node) }}</span>
          </div>
        </div>
        
        <!-- Storage Progress -->
        <div class="mb-4">
          <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>{{ t('repository.stats.usedSpace') }}</span>
            <span>{{ formatBytes(repo.used_space || 0) }} / {{ formatBytes(repo.capacity || 0) }}</span>
          </div>
          <div class="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all"
              :style="{ width: `${repo.capacity ? ((repo.used_space || 0) / repo.capacity) * 100 : 0}%` }"
            />
          </div>
        </div>
        
        <div class="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-700 dark:border-slate-700 dark:border-slate-700">
          <span class="text-xs text-slate-400 dark:text-slate-500 uppercase">{{ getRepoTypeLabel(repo.repo_type) }}</span>
          <div class="flex items-center gap-1">
            <button
              v-if="!repo.kopia_initialized && repo.bound_node"
              @click="initKopia(repo)"
              class="p-1.5 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
              :title="t('repository.initKopia')"
            >
              <PlayIcon class="w-4 h-4" />
            </button>
            <button
              @click="testConnection(repo)"
              :disabled="testingConnection === repo.id"
              :class="[
                'p-1.5 rounded-lg transition-colors',
                testingConnection === repo.id 
                  ? 'text-slate-300 cursor-wait' 
                  : connectionTestResult[repo.id]?.success 
                    ? 'text-emerald-500 hover:text-emerald-700 hover:bg-emerald-50' 
                    : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
              ]"
              :title="testingConnection === repo.id ? t('repository.testing') : t('repository.testConnection')"
            >
              <SignalIcon v-if="testingConnection === repo.id" class="w-4 h-4 animate-pulse" />
              <CheckCircleIcon v-else-if="connectionTestResult[repo.id]?.success" class="w-4 h-4" />
              <LinkIcon v-else class="w-4 h-4" />
            </button>
            <button
              @click="openEditModal(repo)"
              class="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              :title="t('common.edit')"
            >
              <PencilIcon class="w-4 h-4" />
            </button>
            <button
              @click="selectedRepo = repo; showDetailModal = true"
              class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:bg-slate-700 rounded-lg transition-colors"
              :title="t('common.details')"
            >
              <Cog6ToothIcon class="w-4 h-4" />
            </button>
            <button
              @click="deleteRepository(repo)"
              class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              :title="t('common.delete')"
            >
              <TrashIcon class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      </div>
    </template>

    <!-- List View -->
    <template v-else>
      <div v-if="isLoading" class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      </div>

      <div v-else-if="filteredRepos.length === 0" class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-12 text-center">
        <div class="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <CircleStackIcon class="w-8 h-8 text-slate-400" />
        </div>
        <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('repository.empty.title') }}</h3>
        <p class="text-slate-500 dark:text-slate-400">{{ t('repository.empty.description') }}</p>
      </div>

      <div v-else class="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-[1000px] w-full divide-y divide-slate-200">
            <thead class="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                <th class="sticky left-0 bg-slate-50 dark:bg-slate-700 px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider z-10">{{ t('repository.list.name') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('repository.list.type') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('repository.list.status') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('repository.list.connection') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('repository.list.boundNode') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('repository.list.capacity') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ t('repository.list.kopia') }}</th>
                <th class="sticky right-0 bg-slate-50 dark:bg-slate-700 px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider z-10">{{ t('repository.list.actions') }}</th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-slate-800 divide-y divide-slate-200">
              <tr
                v-for="repo in paginatedRepos"
                :key="repo.id"
                class="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <!-- Name -->
                <td class="sticky left-0 bg-white dark:bg-slate-800 px-4 py-3 whitespace-nowrap z-10">
                  <div class="flex items-center gap-3">
                    <div :class="['w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', getRepoTypeColor(repo.repo_type)]">
                      <component :is="getRepoTypeIcon(repo.repo_type)" class="w-4 h-4 text-white" />
                    </div>
                    <button
                      @click="selectedRepo = repo; showDetailModal = true"
                      class="font-medium text-slate-800 hover:text-indigo-600 cursor-pointer transition-colors text-left"
                    >
                      {{ repo.name }}
                    </button>
                  </div>
                </td>
                <!-- Type -->
                <td class="px-4 py-3 whitespace-nowrap">
                  <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                    repo.repo_type === 's3' ? 'bg-orange-100 text-orange-700' :
                    repo.repo_type === 'nas' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400' :
                    'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                  ]">
                    {{ getRepoTypeLabel(repo.repo_type) }}
                  </span>
                </td>
                <!-- Status -->
                <td class="px-4 py-3 whitespace-nowrap">
                  <span :class="[
                    'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                    repo.status === 'active' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-700 text-slate-600'
                  ]">
                    {{ repo.status === 'active' ? t('common.active') : t('common.inactive') }}
                  </span>
                </td>
                <!-- Connection Info -->
                <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 dark:text-slate-300 max-w-[200px]">
                  <template v-if="repo.repo_type === 's3'">
                    <div class="truncate" :title="repo.config?.endpoint">{{ repo.config?.bucket || '-' }}</div>
                  </template>
                  <template v-else-if="repo.repo_type === 'nas'">
                    <div class="truncate" :title="repo.config?.server">{{ repo.config?.server || '-' }}</div>
                  </template>
                  <template v-else>
                    <div class="truncate" :title="repo.config?.path">{{ repo.config?.path || '-' }}</div>
                  </template>
                </td>
                <!-- Bound Node -->
                <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300 dark:text-slate-300 dark:text-slate-300">
                  {{ getNodeName(repo.bound_node) }}
                </td>
                <!-- Capacity -->
                <td class="px-4 py-3 whitespace-nowrap">
                  <div v-if="repo.capacity" class="flex items-center gap-2">
                    <div class="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all"
                        :style="{ width: `${Math.min(((repo.used_space || 0) / repo.capacity) * 100, 100)}%` }"
                      />
                    </div>
                    <span class="text-xs text-slate-500 dark:text-slate-400">{{ formatBytes(repo.used_space || 0) }}/{{ formatBytes(repo.capacity) }}</span>
                  </div>
                  <span v-else class="text-slate-400 text-sm">-</span>
                </td>
                <!-- Kopia -->
                <td class="px-4 py-3 whitespace-nowrap">
                  <span v-if="repo.kopia_initialized" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                    <CheckCircleIcon class="w-3 h-3" />
                    {{ t('repository.initialized') }}
                  </span>
                  <span v-else class="text-slate-400 text-xs">-</span>
                </td>
                <!-- Actions -->
                <td class="sticky right-0 bg-white dark:bg-slate-800 px-4 py-3 whitespace-nowrap text-right z-10">
                  <div class="flex items-center justify-end gap-1">
                    <button
                      v-if="!repo.kopia_initialized && repo.bound_node"
                      @click="initKopia(repo)"
                      class="p-1.5 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
                      :title="t('repository.initKopia')"
                    >
                      <PlayIcon class="w-4 h-4" />
                    </button>
                    <button
                      @click="testConnection(repo)"
                      :disabled="testingConnection === repo.id"
                      :class="[
                        'p-1.5 rounded-lg transition-colors',
                        testingConnection === repo.id 
                          ? 'text-slate-300 cursor-wait' 
                          : connectionTestResult[repo.id]?.success 
                            ? 'text-emerald-500 hover:text-emerald-700 hover:bg-emerald-50' 
                            : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
                      ]"
                      :title="testingConnection === repo.id ? t('repository.testing') : t('repository.testConnection')"
                    >
                      <SignalIcon v-if="testingConnection === repo.id" class="w-4 h-4 animate-pulse" />
                      <CheckCircleIcon v-else-if="connectionTestResult[repo.id]?.success" class="w-4 h-4" />
                      <LinkIcon v-else class="w-4 h-4" />
                    </button>
                    <button
                      @click="openEditModal(repo)"
                      class="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      :title="t('common.edit')"
                    >
                      <PencilIcon class="w-4 h-4" />
                    </button>
                    <button
                      @click="selectedRepo = repo; showDetailModal = true"
                      class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:bg-slate-700 rounded-lg transition-colors"
                      :title="t('common.details')"
                    >
                      <InformationCircleIcon class="w-4 h-4" />
                    </button>
                    <button
                      @click="deleteRepository(repo)"
                      class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      :title="t('common.delete')"
                    >
                      <TrashIcon class="w-4 h-4" />
                    </button>
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
          :total-items="filteredRepos.length"
        />
      </div>
    </template>

    <!-- Create Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showCreateModal = false" />
        <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
          <!-- Fixed Header -->
          <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700 dark:border-slate-700 flex items-center justify-between flex-shrink-0">
            <h2 class="text-lg font-semibold text-slate-800 dark:text-white dark:text-white dark:text-white">
              {{ isEditMode ? t('repository.form.editRepository') : t('repository.form.addRepository') }}
            </h2>
            <button @click="showCreateModal = false; resetForm()" class="p-1 hover:bg-slate-100 dark:bg-slate-700 rounded-lg">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <!-- Fixed Repository Type Selection -->
          <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/50 flex-shrink-0">
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">{{ t('repository.form.repositoryType') }}</label>
            <div class="grid grid-cols-3 gap-3">
              <button
                v-for="type in repoTypes"
                :key="type.value"
                @click="!isEditMode && (newRepo.repo_type = type.value as any)"
                :disabled="isEditMode"
                :class="[
                  'flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all',
                  isEditMode ? 'cursor-not-allowed opacity-60' : '',
                  newRepo.repo_type === type.value 
                    ? 'border-blue-500 dark:border-blue-400 bg-white dark:bg-slate-700 shadow-sm' 
                    : 'border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 hover:border-slate-300 dark:hover:border-slate-500'
                ]"
              >
                <div :class="[
                  'w-9 h-9 rounded-lg flex items-center justify-center dark:bg-opacity-50',
                  type.color === 'orange' ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400' :
                  type.color === 'purple' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400' :
                  'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                ]">
                  <component :is="type.icon" class="w-5 h-5" />
                </div>
                <span class="text-xs font-medium text-slate-700 dark:text-slate-200">{{ type.label }}</span>
              </button>
            </div>
          </div>

          <!-- Scrollable Content Area -->
          <div class="flex-1 overflow-y-auto p-6 space-y-4">

            <!-- Basic Info -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('common.name') }} *</label>
                <input 
                  v-model="newRepo.name" 
                  type="text" 
                  :placeholder="t('repository.form.namePlaceholder')" 
                  :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2', 
                    formErrors.name ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                  @input="clearError('name')"
                />
                <p v-if="formErrors.name" class="mt-1 text-xs text-red-500">{{ formErrors.name }}</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('common.description') }}</label>
                <input v-model="newRepo.description" type="text" :placeholder="t('repository.form.descPlaceholder')" class="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">
                  {{ t('repository.form.capacity') }}
                  <span class="text-xs text-slate-400 dark:text-slate-500 font-normal ml-1">({{ t('repository.form.capacityUnit') }})</span>
                </label>
                <input 
                  v-model.number="newRepo.capacity" 
                  type="number" 
                  min="0" 
                  :placeholder="t('repository.form.capacityPlaceholder')"
                  class="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500" 
                />
                <p class="mt-1 text-xs text-slate-400 dark:text-slate-500">{{ t('repository.form.capacityHint') }}</p>
              </div>
            </div>

            <!-- S3 Configuration -->
            <div v-if="newRepo.repo_type === 's3'" class="space-y-4 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
              <div class="flex items-start gap-2 text-sm text-orange-700 dark:text-orange-400 bg-orange-50 dark:bg-slate-700/50 rounded-lg p-3 border-l-4 border-orange-400">
                <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                  <p class="font-medium">{{ t('repository.s3.hint') }}</p>
                  <p class="mt-1 text-xs text-orange-600">{{ t('repository.s3.hintDetail') }}</p>
                </div>
              </div>
              
              <!-- Credentials Section (must be filled first) -->
              <div class="p-3 bg-white dark:bg-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-600">
                <h4 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">{{ t('repository.s3.credentials') }}</h4>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.s3.endpoint') }} *</label>
                    <input 
                      v-model="newRepo.s3_config.endpoint" 
                      type="text" 
                      placeholder="https://s3.amazonaws.com" 
                      :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                        formErrors.endpoint ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                      @input="clearError('endpoint')"
                    />
                    <p class="text-xs text-slate-500 mt-1">{{ t('repository.s3.endpointHint') }}</p>
                    <p v-if="formErrors.endpoint" class="mt-1 text-xs text-red-500">{{ formErrors.endpoint }}</p>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.s3.region') }}</label>
                    <input v-model="newRepo.s3_config.region" type="text" placeholder="us-east-1" class="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                  
                  <!-- URL Style Selection -->
                  <div>
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.s3.urlStyle') }}</label>
                    <select 
                      v-model="newRepo.s3_config.url_style"
                      class="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option class="bg-white dark:bg-slate-700" value="virtual">{{ t('repository.s3.urlStyleVirtual') }}</option>
                      <option class="bg-white dark:bg-slate-700" value="path">{{ t('repository.s3.urlStylePath') }}</option>
                    </select>
                    <p class="text-xs text-slate-500 mt-1">{{ t('repository.s3.urlStyleHint') }}</p>
                  </div>
                  
                  <!-- Use TLS Toggle -->
                  <div class="flex items-center justify-between py-2">
                    <div>
                      <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-200">{{ t('repository.s3.useTLS') }}</label>
                      <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.s3.useTLSHint') }}</p>
                    </div>
                    <button 
                      type="button"
                      @click="newRepo.s3_config.use_tls = !newRepo.s3_config.use_tls"
                      :class="[
                        'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                        newRepo.s3_config.use_tls ? 'bg-blue-600' : 'bg-slate-200'
                      ]"
                      role="switch"
                      :aria-checked="newRepo.s3_config.use_tls"
                    >
                      <span 
                        :class="[
                          'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                          newRepo.s3_config.use_tls ? 'translate-x-5' : 'translate-x-0'
                        ]"
                      ></span>
                    </button>
                  </div>
                  
                  <div>
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.s3.accessKey') }} *</label>
                    <input 
                      v-model="newRepo.s3_config.access_key" 
                      type="text" 
                      placeholder="AKIAIOSFODNN7EXAMPLE" 
                      :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                        formErrors.access_key ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                      @input="clearError('access_key')"
                    />
                    <p v-if="formErrors.access_key" class="mt-1 text-xs text-red-500">{{ formErrors.access_key }}</p>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">
                      {{ t('repository.s3.secretKey') }}
                      <span v-if="!isEditMode">*</span>
                    </label>
                    <input 
                      v-model="newRepo.s3_config.secret_key" 
                      type="password" 
                      :placeholder="isEditMode ? '••••••••••••••••' : '••••••••••••••••'" 
                      :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                        formErrors.secret_key ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                      @input="clearError('secret_key')"
                    />
                    <p v-if="isEditMode && !formErrors.secret_key" class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {{ t('repository.s3.secretKeyEditHint') }}
                    </p>
                    <p v-if="formErrors.secret_key" class="mt-1 text-xs text-red-500">{{ formErrors.secret_key }}</p>
                  </div>
                </div>
              </div>
              
              <!-- Bucket Selection Mode -->
              <div class="p-3 bg-white dark:bg-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-600">
                <h4 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">{{ t('repository.s3.bucketSelection') }}</h4>
                
                <!-- Bucket Mode Selection -->
                <div class="mb-4">
                  <div class="grid grid-cols-2 gap-3">
                    <button
                      @click="newRepo.s3_config.bucket_mode = 'existing'"
                      :class="[
                        'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
                        newRepo.s3_config.bucket_mode === 'existing' 
                          ? 'border-orange-500 dark:border-orange-500 bg-orange-50 dark:bg-slate-700 text-orange-700 dark:text-orange-400' 
                          : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-500'
                      ]"
                    >
                      <FolderIcon class="w-4 h-4" />
                      {{ t('repository.s3.existingBucket') }}
                    </button>
                    <button
                      @click="newRepo.s3_config.bucket_mode = 'new'"
                      :class="[
                        'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
                        newRepo.s3_config.bucket_mode === 'new' 
                          ? 'border-orange-500 dark:border-orange-500 bg-orange-50 dark:bg-slate-700 text-orange-700 dark:text-orange-400' 
                          : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-500'
                      ]"
                    >
                      <PlusCircleIcon class="w-4 h-4" />
                      {{ t('repository.s3.newBucket') }}
                    </button>
                  </div>
                </div>
                
                <!-- Existing Bucket Selection -->
                <div v-if="newRepo.s3_config.bucket_mode === 'existing'">
                  <!-- Warning for existing bucket -->
                  <div class="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 dark:bg-slate-700/50 rounded-lg p-3 mb-4 border border-amber-300 dark:border-amber-700 border-l-4">
                    <ExclamationTriangleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div>
                      <p class="font-medium">{{ t('repository.s3.existingBucketWarning') }}</p>
                      <p class="mt-1 text-xs text-amber-600 dark:text-amber-400">{{ t('repository.s3.existingBucketWarningDetail') }}</p>
                    </div>
                  </div>
                  
                  <!-- Fetch bucket list button -->
                  <button
                    @click="fetchBucketList"
                    :disabled="!newRepo.s3_config.endpoint || !newRepo.s3_config.access_key || !newRepo.s3_config.secret_key"
                    :class="[
                      'w-full px-4 py-2 rounded-lg text-sm font-medium transition-all mb-3',
                      (!newRepo.s3_config.endpoint || !newRepo.s3_config.access_key || !newRepo.s3_config.secret_key)
                        ? 'bg-slate-100 dark:bg-slate-700 text-slate-400 cursor-not-allowed'
                        : 'bg-orange-500 text-white hover:bg-orange-600'
                    ]"
                  >
                    <span v-if="isLoadingBuckets" class="flex items-center justify-center gap-2">
                      <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {{ t('repository.s3.loadingBuckets') }}
                    </span>
                    <span v-else class="flex items-center justify-center gap-2">
                      <ArrowPathIcon class="w-4 h-4" />
                      {{ t('repository.s3.fetchBucketList') }}
                    </span>
                  </button>
                  
                  <!-- Bucket list error -->
                  <p v-if="bucketListError" class="mb-3 text-xs text-red-500">{{ bucketListError }}</p>
                  
                  <!-- Bucket select -->
                  <div v-if="s3BucketList.length > 0">
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.s3.selectBucket') }} *</label>
                    <select
                      v-model="newRepo.s3_config.bucket"
                      :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                        formErrors.bucket ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                      @change="clearError('bucket')"
                    >
                      <option class="bg-white dark:bg-slate-700" value="">{{ t('repository.s3.selectBucketPlaceholder') }}</option>
                      <option class="bg-white dark:bg-slate-700" v-for="bucket in s3BucketList" :key="bucket.name" :value="bucket.name">
                        {{ bucket.name }}
                      </option>
                    </select>
                    <p v-if="formErrors.bucket" class="mt-1 text-xs text-red-500">{{ formErrors.bucket }}</p>
                  </div>
                </div>
                
                <!-- New Bucket Creation -->
                <div v-if="newRepo.s3_config.bucket_mode === 'new'">
                  <!-- Bucket name rules info -->
                  <div class="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 mb-4 border border-slate-200 dark:border-slate-700">
                    <InformationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5 text-slate-400" />
                    <div class="text-xs space-y-1">
                      <p class="font-medium text-slate-700 dark:text-slate-200">{{ t('repository.s3.bucketNameRules') }}:</p>
                      <ul class="list-disc list-inside text-slate-600 space-y-0.5">
                        <li>{{ t('repository.s3.bucketNameRule1') }}</li>
                        <li>{{ t('repository.s3.bucketNameRule2') }}</li>
                        <li>{{ t('repository.s3.bucketNameRule3') }}</li>
                        <li>{{ t('repository.s3.bucketNameRule4') }}</li>
                        <li>{{ t('repository.s3.bucketNameRule5') }}</li>
                      </ul>
                    </div>
                  </div>
                  
                  <div>
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.s3.bucketName') }} *</label>
                    <div class="relative">
                      <input 
                        v-model="newRepo.s3_config.bucket" 
                        type="text" 
                        placeholder="my-backup-bucket" 
                        :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 pr-24',
                          formErrors.bucket ? 'border-red-300 focus:ring-red-500' : 
                          bucketNameAvailable === true ? 'border-green-300 focus:ring-green-500' :
                          bucketNameAvailable === false ? 'border-red-300 focus:ring-red-500' :
                          'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                        @input="clearError('bucket')"
                      />
                      <button
                        @click="checkBucketNameAvailability"
                        :disabled="!newRepo.s3_config.bucket || checkingBucketName"
                        :class="[
                          'absolute right-1 top-1 bottom-1 px-3 rounded text-xs font-medium transition-all',
                          (!newRepo.s3_config.bucket || checkingBucketName)
                            ? 'bg-slate-100 dark:bg-slate-700 text-slate-400 cursor-not-allowed'
                            : 'bg-blue-500 text-white hover:bg-blue-600'
                        ]"
                      >
                        {{ checkingBucketName ? t('repository.s3.checking') : t('repository.s3.check') }}
                      </button>
                    </div>
                    
                    <!-- Bucket name validation message -->
                    <p v-if="bucketNameMessage" :class="[
                      'mt-1 text-xs flex items-center gap-1',
                      bucketNameAvailable === true ? 'text-green-600' : 'text-red-500'
                    ]">
                      <CheckCircleIcon v-if="bucketNameAvailable === true" class="w-3 h-3" />
                      <XCircleIcon v-else class="w-3 h-3" />
                      {{ bucketNameMessage }}
                    </p>
                    <p v-if="formErrors.bucket" class="mt-1 text-xs text-red-500">{{ formErrors.bucket }}</p>
                  </div>
                </div>
              </div>
              
              <!-- Prefix -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.s3.prefix') }}</label>
                <input v-model="newRepo.s3_config.prefix" type="text" placeholder="backups/hyperfilelens" class="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.s3.prefixHint') }}</p>
              </div>
            </div>

            <!-- NAS Configuration -->
            <div v-if="newRepo.repo_type === 'nas'" class="space-y-4 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
              <div class="flex items-start gap-2 text-sm text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-slate-700/50 rounded-lg p-3 border-l-4 border-purple-400">
                <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                  <p class="font-medium">{{ t('repository.nas.hint') }}</p>
                  <p class="mt-1 text-xs text-purple-600">{{ t('repository.nas.hintDetail') }}</p>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.nas.mountType') }}</label>
                <div class="grid grid-cols-2 gap-3">
                  <button
                    @click="newRepo.nas_config.mount_type = 'nfs'"
                    :class="[
                      'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
                      newRepo.nas_config.mount_type === 'nfs' 
                        ? 'border-purple-500 dark:border-purple-500 bg-purple-50 dark:bg-slate-700 text-purple-700 dark:text-purple-400' 
                        : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-500'
                    ]"
                  >
                    NFS
                  </button>
                  <button
                    @click="newRepo.nas_config.mount_type = 'cifs'"
                    :class="[
                      'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
                      newRepo.nas_config.mount_type === 'cifs' 
                        ? 'border-purple-500 dark:border-purple-500 bg-purple-50 dark:bg-slate-700 text-purple-700 dark:text-purple-400' 
                        : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-500'
                    ]"
                  >
                    CIFS/SMB
                  </button>
                </div>
              </div>
              
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.nas.server') }} *</label>
                  <input 
                    v-model="newRepo.nas_config.server" 
                    type="text" 
                    placeholder="192.168.1.100 或 nas.example.com" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                      formErrors.server ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                    @input="clearError('server')"
                  />
                  <p v-if="formErrors.server" class="mt-1 text-xs text-red-500">{{ formErrors.server }}</p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.nas.exportPath') }} *</label>
                  <input 
                    v-model="newRepo.nas_config.export_path" 
                    type="text" 
                    :placeholder="newRepo.nas_config.mount_type === 'nfs' ? '/export/backup' : '/share/backup'" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                      formErrors.export_path ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                    @input="clearError('export_path')"
                  />
                  <p v-if="formErrors.export_path" class="mt-1 text-xs text-red-500">{{ formErrors.export_path }}</p>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.nas.mountOptions') }}</label>
                <input v-model="newRepo.nas_config.mount_options" type="text" :placeholder="newRepo.nas_config.mount_type === 'nfs' ? 'rw,hard,intr' : 'vers=3.0,iocharset=utf8'" class="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.nas.mountOptionsHint') }}</p>
              </div>

              <!-- CIFS credentials -->
              <div v-if="newRepo.nas_config.mount_type === 'cifs'" class="grid grid-cols-2 gap-4 p-3 bg-white dark:bg-slate-700 rounded-lg">
                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.nas.username') }} *</label>
                  <input 
                    v-model="newRepo.nas_config.username" 
                    type="text" 
                    placeholder="username" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                      formErrors.username ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                    @input="clearError('username')"
                  />
                  <p v-if="formErrors.username" class="mt-1 text-xs text-red-500">{{ formErrors.username }}</p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">
                    {{ t('repository.nas.password') }}
                    <span v-if="!isEditMode">*</span>
                  </label>
                  <input 
                    v-model="newRepo.nas_config.password" 
                    type="password" 
                    placeholder="••••••••" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                      formErrors.password ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                    @input="clearError('password')"
                  />
                  <p v-if="isEditMode && !formErrors.password" class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {{ t('repository.s3.secretKeyEditHint') }}
                  </p>
                  <p v-if="formErrors.password" class="mt-1 text-xs text-red-500">{{ formErrors.password }}</p>
                </div>
              </div>

              <!-- Bound Sync Proxy for NAS -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.boundSyncProxy') }} *</label>
                <select 
                  v-model="newRepo.bound_node" 
                  :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                    formErrors.bound_node ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                  @change="clearError('bound_node')"
                >
                  <option class="bg-white dark:bg-slate-700" value="">{{ t('repository.selectSyncProxy') }}</option>
                  <option class="bg-white dark:bg-slate-700" v-for="proxy in availableSyncProxies" :key="proxy.id" :value="proxy.id">
                    {{ proxy.name }} ({{ proxy.hostname || proxy.id }})
                  </option>
                </select>
                <p v-if="formErrors.bound_node" class="mt-1 text-xs text-red-500">{{ formErrors.bound_node }}</p>
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.boundSyncProxyHint') }}</p>
              </div>
            </div>

            <!-- Local Filesystem Configuration -->
            <div v-if="newRepo.repo_type === 'local'" class="space-y-4 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
              <div class="flex items-start gap-2 text-sm text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-slate-700/50 rounded-lg p-3 border-l-4 border-blue-400">
                <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                  <p class="font-medium">{{ t('repository.local.hint') }}</p>
                  <p class="mt-1 text-xs text-blue-600">{{ t('repository.local.hintDetail') }}</p>
                </div>
              </div>

              <!-- Select Sync Proxy -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('repository.boundSyncProxy') }} *</label>
                <select 
                  :value="newRepo.bound_node || ''" 
                  @change="handleProxySelect(($event.target as HTMLSelectElement).value)"
                  :class="['w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2',
                    formErrors.bound_node ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500']"
                >
                  <option class="bg-white dark:bg-slate-700" value="">{{ t('repository.selectSyncProxy') }}</option>
                  <option class="bg-white dark:bg-slate-700" v-for="proxy in availableSyncProxies" :key="proxy.id" :value="proxy.id">
                    {{ proxy.name }} ({{ proxy.hostname || proxy.id }})
                  </option>
                </select>
                <p v-if="formErrors.bound_node" class="mt-1 text-xs text-red-500">{{ formErrors.bound_node }}</p>
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.boundSyncProxyHint') }}</p>
              </div>

              <!-- Directory Browser -->
              <div v-if="newRepo.bound_node" class="bg-white dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-700">
                <div class="px-3 py-2 border-b border-slate-100 dark:border-slate-700 dark:border-slate-700 flex items-center justify-between">
                  <div class="flex items-center gap-2 text-sm">
                    <FolderIcon class="w-4 h-4 text-slate-400" />
                    <span class="text-slate-600 dark:text-slate-300">{{ t('repository.local.selectDirectory') }}</span>
                  </div>
                  <button
                    v-if="currentPath !== '/'"
                    @click="navigateUp"
                    class="text-xs text-blue-600 hover:text-blue-700"
                  >
                    {{ t('repository.local.goUp') }}
                  </button>
                </div>
                
                <!-- Current Path -->
                <div class="px-3 py-2 bg-slate-50 dark:bg-slate-700 border-b border-slate-100 dark:border-slate-700 dark:border-slate-700 dark:border-slate-700 dark:border-slate-700">
                  <code class="text-sm text-slate-700 dark:text-slate-200">{{ currentPath || '/' }}</code>
                </div>

                <!-- Loading -->
                <div v-if="isLoadingDirectories" class="flex items-center justify-center py-8">
                  <div class="w-6 h-6 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                </div>

                <!-- Directory List -->
                <div v-else class="max-h-48 overflow-y-auto">
                  <div v-if="proxyDirectories.length === 0" class="py-6 text-center text-sm text-slate-500 dark:text-slate-400 dark:text-slate-400">
                    {{ t('repository.local.noSubdirectories') }}
                  </div>
                  <button
                    v-for="dir in proxyDirectories"
                    :key="dir"
                    @click="navigateToDirectory(dir)"
                    class="w-full px-3 py-2 flex items-center gap-2 hover:bg-slate-50 dark:hover:bg-slate-700 text-left text-sm"
                  >
                    <FolderIcon class="w-4 h-4 text-yellow-500" />
                    <span class="text-slate-700 dark:text-slate-200">{{ dir }}</span>
                    <ChevronRightIcon class="w-4 h-4 text-slate-400 ml-auto" />
                  </button>
                </div>

                <!-- Select Current Path -->
                <div class="px-3 py-2 border-t border-slate-100 dark:border-slate-700 dark:border-slate-700 dark:border-slate-700">
                  <button
                    @click="selectCurrentPath"
                    class="w-full py-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    {{ t('repository.local.useCurrentPath') }}
                  </button>
                </div>
              </div>
              
              <!-- Selected Path Display -->
              <div v-if="newRepo.local_config.path" class="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/30 rounded-lg">
                <CheckCircleIcon class="w-5 h-5 text-green-600" />
                <span class="text-sm text-green-700 dark:text-green-400">{{ t('repository.local.selectedPath') }}: <code class="bg-green-100 dark:bg-green-800/50 px-1 rounded">{{ newRepo.local_config.path }}</code></span>
              </div>
              
              <!-- Path Error -->
              <p v-if="formErrors.path" class="text-xs text-red-500">{{ formErrors.path }}</p>

              <!-- No Sync Proxy Available Warning -->
              <div v-if="availableSyncProxies.length === 0" class="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/30 rounded-lg border border-amber-200 dark:border-amber-800">
                <ExclamationCircleIcon class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                <div>
                  <p class="text-sm font-medium text-amber-700">{{ t('repository.local.noSyncProxy') }}</p>
                  <p class="text-xs text-amber-600 dark:text-amber-400 mt-1">{{ t('repository.local.noSyncProxyHint') }}</p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Fixed Footer -->
          <div class="px-6 py-4 border-t border-slate-100 dark:border-slate-700 flex justify-end gap-3 flex-shrink-0 bg-white dark:bg-slate-800">
            <button @click="showCreateModal = false; resetForm()" class="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
              {{ t('common.cancel') }}
            </button>
            <button 
              @click="createRepository" 
              :disabled="!isFormValid"
              :class="[
                'px-4 py-2 text-sm rounded-lg transition-colors',
                isFormValid 
                  ? 'text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600' 
                  : 'text-slate-500 dark:text-slate-400 bg-slate-200 dark:bg-slate-700 cursor-not-allowed'
              ]"
            >
              {{ isEditMode ? t('common.save') : t('common.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Detail Modal -->
    <Teleport to="body">
      <div v-if="showDetailModal && selectedRepo" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showDetailModal = false" />
        <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
          <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700 dark:border-slate-700 flex items-center justify-between sticky top-0 bg-white z-10">
            <h2 class="text-lg font-semibold text-slate-800 dark:text-white dark:text-white dark:text-white">{{ selectedRepo.name }}</h2>
            <button @click="showDetailModal = false" class="p-1 hover:bg-slate-100 dark:bg-slate-700 rounded-lg">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6 space-y-4">
            <!-- Type & Status -->
            <div class="flex items-center gap-3">
              <div :class="['w-12 h-12 rounded-lg flex items-center justify-center', getRepoTypeColor(selectedRepo.repo_type)]">
                <component :is="getRepoTypeIcon(selectedRepo.repo_type)" class="w-6 h-6" />
              </div>
              <div class="flex-1">
                <p class="font-medium text-slate-800 dark:text-white">{{ getRepoTypeLabel(selectedRepo.repo_type) }}</p>
                <p class="text-sm text-slate-500 dark:text-slate-400 dark:text-slate-400">{{ selectedRepo.status === 'active' ? t('common.active') : t('common.inactive') }}</p>
              </div>
              <span v-if="selectedRepo.kopia_initialized" class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700">
                <CheckCircleIcon class="w-4 h-4" />
                Kopia {{ t('repository.initialized') }}
              </span>
            </div>
            
            <!-- Description -->
            <div v-if="selectedRepo.description" class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('common.description') }}</p>
              <p class="text-sm text-slate-700 dark:text-slate-200">{{ selectedRepo.description }}</p>
            </div>
            
            <!-- Storage Stats -->
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.stats.totalCapacity') }}</p>
                <p class="font-semibold text-slate-800 text-lg">{{ formatBytes(selectedRepo.capacity || 0) }}</p>
              </div>
              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.stats.usedSpace') }}</p>
                <p class="font-semibold text-slate-800 text-lg">{{ formatBytes(selectedRepo.used_space || 0) }}</p>
              </div>
            </div>
            
            <!-- S3 Configuration -->
            <div v-if="selectedRepo.repo_type === 's3'" class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 space-y-3">
              <h4 class="font-medium text-slate-700 flex items-center gap-2">
                <GlobeAltIcon class="w-5 h-5" />
                {{ t('repository.types.s3') }} {{ t('repository.configInfo') }}
              </h4>
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.s3.endpoint') }}</p>
                  <p class="text-slate-700 font-mono">{{ selectedRepo.config?.endpoint || '-' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.s3.bucket') }}</p>
                  <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.config?.bucket || '-' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.s3.region') }}</p>
                  <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.config?.region || '-' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.s3.prefix') }}</p>
                  <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.config?.prefix || '-' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.s3.accessKey') }}</p>
                  <p class="text-slate-700 font-mono">{{ selectedRepo.credentials_masked?.access_key || '-' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.s3.useTLS') }}</p>
                  <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.config?.use_tls !== false ? t('common.yes') : t('common.no') }}</p>
                </div>
              </div>
            </div>
            
            <!-- NAS Configuration -->
            <div v-if="selectedRepo.repo_type === 'nas'" class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 space-y-3">
              <h4 class="font-medium text-slate-700 flex items-center gap-2">
                <ServerIcon class="w-5 h-5" />
                {{ t('repository.types.nas') }} {{ t('repository.configInfo') }}
              </h4>
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.nas.server') }}</p>
                  <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.config?.server || '-' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.nas.exportPath') }}</p>
                  <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.config?.export_path || '-' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.nas.nasType') }}</p>
                  <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.config?.nas_type?.toUpperCase() || 'NFS' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.nas.mountOptions') }}</p>
                  <p class="text-slate-700 font-mono text-xs">{{ selectedRepo.config?.mount_options || '-' }}</p>
                </div>
                <div v-if="selectedRepo.config?.nas_type === 'cifs'">
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.nas.username') }}</p>
                  <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.config?.username || '-' }}</p>
                </div>
              </div>
            </div>
            
            <!-- Local Configuration -->
            <div v-if="selectedRepo.repo_type === 'local'" class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 space-y-3">
              <h4 class="font-medium text-slate-700 flex items-center gap-2">
                <FolderIcon class="w-5 h-5" />
                {{ t('repository.types.local') }} {{ t('repository.configInfo') }}
              </h4>
              <div class="text-sm">
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('repository.local.path') }}</p>
                <p class="text-slate-700 font-mono">{{ selectedRepo.config?.path || '-' }}</p>
              </div>
            </div>
            
            <!-- Bound Node -->
            <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('sourceResources.boundNode') }}</p>
              <div class="flex items-center gap-2">
                <div :class="['w-2 h-2 rounded-full', getNodeStatus(selectedRepo.bound_node) === 'active' ? 'bg-emerald-500' : 'bg-slate-300']" />
                <span class="text-sm text-slate-700 dark:text-slate-200">{{ getNodeName(selectedRepo.bound_node) }}</span>
                <span v-if="getNode(selectedRepo.bound_node)?.role" class="text-xs text-slate-400 dark:text-slate-500">({{ getNode(selectedRepo.bound_node)?.role }})</span>
              </div>
            </div>
            
            <!-- Timestamps -->
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('common.createdAt') }}</p>
                <p class="text-slate-700 dark:text-slate-200">{{ new Date(selectedRepo.created_at).toLocaleString() }}</p>
              </div>
              <div>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('common.updatedAt') }}</p>
                <p class="text-slate-700 dark:text-slate-200">{{ selectedRepo.updated_at ? new Date(selectedRepo.updated_at).toLocaleString() : '-' }}</p>
              </div>
            </div>
          </div>
          <div class="px-6 py-4 border-t border-slate-100 dark:border-slate-700 dark:border-slate-700 flex justify-end sticky bottom-0 bg-white dark:bg-slate-800">
            <button @click="showDetailModal = false" class="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 dark:text-slate-300 border border-slate-200 rounded-lg hover:bg-slate-50 dark:bg-slate-700/50">
              {{ t('common.cancel') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
