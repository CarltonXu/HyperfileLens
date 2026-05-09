package task

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/hyperfilelens/proxy/config"
	"github.com/hyperfilelens/proxy/kopia"
	"github.com/hyperfilelens/proxy/logger"
	"github.com/hyperfilelens/proxy/message"
	"github.com/hyperfilelens/proxy/mount"
	"github.com/hyperfilelens/proxy/ws"
)

// Type constants for task types (using message package constants)
const (
	TypeBackup  = message.TypeBackup
	TypeRestore = message.TypeRestore
	TypeMount   = message.TypeMount
	TypeList    = message.TypeList
)

// Status constants (using message package constants)
const (
	StatusRunning   = message.StatusRunning
	StatusCompleted = message.StatusCompleted
	StatusFailed    = message.StatusFailed
	StatusCancelled = message.StatusCancelled
)

// Task represents a task
type Task struct {
	ID          string                                    `json:"id"`
	Type        string                                    `json:"type"`
	Priority    message.TaskPriority                      `json:"priority"`
	Status      message.TaskStatus                        `json:"status"`
	Payload     map[string]interface{}                    `json:"payload"`
	Progress    float64                                   `json:"progress"`
	Message     string                                    `json:"message"`
	Error       string                                    `json:"error,omitempty"`
	CreatedAt   time.Time                                 `json:"created_at"`
	StartedAt   time.Time                                 `json:"started_at,omitempty"`
	CompletedAt time.Time                                 `json:"completed_at,omitempty"`
	TimeoutAt   time.Time                                 `json:"timeout_at,omitempty"`
	RetryCount  int                                       `json:"retry_count"`
	MaxRetries  int                                       `json:"max_retries"`
	DependsOn   []string                                  `json:"depends_on"`
	BlockedBy   []string                                  `json:"blocked_by"`
	OnComplete  func(result map[string]interface{}) error `json:"-"`
	OnFailure   func(err error) error                     `json:"-"`
	mu          sync.RWMutex
}

// Status represents task status
type Status struct {
	TaskID    string    `json:"task_id"`
	Type      string    `json:"type"`
	Status    string    `json:"status"`
	Progress  int       `json:"progress"`
	Message   string    `json:"message"`
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time,omitempty"`
}

// Dispatcher handles task dispatching
type Dispatcher struct {
	config   *config.Config
	kopia    *kopia.Client
	mountMgr *mount.Manager
	wsClient *ws.Client

	tasks   map[string]*Status
	tasksMu sync.RWMutex
}

// NewDispatcher creates a new task dispatcher
func NewDispatcher(cfg *config.Config, kopiaClient *kopia.Client, mountMgr *mount.Manager, wsClient *ws.Client) *Dispatcher {
	return &Dispatcher{
		config:   cfg,
		kopia:    kopiaClient,
		mountMgr: mountMgr,
		wsClient: wsClient,
		tasks:    make(map[string]*Status),
	}
}

// SetWSClient sets the WebSocket client
func (d *Dispatcher) SetWSClient(client *ws.Client) {
	d.wsClient = client
}

