package task

import (
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/hyperfilelens/proxy/config"
	"github.com/hyperfilelens/proxy/kopia"
	"github.com/hyperfilelens/proxy/mount"
	"github.com/hyperfilelens/proxy/ws"
)

// Type constants for task types
const (
	TypeBackup  = "backup"
	TypeRestore = "restore"
	TypeMount   = "mount"
	TypeList    = "list_snapshots"
)

// Status constants
const (
	StatusRunning   = "running"
	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCancelled = "cancelled"
)

// Task represents a task
type Task struct {
	ID      string                 `json:"id"`
	Type    string                 `json:"type"`
	Payload map[string]interface{} `json:"payload"`
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
	config     *config.Config
	kopia      *kopia.Client
	mountMgr   *mount.Manager
	wsClient   *ws.Client
	
	tasks    map[string]*Status
	tasksMu  sync.RWMutex
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
	fmt.Printf("[INFO] Received task: type=%s, id=%s\n", msg.Type, msg.ID)
	
	switch msg.Type {
	case "backup", "backup_task":
		go d.executeBackup(msg)
	case "restore", "restore_task":
		go d.executeRestore(msg)
	case "mount":
		go d.executeMount(msg)
	case "list_snapshots":
		go d.listSnapshots(msg)
	case "cancel":
		go d.cancelTask(msg)
	case "test_storage":
		go d.executeTestStorage(msg)
	case "init_repository":
		go d.executeInitRepository(msg)
	case "ping":
		d.wsClient.Send(ws.Message{Type: "pong", ID: msg.ID})
	case "connection_established":
		// Server confirmed WebSocket connection
		fmt.Println("[INFO] WebSocket connection confirmed by server")
	case "register_ack":
		// Server acknowledged proxy registration
		fmt.Println("[INFO] Proxy registration acknowledged by server")
	default:
		fmt.Printf("[WARN] Unknown task type: %s\n", msg.Type)
	}
}

// executeBackup executes a backup task
func (d *Dispatcher) executeBackup(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	sourcePath := getString(msg.Payload, "source_path", "")
	repoConfig := getMap(msg.Payload, "repository")
	password := getString(msg.Payload, "password", "")
	
	if sourcePath == "" {
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
		if err := d.kopia.ConnectRepo(repoConfig, password); err != nil {
			d.failTask(taskID, err.Error())
			d.sendError(msg.ID, taskID, err.Error())
			return
		}
	}
	
	// Execute backup
	result, err := d.kopia.Backup(taskID, sourcePath, password)
	
	if err != nil {
		d.failTask(taskID, err.Error())
		d.sendTaskFailed(msg.ID, taskID, err.Error())
	} else {
		d.completeTask(taskID, "Backup completed")
		d.sendTaskCompleted(msg.ID, taskID, result)
	}
}

// executeRestore executes a restore task
func (d *Dispatcher) executeRestore(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	targetPath := getString(msg.Payload, "target_path", "")
	repoConfig := getMap(msg.Payload, "repository")
	password := getString(msg.Payload, "password", "")
	overwrite := getBool(msg.Payload, "overwrite", false)
	
	if snapshotID == "" || targetPath == "" {
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
		if err := d.kopia.ConnectRepo(repoConfig, password); err != nil {
			d.failTask(taskID, err.Error())
			d.sendError(msg.ID, taskID, err.Error())
			return
		}
	}
	
	// Execute restore
	result, err := d.kopia.Restore(taskID, snapshotID, targetPath, password, overwrite)
	
	if err != nil {
		d.failTask(taskID, err.Error())
		d.sendTaskFailed(msg.ID, taskID, err.Error())
	} else {
		d.completeTask(taskID, "Restore completed")
		d.sendTaskCompleted(msg.ID, taskID, result)
	}
}

// executeMount executes a mount task (Sync Proxy only)
func (d *Dispatcher) executeMount(msg ws.Message) {
	if !d.config.IsSyncProxy() {
		d.sendError(msg.ID, "", "mount only available for Sync Proxy")
		return
	}
	
	mountType := getString(msg.Payload, "type", "nfs")
	
	var err error
	switch mountType {
	case "nfs":
		server := getString(msg.Payload, "server", "")
		path := getString(msg.Payload, "path", "")
		target := getString(msg.Payload, "target", "")
		err = d.mountMgr.MountNFS(server, path, target)
	case "smb":
		server := getString(msg.Payload, "server", "")
		share := getString(msg.Payload, "share", "")
		target := getString(msg.Payload, "target", "")
		username := getString(msg.Payload, "username", "")
		password := getString(msg.Payload, "password", "")
		err = d.mountMgr.MountSMB(server, share, target, username, password)
	default:
		err = fmt.Errorf("unsupported mount type: %s", mountType)
	}
	
	if err != nil {
		d.sendError(msg.ID, "", err.Error())
		return
	}
	
	d.wsClient.Send(ws.Message{
		Type: "mount_completed",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"type":   mountType,
			"status": "mounted",
		},
	})
}

// listSnapshots lists available snapshots
func (d *Dispatcher) listSnapshots(msg ws.Message) {
	password := getString(msg.Payload, "password", "")
	
	snapshots, err := d.kopia.ListSnapshots(password)
	if err != nil {
		d.sendError(msg.ID, "", err.Error())
		return
	}
	
	d.wsClient.Send(ws.Message{
		Type: "snapshot_list",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"snapshots": snapshots,
		},
	})
}

