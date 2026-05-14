package message

// TaskPriority represents the priority level of a task
type TaskPriority string

const (
	PriorityLow    TaskPriority = "low"
	PriorityNormal TaskPriority = "normal"
	PriorityHigh   TaskPriority = "high"
	PriorityUrgent TaskPriority = "urgent"
)

// TaskStatus represents the status of a task
type TaskStatus string

const (
	TaskStatusPending   TaskStatus = "pending"
	TaskStatusAccepted  TaskStatus = "accepted"
	TaskStatusRunning   TaskStatus = "running"
	TaskStatusCompleted TaskStatus = "completed"
	TaskStatusFailed    TaskStatus = "failed"
	TaskStatusCancelled TaskStatus = "cancelled"
)

// Message type constants for WebSocket communication
const (
	// ==================== Control Messages ====================
	// Backend -> Proxy
	MsgTypeConnectionEstablished = "connection_established"
	MsgTypeRegisterAck           = "register_ack"
	MsgTypeHeartbeatAck          = "heartbeat_ack"
	MsgTypePing                  = "ping"
	MsgTypePong                  = "pong"
	MsgTypeError                 = "error"

	// Proxy -> Backend
	MsgTypeRegister  = "register"
	MsgTypeHeartbeat = "heartbeat"

	// ==================== Task Commands (Backend -> Proxy) ====================
	MsgTypeBackup            = "backup"
	MsgTypeRestore           = "restore"
	MsgTypeMount             = "mount"
	MsgTypeUnmount           = "unmount"
	MsgTypeListSnapshots     = "list_snapshots"
	MsgTypeCancel            = "cancel"
	MsgTypeTestStorage       = "test_storage"
	MsgTypeInitRepository    = "init_repository"
	MsgTypeListDirectory     = "list_directory"
	MsgTypeListSnapshotFiles = "list_snapshot_files"

	// ==================== Task Status (Proxy -> Backend) ====================
	// Unified task status messages
	MsgTypeTaskStart    = "task_start"
	MsgTypeTaskProgress = "task_progress"
	MsgTypeTaskComplete = "task_complete"

	// Legacy task status messages (for backwards compatibility)
	MsgTypeTaskUpdate = "task_update"
	MsgTypeTaskResult = "task_result"

	// Legacy result messages (for backwards compatibility)
	MsgTypeBackupResult         = "backup_result"
	MsgTypeRestoreResult        = "restore_result"
	MsgTypeMountResult          = "mount_result"
	MsgTypeSnapshotListResult   = "snapshot_list_result"
	MsgTypeTestConnectionResult = "test_connection_result"
	MsgTypeTestStorageResult    = "test_storage_result"
	MsgTypeInitRepositoryResult = "init_repository_result"
	MsgTypeListDirectoryResult  = "list_directory_result"

	// ==================== System Messages (Proxy -> Backend) ====================
	MsgTypeLog    = "log"
	MsgTypeStatus = "status"
	MsgTypeAlert  = "alert"
)

// Task type constants
const (
	TypeBackup  = "backup"
	TypeRestore = "restore"
	TypeMount   = "mount"
	TypeList    = "list_snapshots"
)

// Task status constants
const (
	StatusRunning   = "running"
	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCancelled = "cancelled"
)