// HandleMessage handles incoming WebSocket message
func (d *Dispatcher) HandleMessage(msg ws.Message) {
	logger.Info("Received task", map[string]interface{}{
		"type": msg.Type,
		"id":   msg.ID,
	})

	// DEBUG: Add more detailed logging for important message types
	if msg.Type == message.MsgTypeTestStorage {
		logger.Debug("Test storage task received", map[string]interface{}{
			"message_id": msg.ID,
			"payload":    msg.Payload,
		})
	}
	if msg.Type == message.MsgTypeInitRepository {
		logger.Debug("Init repository task received", map[string]interface{}{
			"message_id": msg.ID,
			"payload":    msg.Payload,
		})
	}
	if msg.Type == message.MsgTypeBackup {
		if msg.Payload != nil {
			logger.Debug("Backup task received", map[string]interface{}{
				"message_id":  msg.ID,
				"task_id":     getString(msg.Payload, "task_id", msg.ID),
				"source_path": getString(msg.Payload, "source_path", ""),
			})
		}
	}
	if msg.Type == message.MsgTypeRestore {
		if msg.Payload != nil {
			logger.Debug("Restore task received", map[string]interface{}{
				"message_id":  msg.ID,
				"task_id":     getString(msg.Payload, "task_id", msg.ID),
				"snapshot_id": getString(msg.Payload, "snapshot_id", ""),
				"target_path": getString(msg.Payload, "target_path", ""),
			})
		}
	}
	if msg.Type == message.MsgTypeMount {
		if msg.Payload != nil {
			logger.Debug("Mount task received", map[string]interface{}{
				"message_id": msg.ID,
				"mount_type": getString(msg.Payload, "type", ""),
			})
		}
	}

	switch msg.Type {
	// Task commands
	case message.MsgTypeBackup:
		go d.executeBackup(msg)
	case message.MsgTypeRestore:
		go d.executeRestore(msg)
	case message.MsgTypeMount:
		go d.executeMount(msg)
	case message.MsgTypeListSnapshots:
		go d.listSnapshots(msg)
	case message.MsgTypeCancel:
		go d.cancelTask(msg)
	case message.MsgTypeTestStorage:
		logger.Info("Executing test_storage task in goroutine", nil)
		go d.executeTestStorage(msg)
	case message.MsgTypeInitRepository:
		go d.executeInitRepository(msg)

	// Control messages
	case message.MsgTypePing:
		d.wsClient.Send(ws.Message{Type: message.MsgTypePong, ID: msg.ID})
	case message.MsgTypeConnectionEstablished:
		// Server confirmed WebSocket connection
		logger.Info("WebSocket connection confirmed by server", nil)
	case message.MsgTypeRegisterAck:
		// Server acknowledged proxy registration
		logger.Info("Proxy registration acknowledged by server", nil)
	case message.MsgTypeHeartbeatAck:
		// Server acknowledged heartbeat, check for pending tasks
		pendingTasks := getSlice(msg.Payload, "pending_tasks")
		if len(pendingTasks) > 0 {
			logger.Info("Received pending tasks from server", map[string]interface{}{
				"count": len(pendingTasks),
			})
			// Process pending tasks
			for _, task := range pendingTasks {
				if taskMap, ok := task.(map[string]interface{}); ok {
					taskType := getString(taskMap, "task_type", "")
					taskID := getString(taskMap, "task_id", "")
					logger.Info("Processing pending task", map[string]interface{}{
						"task_type": taskType,
						"task_id":   taskID,
					})

					// Convert task map to ws.Message and execute
					// The pending task data is in the task map itself
					taskMsg := ws.Message{
						Type:    taskType,
						ID:      taskID,
						Payload: taskMap,
					}

					// Execute the task in a goroutine to avoid blocking
					go d.HandleMessage(taskMsg)
				}
			}
		}
	case message.MsgTypeError:
		// Handle error message from server
		errorMsg := getString(msg.Payload, "message", "Unknown error")
		logger.Warn("Server error", map[string]interface{}{
			"message": errorMsg,
		})

	default:
		logger.Warn("Unknown task type", map[string]interface{}{
			"type": msg.Type,
		})
	}
}

// executeBackup executes a backup task
func (d *Dispatcher) executeBackup(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	sourcePath := getString(msg.Payload, "source_path", "")
	repoConfig := getMap(msg.Payload, "repository")
	password := getString(msg.Payload, "password", "")

	logger.Debug("Backup task start", map[string]interface{}{
		"task_id":     taskID,
		"source_path": sourcePath,
		"repo_config": repoConfig,
		"password":    "[REDACTED]",
	})

	if sourcePath == "" {
		logger.Error("source_path is required", nil)
		d.sendError(msg.ID, taskID, "source_path is required")
		return
	}

	// Initialize task status
	status := &Status{
		TaskID:    taskID,
		Type:      TypeBackup,
		Status:    StatusRunning,
		Progress:  0,
		Message:   "Starting backup",
		StartTime: time.Now(),
	}
	d.setTask(status)

	// Notify start
	d.sendTaskStart(msg.ID, taskID, TypeBackup)

	// Connect to repository if config provided
	if len(repoConfig) > 0 {
		logger.Debug("Connecting to repository...", nil)
		if err := d.kopia.ConnectRepo(repoConfig, password); err != nil {
			logger.Error("Failed to connect to repository", map[string]interface{}{
				"error": err.Error(),
			})
			d.failTask(taskID, err.Error())
			d.sendError(msg.ID, taskID, err.Error())
			return
		}
		logger.Debug("Repository connected successfully", nil)
	}

	// Execute backup
	logger.Debug("Starting Kopia backup...", nil)
	result, err := d.kopia.Backup(taskID, sourcePath, password)

	if err != nil {
		logger.Error("Backup failed", map[string]interface{}{
			"error": err.Error(),
		})
		d.failTask(taskID, err.Error())
		d.sendTaskFailed(msg.ID, taskID, err.Error())
	} else {
		logger.Debug("Backup completed successfully", map[string]interface{}{
			"result": result,
		})
		d.completeTask(taskID, "Backup completed")
		d.sendTaskCompleted(msg.ID, taskID, result)
	}

	logger.Debug("Backup task end", nil)
}