// cancelTask cancels a running task
func (d *Dispatcher) cancelTask(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", "")
	
	d.tasksMu.Lock()
	defer d.tasksMu.Unlock()
	
	if status, exists := d.tasks[taskID]; exists {
		status.Status = StatusCancelled
		status.Message = "Task cancelled"
		status.EndTime = time.Now()
		
		// Cancel Kopia operation
		d.kopia.Cancel(taskID)
		
		d.wsClient.Send(ws.Message{
			Type: "task_cancelled",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id": taskID,
			},
		})
	}
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
	d.wsClient.Send(ws.Message{
		Type: "task_start",
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": taskType,
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) sendTaskCompleted(msgID, taskID string, result interface{}) {
	d.wsClient.Send(ws.Message{
		Type: "task_completed",
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id": taskID,
			"result":  result,
		},
	})
}

func (d *Dispatcher) sendTaskFailed(msgID, taskID, errMsg string) {
	d.wsClient.Send(ws.Message{
		Type: "task_failed",
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id": taskID,
			"error":   errMsg,
		},
	})
}

func (d *Dispatcher) sendError(msgID, taskID, errMsg string) {
	d.wsClient.Send(ws.Message{
		Type: "error",
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id": taskID,
			"error":   errMsg,
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

// executeTestStorage executes a storage connectivity test (Sync Proxy only)
func (d *Dispatcher) executeTestStorage(msg ws.Message) {
	if !d.config.IsSyncProxy() {
		d.sendError(msg.ID, "", "test_storage only available for Sync Proxy")
		return
	}

	taskID := getString(msg.Payload, "task_id", msg.ID)
	storageType := getString(msg.Payload, "storage_type", "nas") // nas, s3, local
	testWrite := getBool(msg.Payload, "test_write", true)
	repositoryID := getString(msg.Payload, "repository_id", "")

	fmt.Printf("[INFO] Starting storage test: type=%s, task_id=%s\n", storageType, taskID)

	// Send task start notification
	d.wsClient.Send(ws.Message{
		Type: "task_start",
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

		if server == "" {
			d.sendStorageTestResult(msg.ID, taskID, result, "server is required")
			return
		}

		// Test connectivity
		var connResult *mount.ConnectivityResult
		if mountType == "smb" {
			connResult = mount.TestSMBConnectivity(server)
		} else {
			connResult = mount.TestNFSConnectivity(server)
		}

		result["connectivity"] = map[string]interface{}{
			"reachable":     connResult.Reachable,
			"response_time": connResult.ResponseTime,
			"error":         connResult.Error,
		}

		if !connResult.Reachable {
			d.sendStorageTestResult(msg.ID, taskID, result, fmt.Sprintf("connectivity test failed: %s", connResult.Error))
			return
		}

		// Test write if mount_path provided
		if testWrite {
			mountPath := getString(msg.Payload, "mount_path", "")
			if mountPath != "" {
				writeResult := mount.TestWriteSimple(mountPath)
				result["write_test"] = map[string]interface{}{
					"writable":    writeResult.Writable,
					"write_speed": writeResult.WriteSpeed,
					"read_speed":  writeResult.ReadSpeed,
					"error":       writeResult.Error,
				}

				// Get space info
				total, used, free, err := mount.GetMountSpaceInfo(mountPath)
				if err == nil {
					result["space_info"] = map[string]interface{}{
						"total_bytes": total,
						"used_bytes":  used,
						"free_bytes":  free,
					}
				}
			}
		}

		result["success"] = true
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
	if errMsg != "" {
		result["error"] = errMsg
		d.wsClient.Send(ws.Message{
			Type: "test_storage_result",
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":    taskID,
				"success":    false,
				"error":      errMsg,
				"result":     result,
				"timestamp":  time.Now(),
			},
		})
	} else {
		d.wsClient.Send(ws.Message{
			Type: "test_storage_result",
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":   taskID,
				"success":   true,
				"result":    result,
				"timestamp": time.Now(),
			},
		})
	}
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

	fmt.Printf("[INFO] Starting repository initialization: repo_id=%s, task_id=%s\n", repositoryID, taskID)

	// Send task start notification
	d.wsClient.Send(ws.Message{
		Type: "task_start",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":       taskID,
			"task_type":     "init_repository",
			"repository_id": repositoryID,
			"timestamp":     time.Now(),
		},
	})

	if len(repoConfig) == 0 {
		d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, "repository config is required")
		return
	}

	// Execute repository creation
	result, err := d.kopia.CreateRepo(repoConfig, password)
	if err != nil {
		d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, err.Error())
		return
	}

	d.sendRepoInitResult(msg.ID, taskID, repositoryID, result, "")
}

// sendRepoInitResult sends repository initialization result to server
func (d *Dispatcher) sendRepoInitResult(msgID, taskID, repositoryID string, result *kopia.CreateRepoResult, errMsg string) {
	if errMsg != "" {
		d.wsClient.Send(ws.Message{
			Type: "init_repository_result",
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
			Type: "init_repository_result",
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":       taskID,
				"repository_id": repositoryID,
				"success":       true,
				"repository_id": result.RepositoryID,
				"path":          result.Path,
				"created_at":    result.CreatedAt,
				"timestamp":     time.Now(),
			},
		})
	}
}