// executeRestore executes a restore task
func (d *Dispatcher) executeRestore(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	targetPath := getString(msg.Payload, "target_path", "")
	repoConfig := getMap(msg.Payload, "repository")
	password := getString(msg.Payload, "password", "")
	overwrite := getBool(msg.Payload, "overwrite", false)

	logger.Debug("Restore task start", map[string]interface{}{
		"task_id":     taskID,
		"snapshot_id": snapshotID,
		"target_path": targetPath,
		"repo_config": repoConfig,
		"password":    "[REDACTED]",
		"overwrite":   overwrite,
	})

	if snapshotID == "" || targetPath == "" {
		logger.Error("snapshot_id and target_path are required", nil)
		d.sendError(msg.ID, taskID, "snapshot_id and target_path are required")
		return
	}

	status := &Status{
		TaskID:    taskID,
		Type:      TypeRestore,
		Status:    StatusRunning,
		Progress:  0,
		Message:   "Starting restore",
		StartTime: time.Now(),
	}
	d.setTask(status)

	d.sendTaskStart(msg.ID, taskID, TypeRestore)

	// Connect to repository
	if len(repoConfig) > 0 {
		logger.Debug("Connecting to repository...", nil)
		if err := d.kopia.ConnectRepo(repoConfig, password); err != nil {
			logger.Error("Failed to connect to repository", map[string]interface{}{
				"error": err.Error(),
			})
			d.failTask(taskID, err.Error())
			d.sendError(msg.ID, taskID, err.Error())
			return
		}
		logger.Debug("Repository connected successfully", nil)
	}

	// Execute restore
	logger.Debug("Starting Kopia restore...", nil)
	result, err := d.kopia.Restore(taskID, snapshotID, targetPath, password, overwrite)

	if err != nil {
		logger.Error("Restore failed", map[string]interface{}{
			"error": err.Error(),
		})
		d.failTask(taskID, err.Error())
		d.sendTaskFailed(msg.ID, taskID, err.Error())
	} else {
		logger.Debug("Restore completed successfully", map[string]interface{}{
			"result": result,
		})
		d.completeTask(taskID, "Restore completed")
		d.sendTaskCompleted(msg.ID, taskID, result)
	}

	logger.Debug("Restore task end", nil)
}

// executeMount executes a mount task (Sync Proxy only)
func (d *Dispatcher) executeMount(msg ws.Message) {
	if !d.config.IsSyncProxy() {
		d.sendError(msg.ID, "", "mount only available for Sync Proxy")
		return
	}

	mountType := getString(msg.Payload, "type", "nfs")

	logger.Debug("Mount task start", map[string]interface{}{
		"mount_type": mountType,
		"payload":    msg.Payload,
	})

	var err error
	switch mountType {
	case "nfs":
		server := getString(msg.Payload, "server", "")
		path := getString(msg.Payload, "path", "")
		target := getString(msg.Payload, "target", "")
		logger.Debug("Mounting NFS share", map[string]interface{}{
			"server": server,
			"path":   path,
			"target": target,
		})
		err = d.mountMgr.MountNFS(server, path, target)
	case "smb":
		server := getString(msg.Payload, "server", "")
		share := getString(msg.Payload, "share", "")
		target := getString(msg.Payload, "target", "")
		username := getString(msg.Payload, "username", "")
		password := getString(msg.Payload, "password", "")
		logger.Debug("Mounting SMB share", map[string]interface{}{
			"server":   server,
			"share":    share,
			"target":   target,
			"username": username,
			"password": "[REDACTED]",
		})
		err = d.mountMgr.MountSMB(server, share, target, username, password)
	default:
		err = fmt.Errorf("unsupported mount type: %s", mountType)
	}

	if err != nil {
		logger.Error("Mount failed", map[string]interface{}{
			"error": err.Error(),
		})
		d.sendError(msg.ID, "", err.Error())
		logger.Debug("Mount task failed", nil)
		return
	}

	logger.Info("Mount completed successfully", nil)
	d.wsClient.Send(ws.Message{
		Type: "mount_completed",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"type":   mountType,
			"status": "mounted",
		},
	})

	logger.Debug("Mount task end", nil)
}

// listSnapshots lists available snapshots
func (d *Dispatcher) listSnapshots(msg ws.Message) {
	password := getString(msg.Payload, "password", "")

	logger.Debug("Snapshot list start", nil)
	logger.Debug("Listing Kopia snapshots...", nil)

	snapshots, err := d.kopia.ListSnapshots(password)
	if err != nil {
		logger.Error("Failed to list snapshots", map[string]interface{}{
			"error": err.Error(),
		})
		d.sendError(msg.ID, "", err.Error())
		logger.Debug("Snapshot list failed", nil)
		return
	}

	// snapshots is a string containing JSON output
	outputStr := ""
	if str, ok := snapshots.(string); ok {
		outputStr = str
	}

	logger.Debug("Found snapshots", map[string]interface{}{
		"output_length": len(outputStr),
	})

	d.wsClient.Send(ws.Message{
		Type: "snapshot_list",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"snapshots": snapshots,
		},
	})

	logger.Debug("Snapshot list end", nil)
}

// cancelTask cancels a running task
func (d *Dispatcher) cancelTask(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", "")

	logger.Debug("Task cancel start", map[string]interface{}{
		"task_id": taskID,
	})

	d.tasksMu.Lock()
	defer d.tasksMu.Unlock()

	if status, exists := d.tasks[taskID]; exists {
		logger.Debug("Cancelling task...", nil)
		status.Status = StatusCancelled
		status.Message = "Task cancelled"
		status.EndTime = time.Now()

		// Cancel Kopia operation
		d.kopia.Cancel(taskID)

		logger.Debug("Task cancelled successfully", nil)
		d.sendTaskCancelled(msg.ID, taskID, "Task cancelled by user")
	} else {
		logger.Warn("Task not found", map[string]interface{}{
			"task_id": taskID,
		})
		d.sendError(msg.ID, taskID, "Task not found")
	}

	logger.Debug("Task cancel end", nil)
}

// Helper methods

func (d *Dispatcher) setTask(status *Status) {
	d.tasksMu.Lock()
	d.tasks[status.TaskID] = status
	d.tasksMu.Unlock()
}

func (d *Dispatcher) failTask(taskID, errMsg string) {
	d.tasksMu.Lock()
	if status, exists := d.tasks[taskID]; exists {
		status.Status = StatusFailed
		status.Message = errMsg
		status.EndTime = time.Now()
	}
	d.tasksMu.Unlock()
}

func (d *Dispatcher) completeTask(taskID, message string) {
	d.tasksMu.Lock()
	if status, exists := d.tasks[taskID]; exists {
		status.Status = StatusCompleted
		status.Message = message
		status.Progress = 100
		status.EndTime = time.Now()
	}
	d.tasksMu.Unlock()
}

func (d *Dispatcher) sendTaskStart(msgID, taskID, taskType string) {
	logger.Debug("Sending task start", map[string]interface{}{
		"message_id": msgID,
		"task_id":    taskID,
		"task_type":  taskType,
	})
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskStart,
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": taskType,
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) sendTaskProgress(msgID, taskID, taskType string, progress int, msg string) {
	logger.Debug("Sending task progress", map[string]interface{}{
		"task_id":   taskID,
		"task_type": taskType,
		"progress":  progress,
		"message":   msg,
	})
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskProgress,
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": taskType,
			"progress":  progress,
			"message":   msg,
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) sendTaskProgressWithDetails(msgID string, progress *Progress) {
	logger.Debug("Sending task progress with details", map[string]interface{}{
		"task_id":         progress.TaskID,
		"task_type":       progress.TaskType,
		"status":          progress.Status,
		"progress":        progress.Progress,
		"current_file":    progress.CurrentFile,
		"processed_files": progress.ProcessedFiles,
		"total_files":     progress.TotalFiles,
		"processed_bytes": progress.ProcessedBytes,
		"total_bytes":     progress.TotalBytes,
		"speed_mbps":      progress.SpeedMBps,
		"eta":             progress.ETA,
		"message":         progress.Message,
	})
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskProgress,
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id":         progress.TaskID,
			"task_type":       progress.TaskType,
			"status":          progress.Status,
			"progress":        progress.Progress,
			"message":         progress.Message,
			"current_file":    progress.CurrentFile,
			"total_files":     progress.TotalFiles,
			"processed_files": progress.ProcessedFiles,
			"total_bytes":     progress.TotalBytes,
			"processed_bytes": progress.ProcessedBytes,
			"speed_mbps":      progress.SpeedMBps,
			"eta":             progress.ETA,
			"timestamp":       time.Now(),
		},
	})
}

func (d *Dispatcher) sendTaskCompleted(msgID, taskID string, result interface{}) {
	logger.Debug("Sending task completed", map[string]interface{}{
		"message_id": msgID,
		"task_id":    taskID,
		"success":    true,
		"result":     result,
	})
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskComplete,
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"success":   true,
			"result":    result,
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) sendTaskFailed(msgID, taskID, errMsg string) {
	logger.Debug("Sending task failed", map[string]interface{}{
		"message_id": msgID,
		"task_id":    taskID,
		"success":    false,
		"error":      errMsg,
	})
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskComplete,
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"success":   false,
			"error":     errMsg,
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) sendError(msgID, taskID, errMsg string) {
	logger.Debug("Sending error", map[string]interface{}{
		"message_id": msgID,
		"task_id":    taskID,
		"error":      errMsg,
	})
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeError,
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"error":     errMsg,
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) sendTaskCancelled(msgID, taskID, reason string) {
	logger.Debug("Sending task cancelled", map[string]interface{}{
		"message_id": msgID,
		"task_id":    taskID,
		"reason":     reason,
	})
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskComplete,
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"success":   false,
			"cancelled": true,
			"error":     reason,
			"timestamp": time.Now(),
		},
	})
}

// Helper functions

func getString(m map[string]interface{}, key, def string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return def
}

func getBool(m map[string]interface{}, key string, def bool) bool {
	if v, ok := m[key]; ok {
		if b, ok := v.(bool); ok {
			return b
		}
	}
	return def
}

func getMap(m map[string]interface{}, key string) map[string]interface{} {
	if v, ok := m[key]; ok {
		if mm, ok := v.(map[string]interface{}); ok {
			return mm
		}
	}
	return nil
}

func getSlice(m map[string]interface{}, key string) []interface{} {
	if v, ok := m[key]; ok {
		if s, ok := v.([]interface{}); ok {
			return s
		}
	}
	return nil
}

// executeTestStorage executes a storage connectivity test (Sync Proxy only)
func (d *Dispatcher) executeTestStorage(msg ws.Message) {
	if !d.config.IsSyncProxy() {
		d.sendError(msg.ID, "", "test_storage only available for Sync Proxy")
		return
	}

	// Use payload for unified message format
	if msg.Payload == nil {
		d.sendStorageTestResult(msg.ID, "", nil, "payload is empty")
		return
	}

	taskID := getString(msg.Payload, "task_id", msg.ID)
	storageType := getString(msg.Payload, "storage_type", "nas")
	testWrite := getBool(msg.Payload, "test_write", true)
	repositoryID := getString(msg.Payload, "repository_id", "")

	logger.Debug("Storage test start", map[string]interface{}{
		"task_id":       taskID,
		"storage_type":  storageType,
		"repository_id": repositoryID,
		"test_write":    testWrite,
		"payload":       msg.Payload,
	})

	logger.Info("Starting storage test", map[string]interface{}{
		"storage_type": storageType,
		"task_id":      taskID,
	})

	// Send task start notification
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskStart,
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": "test_storage",
			"timestamp": time.Now(),
		},
	})

	result := map[string]interface{}{
		"storage_type":  storageType,
		"repository_id": repositoryID,
		"success":       false,
	}

	switch storageType {
	case "nas", "nfs":
		// Test NAS/NFS connectivity
		server := getString(msg.Payload, "server", "")
		path := getString(msg.Payload, "path", "")
		mountType := getString(msg.Payload, "mount_type", "nfs") // nfs or smb
		mountPath := getString(msg.Payload, "mount_path", "")

		logger.Debug("NAS/NFS test parameters", map[string]interface{}{
			"server":     server,
			"path":       path,
			"mount_type": mountType,
			"mount_path": mountPath,
		})

		if server == "" {
			logger.Error("Server is required but empty", nil)
			d.sendStorageTestResult(msg.ID, taskID, result, "server is required")
			return
		}

		// Test connectivity
		logger.Debug("Starting connectivity test...", nil)
		var connResult *mount.ConnectivityResult
		if mountType == "smb" {
			logger.Debug("Testing SMB connectivity", map[string]interface{}{
				"server": server,
			})
			connResult = mount.TestSMBConnectivity(server)
		} else {
			logger.Debug("Testing NFS connectivity", map[string]interface{}{
				"server": server,
			})
			connResult = mount.TestNFSConnectivity(server)
		}

		logger.Debug("Connectivity result", map[string]interface{}{
			"reachable":     connResult.Reachable,
			"response_time": connResult.ResponseTime,
			"error":         connResult.Error,
		})

		result["connectivity"] = map[string]interface{}{
			"reachable":     connResult.Reachable,
			"response_time": connResult.ResponseTime,
			"error":         connResult.Error,
		}

		if !connResult.Reachable {
			logger.Error("Connectivity test failed", map[string]interface{}{
				"error": connResult.Error,
			})
			d.sendStorageTestResult(msg.ID, taskID, result, fmt.Sprintf("connectivity test failed: %s", connResult.Error))
			return
		}

		// Test write if mount_path provided or create temporary mount point
		if testWrite {
			// If mount_path is empty, create a temporary mount point
			if mountPath == "" {
				logger.Info("Creating temporary mount point for write test", nil)
				tempDir := filepath.Join(os.TempDir(), "hyperfilelens-nfs-test-"+taskID[:8])
				if err := os.MkdirAll(tempDir, 0755); err != nil {
					logger.Error("Failed to create temporary mount directory", map[string]interface{}{
						"error": err.Error(),
					})
					result["write_test"] = map[string]interface{}{
						"writable":    false,
						"write_speed": 0,
						"read_speed":  0,
						"error":       fmt.Sprintf("failed to create temp mount dir: %v", err),
					}
					result["success"] = true
					d.sendStorageTestResult(msg.ID, taskID, result, "")
					return
				}
				mountPath = tempDir
				logger.Debug("Created temporary mount point", map[string]interface{}{
					"mount_path": mountPath,
				})

				// Mount NFS to temporary directory
				logger.Info("Mounting NFS for write test", map[string]interface{}{
					"server": server,
					"path":   path,
					"target": mountPath,
				})

				// Get user-provided mount options
				mountOptions := getString(msg.Payload, "mount_options", "")

				var mountErr error
				if mountType == "smb" {
					username := getString(msg.Payload, "username", "")
					password := getString(msg.Payload, "password", "")
					share := path // For SMB, path is actually the share name
					mountErr = d.mountMgr.MountSMB(server, share, mountPath, username, password, mountOptions)
				} else {
					mountErr = d.mountMgr.MountNFS(server, path, mountPath, mountOptions)
				}

				if mountErr != nil {
					logger.Error("Failed to mount for write test", map[string]interface{}{
						"error": mountErr.Error(),
					})
					result["write_test"] = map[string]interface{}{
						"writable":    false,
						"write_speed": 0,
						"read_speed":  0,
						"error":       fmt.Sprintf("mount failed: %v", mountErr),
					}
					result["success"] = true
					d.sendStorageTestResult(msg.ID, taskID, result, "")
					return
				}

				logger.Debug("NFS mounted successfully for write test", nil)

				// Ensure cleanup after test
				defer func() {
					logger.Debug("Cleaning up temporary mount", map[string]interface{}{
						"mount_path": mountPath,
					})
					// Unmount
					d.mountMgr.Unmount(mountPath)
					// Remove temp directory
					os.RemoveAll(mountPath)
					logger.Debug("Temporary mount cleaned up", nil)
				}()
			}

			logger.Debug("Starting write test", map[string]interface{}{
				"mount_path": mountPath,
			})

			// Check if mount path exists (should exist now)
			if _, err := os.Stat(mountPath); os.IsNotExist(err) {
				logger.Error("Mount path does not exist", map[string]interface{}{
					"mount_path": mountPath,
				})
				result["write_test"] = map[string]interface{}{
					"writable":    false,
					"write_speed": 0,
					"read_speed":  0,
					"error":       fmt.Sprintf("mount path does not exist: %s", mountPath),
				}
				result["success"] = true
				d.sendStorageTestResult(msg.ID, taskID, result, "")
				return
			}

			writeResult := mount.TestWriteSimple(mountPath)

			logger.Debug("Write test result", map[string]interface{}{
				"writable":    writeResult.Writable,
				"write_speed": writeResult.WriteSpeed,
				"read_speed":  writeResult.ReadSpeed,
				"error":       writeResult.Error,
			})

			result["write_test"] = map[string]interface{}{
				"writable":    writeResult.Writable,
				"write_speed": writeResult.WriteSpeed,
				"read_speed":  writeResult.ReadSpeed,
				"error":       writeResult.Error,
			}

			// Get space info
			logger.Debug("Getting space info", map[string]interface{}{
				"mount_path": mountPath,
			})
			total, used, free, err := mount.GetMountSpaceInfo(mountPath)
			if err == nil {
				logger.Debug("Space info", map[string]interface{}{
					"total_gb": float64(total) / 1024 / 1024 / 1024,
					"used_gb":  float64(used) / 1024 / 1024 / 1024,
					"free_gb":  float64(free) / 1024 / 1024 / 1024,
				})
				result["space_info"] = map[string]interface{}{
					"total_bytes": total,
					"used_bytes":  used,
					"free_bytes":  free,
				}
			} else {
				logger.Error("Failed to get space info", map[string]interface{}{
					"error": err.Error(),
				})
			}
		}

		result["success"] = true
		logger.Info("Storage test completed successfully", map[string]interface{}{
			"task_id": taskID,
		})
		d.sendStorageTestResult(msg.ID, taskID, result, "")

	case "s3":
		// Test S3 connectivity (using kopia's built-in S3 support)
		// S3 connectivity test is handled by the backend directly via boto3
		// This is for cases where Sync Proxy needs to test S3 access
		result["success"] = true
		result["message"] = "S3 connectivity test should be performed by control plane"
		d.sendStorageTestResult(msg.ID, taskID, result, "")

	case "local":
		// Test local filesystem
		path := getString(msg.Payload, "path", "")
		if path == "" {
			d.sendStorageTestResult(msg.ID, taskID, result, "path is required for local storage test")
			return
		}

		// Check if path exists and is accessible
		if _, err := os.Stat(path); err != nil {
			d.sendStorageTestResult(msg.ID, taskID, result, fmt.Sprintf("path not accessible: %v", err))
			return
		}

		// Test write
		if testWrite {
			writeResult := mount.TestWriteSimple(path)
			result["write_test"] = map[string]interface{}{
				"writable":    writeResult.Writable,
				"write_speed": writeResult.WriteSpeed,
				"read_speed":  writeResult.ReadSpeed,
				"error":       writeResult.Error,
			}
		}

		// Get space info
		total, used, free, err := mount.GetMountSpaceInfo(path)
		if err == nil {
			result["space_info"] = map[string]interface{}{
				"total_bytes": total,
				"used_bytes":  used,
				"free_bytes":  free,
			}
		}

		result["success"] = true
		d.sendStorageTestResult(msg.ID, taskID, result, "")

	default:
		d.sendStorageTestResult(msg.ID, taskID, result, fmt.Sprintf("unsupported storage type: %s", storageType))
	}
}

// sendStorageTestResult sends storage test result to server
func (d *Dispatcher) sendStorageTestResult(msgID, taskID string, result map[string]interface{}, errMsg string) {
	logger.Debug("Sending storage test result", map[string]interface{}{
		"message_id": msgID,
		"task_id":    taskID,
		"success":    errMsg == "",
		"error":      errMsg,
		"result":     result,
	})

	if errMsg != "" {
		result["error"] = errMsg
		d.wsClient.Send(ws.Message{
			Type: message.MsgTypeTestStorageResult,
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":   taskID,
				"success":   false,
				"error":     errMsg,
				"result":    result,
				"timestamp": time.Now(),
			},
		})
	} else {
		d.wsClient.Send(ws.Message{
			Type: message.MsgTypeTestStorageResult,
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":   taskID,
				"success":   true,
				"result":    result,
				"timestamp": time.Now(),
			},
		})
	}
	logger.Debug("Storage test result sent", nil)
}

// executeInitRepository initializes a new Kopia repository (Sync Proxy only)
func (d *Dispatcher) executeInitRepository(msg ws.Message) {
	if !d.config.IsSyncProxy() {
		d.sendError(msg.ID, "", "init_repository only available for Sync Proxy")
		return
	}

	taskID := getString(msg.Payload, "task_id", msg.ID)
	repositoryID := getString(msg.Payload, "repository_id", "")
	repoConfig := getMap(msg.Payload, "repository")
	password := getString(msg.Payload, "password", "")

	logger.Debug("Init repository task start", map[string]interface{}{
		"task_id":       taskID,
		"repository_id": repositoryID,
		"repo_config":   repoConfig,
		"password":      "[REDACTED]",
	})

	logger.Info("Starting repository initialization", map[string]interface{}{
		"repository_id": repositoryID,
		"task_id":       taskID,
	})

	// Send task start notification
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskStart,
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":       taskID,
			"task_type":     "init_repository",
			"repository_id": repositoryID,
			"timestamp":     time.Now(),
		},
	})

	if len(repoConfig) == 0 {
		logger.Error("Repository config is required but empty", nil)
		d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, "repository config is required")
		return
	}

	// Execute repository creation
	logger.Debug("Creating Kopia repository...", nil)
	result, err := d.kopia.CreateRepo(repoConfig, password)
	if err != nil {
		logger.Error("Failed to create repository", map[string]interface{}{
			"error": err.Error(),
		})
		d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, err.Error())
		return
	}

	logger.Debug("Repository created successfully", map[string]interface{}{
		"repository_id": result.RepositoryID,
		"path":          result.Path,
		"created_at":    result.CreatedAt,
	})

	d.sendRepoInitResult(msg.ID, taskID, repositoryID, result, "")

	logger.Debug("Init repository task end", nil)
}

// sendRepoInitResult sends repository initialization result to server
func (d *Dispatcher) sendRepoInitResult(msgID, taskID, repositoryID string, result *kopia.CreateRepoResult, errMsg string) {
	fields := map[string]interface{}{
		"message_id":    msgID,
		"task_id":       taskID,
		"repository_id": repositoryID,
		"success":       errMsg == "",
	}
	if errMsg != "" {
		fields["error"] = errMsg
	}
	if result != nil {
		fields["result_path"] = result.Path
		fields["result_created_at"] = result.CreatedAt
	}
	logger.Debug("Sending repository init result", fields)

	if errMsg != "" {
		d.wsClient.Send(ws.Message{
			Type: message.MsgTypeInitRepositoryResult,
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":       taskID,
				"repository_id": repositoryID,
				"success":       false,
				"error":         errMsg,
				"timestamp":     time.Now(),
			},
		})
	} else {
		d.wsClient.Send(ws.Message{
			Type: message.MsgTypeInitRepositoryResult,
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":       taskID,
				"success":       true,
				"repository_id": result.RepositoryID,
				"path":          result.Path,
				"created_at":    result.CreatedAt,
				"timestamp":     time.Now(),
			},
		})
	}
	logger.Debug("Repository init result sent", nil)
}
