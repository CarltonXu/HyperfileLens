package task

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/hyperfilelens/proxy/config"
	"github.com/hyperfilelens/proxy/kopia"
	"github.com/hyperfilelens/proxy/logger"
	"github.com/hyperfilelens/proxy/message"
	"github.com/hyperfilelens/proxy/mount"
	"github.com/hyperfilelens/proxy/ws"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

// Type constants for task types (using message package constants)
const (
	TypeBackup         = message.TypeBackup
	TypeRestore        = message.TypeRestore
	TypeMount          = message.TypeMount
	TypeList           = message.TypeList
	TypeSnapshotExport = "snapshot_export"
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
	case message.MsgTypeListSnapshots, "snapshot_list":
		go d.listSnapshots(msg)
	case message.MsgTypeDeleteSnapshots, "snapshot_delete":
		go d.deleteSnapshots(msg)
	case message.MsgTypeRunMaintenance, "kopia_maintenance":
		go d.runMaintenance(msg)
	case message.MsgTypePolicyShow:
		go d.showPolicy(msg)
	case message.MsgTypeCancel:
		go d.cancelTask(msg)
	case message.MsgTypeTestStorage:
		logger.Info("Executing test_storage task in goroutine", nil)
		go d.executeTestStorage(msg)
	case message.MsgTypeInitRepository:
		go d.executeInitRepository(msg)
	case message.MsgTypeListDirectory:
		go d.executeListDirectory(msg)
	case message.MsgTypeListSnapshotFiles:
		go d.listSnapshotFiles(msg)
	case message.MsgTypeSnapshotExport:
		go d.executeSnapshotExport(msg)

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

// executeListDirectory lists local directories on the bound Proxy.
func (d *Dispatcher) executeListDirectory(msg ws.Message) {
	if msg.Payload == nil {
		d.sendListDirectoryResult(msg.ID, "", "", nil, "payload is empty")
		return
	}

	taskID := getString(msg.Payload, "task_id", msg.ID)
	requestedPath := getString(msg.Payload, "path", "/")
	if requestedPath == "" {
		requestedPath = "/"
	}
	cleanPath := filepath.Clean(os.ExpandEnv(requestedPath))
	if !filepath.IsAbs(cleanPath) {
		d.sendListDirectoryResult(msg.ID, taskID, requestedPath, nil, "path must be absolute")
		return
	}

	info, err := os.Stat(cleanPath)
	if err != nil {
		d.sendListDirectoryResult(msg.ID, taskID, cleanPath, nil, fmt.Sprintf("path not accessible: %v", err))
		return
	}
	if !info.IsDir() {
		d.sendListDirectoryResult(msg.ID, taskID, cleanPath, nil, "path is not a directory")
		return
	}

	entries, err := os.ReadDir(cleanPath)
	if err != nil {
		d.sendListDirectoryResult(msg.ID, taskID, cleanPath, nil, fmt.Sprintf("failed to read directory: %v", err))
		return
	}

	directories := make([]map[string]interface{}, 0)
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		name := entry.Name()
		fullPath := filepath.Join(cleanPath, name)
		item := map[string]interface{}{
			"name": name,
			"path": fullPath,
		}
		if fi, err := entry.Info(); err == nil {
			item["mode"] = fi.Mode().String()
			item["mod_time"] = fi.ModTime().Format(time.RFC3339)
		}
		directories = append(directories, item)
	}

	sort.Slice(directories, func(i, j int) bool {
		return directories[i]["name"].(string) < directories[j]["name"].(string)
	})

	d.sendListDirectoryResult(msg.ID, taskID, cleanPath, directories, "")
}

func (d *Dispatcher) sendListDirectoryResult(msgID, taskID, path string, directories []map[string]interface{}, errMsg string) {
	payload := map[string]interface{}{
		"task_id":     taskID,
		"success":     errMsg == "",
		"path":        path,
		"directories": directories,
		"timestamp":   time.Now(),
	}
	if errMsg != "" {
		payload["error"] = errMsg
	}
	d.wsClient.Send(ws.Message{
		Type:    message.MsgTypeListDirectoryResult,
		ID:      msgID,
		Payload: payload,
	})
}

// executeBackup executes a backup task
func (d *Dispatcher) executeBackup(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	sourcePath := getString(msg.Payload, "source_path", "")
	repoConfig := getMap(msg.Payload, "repository")
	sourceConfig := getMap(msg.Payload, "source_resource")
	effectivePolicy := getMap(msg.Payload, "effective_policy")
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

	var mountedSourcePath string
	var tempSourceMountPath string
	defer func() {
		if mountedSourcePath != "" {
			if err := d.mountMgr.Unmount(mountedSourcePath); err != nil {
				logger.Warn("Failed to unmount temporary source path", map[string]interface{}{
					"mount_path": mountedSourcePath,
					"error":      err.Error(),
				})
			}
		}
		if tempSourceMountPath != "" {
			if err := safeRemoveMountPointDir(tempSourceMountPath); err != nil {
				logger.Warn("Failed to remove temporary source mount path", map[string]interface{}{
					"mount_path": tempSourceMountPath,
					"error":      err.Error(),
				})
			}
		}
	}()

	if len(sourceConfig) > 0 {
		adjustedSourcePath, mountedPath, tempPath, err := d.prepareBackupSource(taskID, sourcePath, sourceConfig)
		if err != nil {
			logger.Error("Failed to prepare backup source", map[string]interface{}{"error": err.Error()})
			d.sendError(msg.ID, taskID, err.Error())
			return
		}
		sourcePath = adjustedSourcePath
		mountedSourcePath = mountedPath
		tempSourceMountPath = tempPath
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
	d.sendTaskProgress(msg.ID, taskID, TypeBackup, 5, "Connecting repository")

	// Connect to repository if config provided
	if len(repoConfig) > 0 {
		logger.Debug("Connecting to repository...", nil)
		if err := d.connectRepository(repoConfig, password); err != nil {
			logger.Error("Failed to connect to repository", map[string]interface{}{
				"error": err.Error(),
			})
			d.failTask(taskID, err.Error())
			d.sendError(msg.ID, taskID, err.Error())
			return
		}
		logger.Debug("Repository connected successfully", nil)
	}
	d.sendTaskProgress(msg.ID, taskID, TypeBackup, 20, "Repository connected")

	if len(effectivePolicy) > 0 {
		d.sendTaskProgress(msg.ID, taskID, TypeBackup, 22, "Applying backup policy")
		if err := d.kopia.ApplyPolicy(effectivePolicy, sourcePath, password); err != nil {
			logger.Error("Failed to apply backup policy", map[string]interface{}{
				"error": err.Error(),
			})
			d.failTask(taskID, err.Error())
			d.sendTaskFailed(msg.ID, taskID, err.Error())
			return
		}
		d.sendTaskProgress(msg.ID, taskID, TypeBackup, 24, "Backup policy applied")
	}

	// Execute backup
	logger.Debug("Starting Kopia backup...", nil)
	progress := NewProgress(taskID, TypeBackup, "Creating Kopia snapshot")
	progress.Progress = 25
	d.sendTaskProgressWithDetails(msg.ID, progress)
	result, err := d.kopia.BackupWithProgress(taskID, sourcePath, password, func(update kopia.BackupProgress) {
		progress.ProcessedFiles = update.ProcessedFiles
		progress.TotalFiles = update.TotalFiles
		progress.ProcessedBytes = update.ProcessedBytes
		progress.TotalBytes = update.TotalBytes
		progress.SpeedMBps = update.SpeedMBps
		progress.ETA = update.ETA
		if update.Percent > 0 {
			progress.Progress = 25 + int(float64(update.Percent)*0.70)
		}
		if progress.Progress > 95 {
			progress.Progress = 95
		}
		progress.Message = "Kopia snapshot running"
		d.sendTaskProgressWithDetails(msg.ID, progress)
	})

	if err != nil {
		logger.Error("Backup failed", map[string]interface{}{
			"error": err.Error(),
		})
		d.failTask(taskID, err.Error())
		d.sendTaskFailed(msg.ID, taskID, err.Error())
	} else {
		progress.TotalFiles = result.TotalFiles
		progress.ProcessedFiles = result.BackedUpFiles
		progress.TotalBytes = result.TotalSize
		progress.ProcessedBytes = result.BackedUpSize
		progress.SpeedMBps = float64(result.BytesPerSecond) / 1024 / 1024
		progress.MarkCompleted("Backup completed")
		d.sendTaskProgressWithDetails(msg.ID, progress)
		logger.Debug("Backup completed successfully", map[string]interface{}{
			"result": result,
		})
		d.completeTask(taskID, "Backup completed")
		d.sendTaskCompleted(msg.ID, taskID, result)
	}

	logger.Debug("Backup task end", nil)
}

func (d *Dispatcher) prepareBackupSource(taskID, sourcePath string, sourceConfig map[string]interface{}) (string, string, string, error) {
	sourceType := getString(sourceConfig, "type", getString(sourceConfig, "resource_type", ""))
	switch sourceType {
	case "", "local":
		return sourcePath, "", "", nil
	case "nas", "nfs", "cifs":
		if !d.config.IsSyncProxy() {
			return "", "", "", fmt.Errorf("network source backup requires a Sync Proxy")
		}
		server := getString(sourceConfig, "server", "")
		remotePath := getString(sourceConfig, "export_path", getString(sourceConfig, "share", ""))
		mountType := getString(sourceConfig, "mount_type", "nfs")
		mountOptions := getString(sourceConfig, "mount_options", "")
		username := getString(sourceConfig, "username", "")
		password := getString(sourceConfig, "password", "")
		if server == "" || remotePath == "" {
			return "", "", "", fmt.Errorf("network source server and path are required")
		}
		mountPath, removeAfterUse, err := d.resolveStableSourceMountPath(taskID, sourceConfig)
		if err != nil {
			return "", "", "", err
		}
		if err := os.MkdirAll(mountPath, 0755); err != nil {
			return "", "", "", fmt.Errorf("failed to create source mount directory: %w", err)
		}
		if mount.IsPathMounted(mountPath) {
			logger.Debug("Reusing already mounted source path", map[string]interface{}{
				"task_id":    taskID,
				"mount_path": mountPath,
			})
			return resolveMountedSourcePath(sourcePath, mountPath, remotePath, getString(sourceConfig, "mount_point", "")), "", "", nil
		}
		if mountType == "smb" || mountType == "cifs" {
			err = d.mountMgr.MountSMB(server, remotePath, mountPath, username, password, mountOptions)
		} else {
			err = d.mountMgr.MountNFS(server, remotePath, mountPath, mountOptions)
		}
		if err != nil {
			if mount.IsPathMounted(mountPath) {
				logger.Warn("Mount command failed but source path is mounted; continuing with mounted path", map[string]interface{}{
					"task_id":    taskID,
					"mount_path": mountPath,
					"error":      err.Error(),
				})
				return resolveMountedSourcePath(sourcePath, mountPath, remotePath, getString(sourceConfig, "mount_point", "")), "", "", nil
			}
			if removeAfterUse {
				if removeErr := safeRemoveMountPointDir(mountPath); removeErr != nil {
					logger.Warn("Failed to remove unmounted source path after mount failure", map[string]interface{}{
						"mount_path": mountPath,
						"error":      removeErr.Error(),
					})
				}
			}
			return "", "", "", fmt.Errorf("failed to mount network source: %w", err)
		}
		tempPath := ""
		if removeAfterUse {
			tempPath = mountPath
		}
		return resolveMountedSourcePath(sourcePath, mountPath, remotePath, getString(sourceConfig, "mount_point", "")), mountPath, tempPath, nil
	case "s3":
		return "", "", "", fmt.Errorf("S3 object storage as backup source is not yet supported by this proxy backup executor")
	default:
		return sourcePath, "", "", nil
	}
}

func (d *Dispatcher) resolveStableSourceMountPath(taskID string, sourceConfig map[string]interface{}) (string, bool, error) {
	configuredMountPoint := strings.TrimSpace(getString(sourceConfig, "mount_point", ""))
	if configuredMountPoint != "" && filepath.IsAbs(configuredMountPoint) {
		return filepath.Clean(configuredMountPoint), false, nil
	}

	sourceID := strings.TrimSpace(getString(sourceConfig, "id", ""))
	if sourceID != "" {
		return filepath.Join("/mnt/hyperfilelens", "source-"+safeSourceIDPrefix(sourceID)), false, nil
	}

	return filepath.Join("/mnt/hyperfilelens", "sources", "task-"+safePathToken(taskID)), false, nil
}

func resolveMountedSourcePath(sourcePath, mountPath, remotePath, configuredMountPoint string) string {
	candidates := []string{remotePath, configuredMountPoint}
	cleanSource := filepath.Clean(sourcePath)
	if sourcePath == "" || sourcePath == "/" || sourcePath == "." {
		return mountPath
	}
	for _, candidate := range candidates {
		if candidate == "" {
			continue
		}
		cleanCandidate := filepath.Clean(candidate)
		if cleanSource == cleanCandidate {
			return mountPath
		}
		if strings.HasPrefix(cleanSource, cleanCandidate+string(os.PathSeparator)) {
			relative := strings.TrimPrefix(cleanSource, cleanCandidate)
			return filepath.Join(mountPath, strings.TrimLeft(relative, `/\`))
		}
	}
	return filepath.Join(mountPath, strings.TrimLeft(sourcePath, `/\`))
}

func (d *Dispatcher) connectRepository(repoConfig map[string]interface{}, password string) error {
	kopiaConfig, err := d.prepareRepository(repoConfig)
	if err != nil {
		return err
	}
	return d.kopia.ConnectRepo(kopiaConfig, password)
}

func (d *Dispatcher) prepareRepository(repoConfig map[string]interface{}) (map[string]interface{}, error) {
	if len(repoConfig) == 0 {
		return repoConfig, nil
	}
	repoType := strings.ToLower(getString(repoConfig, "type", "filesystem"))
	switch repoType {
	case "nas", "nfs", "cifs":
		if !d.config.IsSyncProxy() {
			return nil, fmt.Errorf("network repository requires a Sync Proxy")
		}
		server := getString(repoConfig, "server", getString(repoConfig, "nas_server", ""))
		remotePath := getString(repoConfig, "export_path", getString(repoConfig, "nas_path", getString(repoConfig, "path", "")))
		mountType := strings.ToLower(getString(repoConfig, "mount_type", repoType))
		mountOptions := getString(repoConfig, "mount_options", "")
		username := getString(repoConfig, "username", "")
		mountPassword := getString(repoConfig, "password", "")
		if server == "" || remotePath == "" {
			return nil, fmt.Errorf("network repository server and export path are required")
		}
		mountPath, err := d.resolveStableRepositoryMountPath(repoConfig)
		if err != nil {
			return nil, err
		}
		if err := os.MkdirAll(mountPath, 0755); err != nil {
			return nil, fmt.Errorf("failed to create repository mount directory: %w", err)
		}
		if !mount.IsPathMounted(mountPath) {
			if mountType == "smb" || mountType == "cifs" {
				err = d.mountMgr.MountSMB(server, remotePath, mountPath, username, mountPassword, mountOptions)
			} else {
				err = d.mountMgr.MountNFS(server, remotePath, mountPath, mountOptions)
			}
			if err != nil {
				if mount.IsPathMounted(mountPath) {
					logger.Warn("Repository mount command failed but path is mounted; continuing", map[string]interface{}{
						"mount_path": mountPath,
						"error":      err.Error(),
					})
				} else {
					return nil, fmt.Errorf("failed to mount network repository: %w", err)
				}
			}
		}
		kopiaConfig := copyMap(repoConfig)
		kopiaConfig["type"] = "filesystem"
		kopiaConfig["path"] = mountPath
		kopiaConfig["mounted_path"] = mountPath
		return kopiaConfig, nil
	default:
		return repoConfig, nil
	}
}

func (d *Dispatcher) resolveStableRepositoryMountPath(repoConfig map[string]interface{}) (string, error) {
	configuredMountPath := strings.TrimSpace(getString(repoConfig, "mount_path", ""))
	if configuredMountPath != "" && filepath.IsAbs(configuredMountPath) {
		return filepath.Clean(configuredMountPath), nil
	}
	repositoryID := strings.TrimSpace(getString(repoConfig, "id", getString(repoConfig, "repository_id", "")))
	if repositoryID != "" {
		return filepath.Join("/mnt/hyperfilelens", "repository-"+safeSourceIDPrefix(repositoryID)), nil
	}
	return filepath.Join("/mnt/hyperfilelens", "repository-unknown"), nil
}

func safePathToken(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return "unknown"
	}
	var b strings.Builder
	for _, r := range value {
		switch {
		case r >= 'a' && r <= 'z':
			b.WriteRune(r)
		case r >= 'A' && r <= 'Z':
			b.WriteRune(r)
		case r >= '0' && r <= '9':
			b.WriteRune(r)
		case r == '-' || r == '_' || r == '.':
			b.WriteRune(r)
		default:
			b.WriteRune('-')
		}
	}
	token := strings.Trim(b.String(), "-.")
	if token == "" {
		return "unknown"
	}
	return token
}

func safeSourceIDPrefix(sourceID string) string {
	token := safePathToken(sourceID)
	if len(token) > 8 {
		return token[:8]
	}
	return token
}

func resolveStorageTestMountPath(taskID, repositoryID, sourceResourceID, configuredMountPath string) (string, bool, error) {
	configuredMountPath = strings.TrimSpace(configuredMountPath)
	if configuredMountPath != "" {
		if !filepath.IsAbs(configuredMountPath) {
			return "", false, fmt.Errorf("configured mount_path must be absolute")
		}
		return filepath.Clean(configuredMountPath), false, nil
	}
	if sourceResourceID != "" {
		return filepath.Join("/mnt/hyperfilelens", "source-"+safeSourceIDPrefix(sourceResourceID)), false, nil
	}
	if repositoryID != "" {
		return filepath.Join("/mnt/hyperfilelens", "repository-"+safeSourceIDPrefix(repositoryID)), false, nil
	}
	return filepath.Join("/mnt/hyperfilelens", "storage-test", "task-"+safePathToken(taskID)), true, nil
}

func safeRemoveMountPointDir(path string) error {
	path = filepath.Clean(strings.TrimSpace(path))
	if path == "" || path == "." || path == string(os.PathSeparator) {
		return fmt.Errorf("refusing to remove unsafe path %q", path)
	}
	if mount.IsPathMounted(path) {
		return fmt.Errorf("refusing to remove %s because it is still mounted", path)
	}
	if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

// executeRestore executes a restore task
func (d *Dispatcher) executeRestore(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	objectID := getString(msg.Payload, "object_id", "")
	targetPath := getString(msg.Payload, "target_path", "")
	repoConfig := getMap(msg.Payload, "repository")
	password := getString(msg.Payload, "password", "")
	overwrite := getBool(msg.Payload, "overwrite", false)
	restoreScope := getString(msg.Payload, "restore_scope", "entire_snapshot")
	restorePaths := getStringSlice(msg.Payload, "restore_paths")

	logger.Debug("Restore task start", map[string]interface{}{
		"task_id":       taskID,
		"snapshot_id":   snapshotID,
		"object_id":     objectID,
		"target_path":   targetPath,
		"repo_config":   repoConfig,
		"password":      "[REDACTED]",
		"overwrite":     overwrite,
		"restore_scope": restoreScope,
		"restore_paths": restorePaths,
	})

	if snapshotID == "" || targetPath == "" {
		logger.Error("snapshot_id and target_path are required", nil)
		d.sendError(msg.ID, taskID, "snapshot_id and target_path are required")
		return
	}
	if restoreScope == "selected_paths" && (objectID == "" || len(restorePaths) == 0) {
		logger.Error("object_id and restore_paths are required for selected path restore", nil)
		d.sendError(msg.ID, taskID, "object_id and restore_paths are required for selected path restore")
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
	d.sendTaskProgress(msg.ID, taskID, TypeRestore, 5, "Connecting repository")

	// Connect to repository
	if len(repoConfig) > 0 {
		logger.Debug("Connecting to repository...", nil)
		if err := d.connectRepository(repoConfig, password); err != nil {
			logger.Error("Failed to connect to repository", map[string]interface{}{
				"error": err.Error(),
			})
			d.failTask(taskID, err.Error())
			d.sendError(msg.ID, taskID, err.Error())
			return
		}
		logger.Debug("Repository connected successfully", nil)
	}
	d.sendTaskProgress(msg.ID, taskID, TypeRestore, 20, "Repository connected")

	// Execute restore
	logger.Debug("Starting Kopia restore...", nil)
	d.sendTaskProgress(msg.ID, taskID, TypeRestore, 30, "Restoring snapshot")
	var result *kopia.RestoreResult
	var err error
	if restoreScope == "selected_paths" {
		result, err = d.kopia.RestoreSelected(taskID, objectID, targetPath, password, overwrite, restorePaths)
	} else if objectID != "" {
		result, err = d.kopia.RestoreObject(taskID, objectID, targetPath, password, overwrite)
	} else {
		result, err = d.kopia.Restore(taskID, snapshotID, targetPath, password, overwrite)
	}

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
		d.sendTaskProgress(msg.ID, taskID, TypeRestore, 100, "Restore completed")
		d.completeTask(taskID, "Restore completed")
		d.sendTaskCompleted(msg.ID, taskID, result)
	}

	logger.Debug("Restore task end", nil)
}

func (d *Dispatcher) executeSnapshotExport(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	exportID := getString(msg.Payload, "recovery_export_id", "")
	objectID := getString(msg.Payload, "object_id", "")
	repoConfig := getMap(msg.Payload, "repository")
	password := getString(msg.Payload, "password", "")
	selectedPaths := getStringSlice(msg.Payload, "selected_paths")
	uploadURL := getString(msg.Payload, "upload_url", "")

	if taskID == "" || exportID == "" || objectID == "" || len(selectedPaths) == 0 {
		d.sendTaskFailed(msg.ID, taskID, "task_id, recovery_export_id, object_id and selected_paths are required")
		return
	}

	status := &Status{
		TaskID:    taskID,
		Type:      TypeSnapshotExport,
		Status:    StatusRunning,
		Progress:  0,
		Message:   "Starting snapshot export",
		StartTime: time.Now(),
	}
	d.setTask(status)
	d.sendTaskStart(msg.ID, taskID, TypeSnapshotExport)
	d.sendTaskProgress(msg.ID, taskID, TypeSnapshotExport, 5, "Connecting repository")

	if len(repoConfig) > 0 {
		if err := d.connectRepository(repoConfig, password); err != nil {
			d.failTask(taskID, err.Error())
			d.sendTaskFailed(msg.ID, taskID, err.Error())
			return
		}
	}

	d.sendTaskProgress(msg.ID, taskID, TypeSnapshotExport, 25, "Restoring selected paths")
	stagingRoot := d.config.Storage.TempDirectory
	if stagingRoot == "" {
		stagingRoot = "/tmp/hyperfilelens"
	}
	result, err := d.kopia.ExportSelected(taskID, objectID, stagingRoot, password, selectedPaths, func(update kopia.ExportProgress) {
		d.sendSnapshotExportProgress(msg.ID, taskID, update)
	})
	if err != nil {
		d.failTask(taskID, err.Error())
		d.sendTaskFailed(msg.ID, taskID, err.Error())
		return
	}

	d.sendTaskProgress(msg.ID, taskID, TypeSnapshotExport, 85, "Uploading export package")
	if err := d.uploadExportPackage(uploadURL, result.PackagePath, result.PackageName, result.Checksum, func(uploaded, total int64, speedMBps float64, eta string) {
		progress := 85
		if total > 0 {
			progress = 85 + int(float64(uploaded)/float64(total)*14)
		}
		if progress > 99 {
			progress = 99
		}
		d.sendSnapshotExportProgress(msg.ID, taskID, kopia.ExportProgress{
			Stage:          "upload",
			Message:        "Uploading export package",
			Progress:       progress,
			CurrentFile:    result.PackageName,
			TotalFiles:     1,
			ProcessedFiles: 0,
			TotalBytes:     total,
			ProcessedBytes: uploaded,
			SpeedMBps:      speedMBps,
			ETA:            eta,
		})
	}); err != nil {
		d.failTask(taskID, err.Error())
		d.sendTaskFailed(msg.ID, taskID, err.Error())
		return
	}

	d.sendTaskProgress(msg.ID, taskID, TypeSnapshotExport, 100, "Export package ready")
	d.completeTask(taskID, "Export package ready")
	d.sendTaskCompleted(msg.ID, taskID, result)
}

func (d *Dispatcher) sendSnapshotExportProgress(msgID, taskID string, update kopia.ExportProgress) {
	progress := NewProgress(taskID, TypeSnapshotExport, update.Message)
	progress.Progress = update.Progress
	progress.CurrentFile = update.CurrentFile
	progress.TotalFiles = update.TotalFiles
	progress.ProcessedFiles = update.ProcessedFiles
	progress.TotalBytes = update.TotalBytes
	progress.ProcessedBytes = update.ProcessedBytes
	progress.SpeedMBps = update.SpeedMBps
	progress.ETA = update.ETA
	d.sendTaskProgressWithDetails(msgID, progress)
}

func (d *Dispatcher) uploadExportPackage(uploadURL, packagePath, packageName, checksum string, onProgress func(uploaded, total int64, speedMBps float64, eta string)) error {
	if uploadURL == "" {
		return fmt.Errorf("upload_url is required")
	}
	if strings.HasPrefix(uploadURL, "/") {
		uploadURL = strings.TrimRight(d.config.Server.URL, "/") + uploadURL
	}
	var lastErr error
	for attempt := 1; attempt <= 2; attempt++ {
		if err := d.uploadExportPackageOnce(uploadURL, packagePath, packageName, checksum, onProgress); err != nil {
			lastErr = err
			if attempt == 1 {
				logger.Warn("Export upload failed, retrying once", map[string]interface{}{
					"error": err.Error(),
				})
				time.Sleep(2 * time.Second)
				continue
			}
		} else {
			return nil
		}
	}
	return lastErr
}

type exportUploadProgressReader struct {
	reader     io.Reader
	total      int64
	read       int64
	startedAt  time.Time
	onProgress func(uploaded, total int64, speedMBps float64, eta string)
}

func (r *exportUploadProgressReader) Read(p []byte) (int, error) {
	n, err := r.reader.Read(p)
	if n > 0 {
		r.read += int64(n)
		if r.onProgress != nil {
			elapsed := time.Since(r.startedAt).Seconds()
			speedMBps := 0.0
			eta := ""
			if elapsed > 0 {
				speedBps := float64(r.read) / elapsed
				speedMBps = speedBps / 1024 / 1024
				if speedBps > 0 && r.total > r.read {
					eta = formatExportDuration(float64(r.total-r.read) / speedBps)
				}
			}
			r.onProgress(r.read, r.total, speedMBps, eta)
		}
	}
	return n, err
}

func formatExportDuration(seconds float64) string {
	if seconds <= 0 {
		return ""
	}
	duration := time.Duration(seconds) * time.Second
	if duration < time.Minute {
		return fmt.Sprintf("%ds", int(duration.Seconds()))
	}
	if duration < time.Hour {
		return fmt.Sprintf("%dm%02ds", int(duration.Minutes()), int(duration.Seconds())%60)
	}
	return fmt.Sprintf("%dh%02dm", int(duration.Hours()), int(duration.Minutes())%60)
}

func (d *Dispatcher) uploadExportPackageOnce(uploadURL, packagePath, packageName, checksum string, onProgress func(uploaded, total int64, speedMBps float64, eta string)) error {
	file, err := os.Open(packagePath)
	if err != nil {
		return fmt.Errorf("failed to open export package: %w", err)
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return fmt.Errorf("failed to stat export package: %w", err)
	}

	var header bytes.Buffer
	writer := multipart.NewWriter(&header)
	if err := writer.WriteField("checksum", checksum); err != nil {
		return fmt.Errorf("failed to write checksum field: %w", err)
	}
	if _, err := writer.CreateFormFile("file", packageName); err != nil {
		return fmt.Errorf("failed to prepare upload form: %w", err)
	}
	contentType := writer.FormDataContentType()

	var footer bytes.Buffer
	footerWriter := multipart.NewWriter(&footer)
	if err := footerWriter.SetBoundary(writer.Boundary()); err != nil {
		return fmt.Errorf("failed to prepare upload boundary: %w", err)
	}
	if err := footerWriter.Close(); err != nil {
		return fmt.Errorf("failed to finalize upload form: %w", err)
	}

	reader := &exportUploadProgressReader{
		reader:     file,
		total:      info.Size(),
		startedAt:  time.Now(),
		onProgress: onProgress,
	}
	body := io.MultiReader(&header, reader, &footer)

	req, err := http.NewRequest("POST", uploadURL, body)
	if err != nil {
		return fmt.Errorf("failed to create upload request: %w", err)
	}
	req.ContentLength = int64(header.Len()) + info.Size() + int64(footer.Len())
	req.Header.Set("Content-Type", contentType)
	if d.config.Server.APIToken != "" {
		req.Header.Set("Authorization", "Token "+d.config.Server.APIToken)
	}
	client := &http.Client{Timeout: 24 * time.Hour}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to upload export package: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("export upload failed: %s - %s", resp.Status, strings.TrimSpace(string(respBody)))
	}
	return nil
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
	taskID := getString(msg.Payload, "task_id", msg.ID)
	password := getString(msg.Payload, "password", "")
	repoConfig := getMap(msg.Payload, "repository")
	sourcePath := getString(msg.Payload, "source_path", "")
	sourceConfig := getMap(msg.Payload, "source_resource")

	logger.Debug("Snapshot list start", nil)
	logger.Debug("Listing Kopia snapshots...", nil)
	d.sendTaskStart(msg.ID, taskID, message.MsgTypeListSnapshots)
	if len(repoConfig) > 0 {
		if err := d.connectRepository(repoConfig, password); err != nil {
			d.sendTaskFailed(msg.ID, taskID, err.Error())
			return
		}
	}
	if len(sourceConfig) > 0 {
		resolvedSourcePath, err := d.resolveSnapshotListSourcePath(taskID, sourcePath, sourceConfig)
		if err != nil {
			d.sendTaskFailed(msg.ID, taskID, err.Error())
			return
		}
		sourcePath = resolvedSourcePath
	}

	snapshots, err := d.kopia.ListSnapshotsForSource(password, sourcePath)
	if err != nil {
		logger.Error("Failed to list snapshots", map[string]interface{}{
			"error": err.Error(),
		})
		d.sendTaskFailed(msg.ID, taskID, err.Error())
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
		Type: message.MsgTypeTaskComplete,
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": message.MsgTypeListSnapshots,
			"success":   true,
			"result": map[string]interface{}{
				"snapshots":   snapshots,
				"source_path": sourcePath,
			},
			"timestamp": time.Now(),
		},
	})

	logger.Debug("Snapshot list end", nil)
}

func (d *Dispatcher) resolveSnapshotListSourcePath(taskID, sourcePath string, sourceConfig map[string]interface{}) (string, error) {
	sourceType := getString(sourceConfig, "type", getString(sourceConfig, "resource_type", ""))
	switch sourceType {
	case "", "local":
		return sourcePath, nil
	case "nas", "nfs", "cifs":
		mountPath, _, err := d.resolveStableSourceMountPath(taskID, sourceConfig)
		if err != nil {
			return "", err
		}
		remotePath := getString(sourceConfig, "export_path", getString(sourceConfig, "share", ""))
		configuredMountPoint := getString(sourceConfig, "mount_point", "")
		return resolveMountedSourcePath(sourcePath, mountPath, remotePath, configuredMountPoint), nil
	default:
		return sourcePath, nil
	}
}

func (d *Dispatcher) deleteSnapshots(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	password := getString(msg.Payload, "password", "")
	repoConfig := getMap(msg.Payload, "repository")
	snapshotIDs := getStringSlice(msg.Payload, "snapshot_ids")

	logger.Debug("Snapshot delete start", map[string]interface{}{
		"task_id": taskID,
		"count":   len(snapshotIDs),
	})
	d.sendTaskStart(msg.ID, taskID, message.MsgTypeDeleteSnapshots)
	if len(repoConfig) > 0 {
		if err := d.connectRepository(repoConfig, password); err != nil {
			d.sendTaskFailed(msg.ID, taskID, err.Error())
			return
		}
	}
	if len(snapshotIDs) == 0 {
		d.sendTaskFailed(msg.ID, taskID, "snapshot_ids is required")
		return
	}
	output, err := d.kopia.DeleteSnapshots(snapshotIDs, password)
	if err != nil {
		d.sendTaskFailed(msg.ID, taskID, err.Error())
		return
	}
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskComplete,
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": message.MsgTypeDeleteSnapshots,
			"success":   true,
			"result": map[string]interface{}{
				"snapshot_ids": snapshotIDs,
				"output":       output,
			},
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) runMaintenance(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	password := getString(msg.Payload, "password", "")
	repoConfig := getMap(msg.Payload, "repository")
	full := getBool(msg.Payload, "full", true)

	d.sendTaskStart(msg.ID, taskID, message.MsgTypeRunMaintenance)
	if len(repoConfig) > 0 {
		if err := d.connectRepository(repoConfig, password); err != nil {
			d.sendTaskFailed(msg.ID, taskID, err.Error())
			return
		}
	}
	output, err := d.kopia.RunMaintenance(full, password)
	if err != nil {
		d.sendTaskFailed(msg.ID, taskID, err.Error())
		return
	}
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskComplete,
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": message.MsgTypeRunMaintenance,
			"success":   true,
			"result": map[string]interface{}{
				"output": output,
				"full":   full,
			},
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) showPolicy(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	password := getString(msg.Payload, "password", "")
	repoConfig := getMap(msg.Payload, "repository")
	target := getString(msg.Payload, "target", "")

	d.sendTaskStart(msg.ID, taskID, message.MsgTypePolicyShow)
	if len(repoConfig) > 0 {
		if err := d.connectRepository(repoConfig, password); err != nil {
			d.sendTaskFailed(msg.ID, taskID, err.Error())
			return
		}
	}
	output, err := d.kopia.ShowPolicy(target, password)
	if err != nil {
		d.sendTaskFailed(msg.ID, taskID, err.Error())
		return
	}
	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskComplete,
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": message.MsgTypePolicyShow,
			"success":   true,
			"result": map[string]interface{}{
				"policy": output,
				"target": target,
			},
			"timestamp": time.Now(),
		},
	})
}

func (d *Dispatcher) listSnapshotFiles(msg ws.Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	objectID := getString(msg.Payload, "object_id", snapshotID)
	path := getString(msg.Payload, "path", "")
	repoConfig := getMap(msg.Payload, "repository")
	password := getString(msg.Payload, "password", "")

	logger.Debug("Snapshot file browser start", map[string]interface{}{
		"task_id":     taskID,
		"snapshot_id": snapshotID,
		"object_id":   objectID,
		"path":        path,
	})

	if objectID == "" {
		d.sendError(msg.ID, taskID, "object_id is required")
		return
	}

	d.sendTaskStart(msg.ID, taskID, message.MsgTypeListSnapshotFiles)
	if len(repoConfig) > 0 {
		if err := d.connectRepository(repoConfig, password); err != nil {
			d.sendTaskFailed(msg.ID, taskID, err.Error())
			return
		}
	}

	files, err := d.kopia.ListSnapshotFiles(objectID, path, password)
	if err != nil {
		d.sendTaskFailed(msg.ID, taskID, err.Error())
		return
	}

	d.wsClient.Send(ws.Message{
		Type: message.MsgTypeTaskComplete,
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"task_type": message.MsgTypeListSnapshotFiles,
			"success":   true,
			"result": map[string]interface{}{
				"snapshot_id": snapshotID,
				"path":        path,
				"files":       files,
				"count":       len(files),
			},
			"timestamp": time.Now(),
		},
	})
	logger.Debug("Snapshot file browser end", map[string]interface{}{
		"task_id": taskID,
		"count":   len(files),
	})
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

func getStringSlice(m map[string]interface{}, key string) []string {
	if v, ok := m[key]; ok {
		switch items := v.(type) {
		case []string:
			return items
		case []interface{}:
			result := make([]string, 0, len(items))
			for _, item := range items {
				if s, ok := item.(string); ok && strings.TrimSpace(s) != "" {
					result = append(result, strings.TrimSpace(s))
				}
			}
			return result
		}
	}
	return nil
}

func getMap(m map[string]interface{}, key string) map[string]interface{} {
	if v, ok := m[key]; ok {
		if mm, ok := v.(map[string]interface{}); ok {
			return mm
		}
	}
	return nil
}

func copyMap(m map[string]interface{}) map[string]interface{} {
	result := make(map[string]interface{}, len(m))
	for key, value := range m {
		result[key] = value
	}
	return result
}

func safeTaskPrefix(taskID string) string {
	if len(taskID) >= 8 {
		return taskID[:8]
	}
	if taskID == "" {
		return "task"
	}
	return taskID
}

func getSlice(m map[string]interface{}, key string) []interface{} {
	if v, ok := m[key]; ok {
		if s, ok := v.([]interface{}); ok {
			return s
		}
	}
	return nil
}

func calculateS3PrefixUsage(ctx context.Context, endpoint, bucket, prefix, region, urlStyle string, useTLS bool, accessKey, secretKey string) (int64, int64, int64, error) {
	var totalSize int64
	var objectCount int64
	var iterations int64
	const maxObjects int64 = 1000000

	endpoint = strings.TrimRight(strings.TrimSpace(endpoint), "/")
	if !strings.HasPrefix(endpoint, "http://") && !strings.HasPrefix(endpoint, "https://") {
		if useTLS {
			endpoint = "https://" + endpoint
		} else {
			endpoint = "http://" + endpoint
		}
	}

	parsed, err := url.Parse(endpoint)
	if err != nil {
		return totalSize, objectCount, iterations, err
	}
	if parsed.Host == "" {
		return totalSize, objectCount, iterations, fmt.Errorf("invalid S3 endpoint: %s", endpoint)
	}

	bucketLookup := minio.BucketLookupAuto
	if urlStyle == "path" {
		bucketLookup = minio.BucketLookupPath
	} else if urlStyle == "virtual" {
		bucketLookup = minio.BucketLookupDNS
	}

	client, err := minio.New(parsed.Host, &minio.Options{
		Creds:        credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure:       parsed.Scheme == "https",
		Region:       region,
		BucketLookup: bucketLookup,
	})
	if err != nil {
		return totalSize, objectCount, iterations, err
	}

	exists, err := client.BucketExists(ctx, bucket)
	if err != nil {
		return totalSize, objectCount, iterations, err
	}
	if !exists {
		return totalSize, objectCount, iterations, fmt.Errorf("bucket does not exist or is not accessible: %s", bucket)
	}

	objectCh := client.ListObjects(ctx, bucket, minio.ListObjectsOptions{
		Prefix:    prefix,
		Recursive: true,
	})
	for object := range objectCh {
		if object.Err != nil {
			return totalSize, objectCount, iterations, object.Err
		}
		totalSize += object.Size
		objectCount++
		if objectCount%1000 == 0 {
			iterations++
		}
		if objectCount >= maxObjects {
			logger.Warn("S3 object listing reached safety limit", map[string]interface{}{
				"bucket":       bucket,
				"prefix":       prefix,
				"object_count": objectCount,
				"max_objects":  maxObjects,
				"total_size":   totalSize,
			})
			break
		}
	}
	if objectCount > 0 && iterations == 0 {
		iterations = 1
	}

	return totalSize, objectCount, iterations, nil
}

// executeTestStorage executes a storage connectivity test.
func (d *Dispatcher) executeTestStorage(msg ws.Message) {
	// Use payload for unified message format
	if msg.Payload == nil {
		d.sendStorageTestResult(msg.ID, "", nil, "payload is empty")
		return
	}

	taskID := getString(msg.Payload, "task_id", msg.ID)
	storageType := getString(msg.Payload, "storage_type", "nas")
	testWrite := getBool(msg.Payload, "test_write", true)
	repositoryID := getString(msg.Payload, "repository_id", "")
	if storageType != "local" && !d.config.IsSyncProxy() {
		d.sendStorageTestResult(msg.ID, taskID, map[string]interface{}{
			"storage_type":  storageType,
			"repository_id": repositoryID,
			"success":       false,
		}, "test_storage for non-local storage is only available for Sync Proxy")
		return
	}

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
		mountType := getString(msg.Payload, "mount_type", "nfs") // nfs, smb, or cifs
		mountPath := getString(msg.Payload, "mount_path", "")
		mountOptions := getString(msg.Payload, "mount_options", "")
		sourceResourceID := getString(msg.Payload, "source_resource_id", "")

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
		if mountType == "smb" || mountType == "cifs" {
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

		if mountPath == "" {
			var removeAfterUse bool
			var err error
			mountPath, removeAfterUse, err = resolveStorageTestMountPath(taskID, repositoryID, sourceResourceID, "")
			if err != nil {
				d.sendStorageTestResult(msg.ID, taskID, result, err.Error())
				return
			}
			logger.Info("Using storage test mount point", map[string]interface{}{
				"mount_path":         mountPath,
				"source_resource_id": sourceResourceID,
				"repository_id":      repositoryID,
				"remove_after_use":   removeAfterUse,
			})
			if err := os.MkdirAll(mountPath, 0755); err != nil {
				logger.Error("Failed to create temporary mount directory", map[string]interface{}{
					"error": err.Error(),
				})
				d.sendStorageTestResult(msg.ID, taskID, result, fmt.Sprintf("failed to create storage test mount dir: %v", err))
				return
			}
			logger.Debug("Created temporary mount point", map[string]interface{}{
				"mount_path": mountPath,
			})

			logger.Info("Mounting NAS for storage test", map[string]interface{}{
				"server": server,
				"path":   path,
				"target": mountPath,
			})

			var mountErr error
			if mount.IsPathMounted(mountPath) {
				logger.Debug("Reusing already mounted storage test path", map[string]interface{}{
					"mount_path": mountPath,
				})
			} else {
				if mountType == "smb" || mountType == "cifs" {
					username := getString(msg.Payload, "username", "")
					password := getString(msg.Payload, "password", "")
					mountErr = d.mountMgr.MountSMB(server, path, mountPath, username, password, mountOptions)
				} else {
					mountErr = d.mountMgr.MountNFS(server, path, mountPath, mountOptions)
				}
			}

			if mountErr != nil {
				logger.Error("Failed to mount for storage test", map[string]interface{}{
					"error": mountErr.Error(),
				})
				if removeAfterUse {
					if removeErr := safeRemoveMountPointDir(mountPath); removeErr != nil {
						logger.Warn("Failed to remove storage test mount path after mount failure", map[string]interface{}{
							"mount_path": mountPath,
							"error":      removeErr.Error(),
						})
					}
				}
				d.sendStorageTestResult(msg.ID, taskID, result, fmt.Sprintf("mount failed: %v", mountErr))
				return
			}

			logger.Debug("NAS mounted successfully for storage test", nil)

			if removeAfterUse {
				defer func() {
					logger.Debug("Cleaning up temporary storage test mount", map[string]interface{}{
						"mount_path": mountPath,
					})
					if err := d.mountMgr.Unmount(mountPath); err != nil {
						logger.Warn("Failed to unmount temporary storage test path", map[string]interface{}{
							"mount_path": mountPath,
							"error":      err.Error(),
						})
					}
					if err := safeRemoveMountPointDir(mountPath); err != nil {
						logger.Warn("Failed to remove temporary storage test mount path", map[string]interface{}{
							"mount_path": mountPath,
							"error":      err.Error(),
						})
					}
					logger.Debug("Temporary storage test mount cleaned up", nil)
				}()
			}
		}

		if _, err := os.Stat(mountPath); os.IsNotExist(err) {
			logger.Error("Mount path does not exist", map[string]interface{}{
				"mount_path": mountPath,
			})
			d.sendStorageTestResult(msg.ID, taskID, result, fmt.Sprintf("mount path does not exist: %s", mountPath))
			return
		}

		if testWrite {
			logger.Debug("Starting write test", map[string]interface{}{
				"mount_path": mountPath,
			})

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

			if !writeResult.Writable {
				result["write_test"] = map[string]interface{}{
					"writable":    false,
					"write_speed": 0,
					"read_speed":  0,
					"error":       writeResult.Error,
				}
				result["success"] = true
				d.sendStorageTestResult(msg.ID, taskID, result, "")
				return
			}
		}

		// Get space info even when write test is disabled.
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

		result["success"] = true
		logger.Info("Storage test completed successfully", map[string]interface{}{
			"task_id": taskID,
		})
		d.sendStorageTestResult(msg.ID, taskID, result, "")

	case "s3":
		endpoint := getString(msg.Payload, "endpoint", "")
		bucket := getString(msg.Payload, "bucket", "")
		prefix := strings.TrimLeft(getString(msg.Payload, "prefix", ""), "/")
		region := getString(msg.Payload, "region", "us-east-1")
		urlStyle := getString(msg.Payload, "url_style", "virtual")
		useTLS := getBool(msg.Payload, "use_tls", true)
		accessKey := getString(msg.Payload, "access_key", "")
		secretKey := getString(msg.Payload, "secret_key", "")

		if endpoint == "" || bucket == "" || accessKey == "" || secretKey == "" {
			d.sendStorageTestResult(msg.ID, taskID, result, "S3 endpoint, bucket, access key and secret key are required")
			return
		}

		logger.Info("Executing S3 storage test via minio-go on proxy", map[string]interface{}{
			"task_id":      taskID,
			"endpoint":     endpoint,
			"bucket":       bucket,
			"prefix":       prefix,
			"region":       region,
			"url_style":    urlStyle,
			"storage_type": storageType,
		})

		ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
		defer cancel()

		totalSize, objectCount, iterations, err := calculateS3PrefixUsage(ctx, endpoint, bucket, prefix, region, urlStyle, useTLS, accessKey, secretKey)
		if err != nil {
			d.sendStorageTestResult(msg.ID, taskID, result, fmt.Sprintf("S3 test failed: %v", err))
			return
		}

		result["connectivity"] = map[string]interface{}{
			"bucket_accessible": true,
			"list_objects":      true,
		}
		result["endpoint"] = endpoint
		result["bucket"] = bucket
		result["prefix"] = prefix
		result["region"] = region
		result["object_count"] = objectCount
		result["iterations"] = iterations
		result["space_info"] = map[string]interface{}{
			"total_bytes": totalSize,
			"used_bytes":  totalSize,
			"free_bytes":  0,
		}
		result["success"] = true
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

	steps := make([]map[string]interface{}, 0, 8)
	sendProgress := func(progress int, step, statusText, detail string) {
		stepData := map[string]interface{}{
			"step":      step,
			"status":    statusText,
			"message":   detail,
			"progress":  progress,
			"timestamp": time.Now(),
		}
		steps = append(steps, stepData)
		d.wsClient.Send(ws.Message{
			Type: message.MsgTypeTaskProgress,
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":       taskID,
				"task_type":     "init_repository",
				"repository_id": repositoryID,
				"progress":      progress,
				"step":          step,
				"status":        statusText,
				"message":       detail,
				"timestamp":     time.Now(),
			},
		})
	}

	if len(repoConfig) == 0 {
		logger.Error("Repository config is required but empty", nil)
		sendProgress(100, "validate", "failed", "Repository config is required")
		d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, "repository config is required", steps)
		return
	}

	repoType := getString(repoConfig, "type", "filesystem")
	kopiaConfig := copyMap(repoConfig)

	sendProgress(5, "validate", "running", "Validating repository configuration")
	switch repoType {
	case "nas", "nfs":
		server := getString(repoConfig, "server", getString(repoConfig, "nas_server", ""))
		remotePath := getString(repoConfig, "export_path", getString(repoConfig, "nas_path", getString(repoConfig, "path", "")))
		mountType := getString(repoConfig, "mount_type", "nfs")
		mountOptions := getString(repoConfig, "mount_options", "")
		username := getString(repoConfig, "username", "")
		mountPassword := getString(repoConfig, "password", "")

		if server == "" || remotePath == "" {
			sendProgress(100, "validate", "failed", "NAS server and export path are required")
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, "NAS server and export path are required", steps)
			return
		}

		sendProgress(15, "connectivity", "running", "Checking NAS connectivity")
		var connResult *mount.ConnectivityResult
		if mountType == "smb" || mountType == "cifs" {
			connResult = mount.TestSMBConnectivity(server)
		} else {
			connResult = mount.TestNFSConnectivity(server)
		}
		if !connResult.Reachable {
			errMsg := fmt.Sprintf("NAS connectivity test failed: %s", connResult.Error)
			sendProgress(100, "connectivity", "failed", errMsg)
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, errMsg, steps)
			return
		}
		sendProgress(25, "connectivity", "completed", "NAS connectivity check passed")

		mountPath, err := d.resolveStableRepositoryMountPath(repoConfig)
		if err != nil {
			errMsg := fmt.Sprintf("failed to resolve repository mount path: %v", err)
			sendProgress(100, "mount_prepare", "failed", errMsg)
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, errMsg, steps)
			return
		}
		if err := os.MkdirAll(mountPath, 0755); err != nil {
			errMsg := fmt.Sprintf("failed to create repository mount dir: %v", err)
			sendProgress(100, "mount_prepare", "failed", errMsg)
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, errMsg, steps)
			return
		}

		sendProgress(35, "mount", "running", "Mounting NAS to a stable repository path")
		if !mount.IsPathMounted(mountPath) {
			var mountErr error
			if mountType == "smb" || mountType == "cifs" {
				mountErr = d.mountMgr.MountSMB(server, remotePath, mountPath, username, mountPassword, mountOptions)
			} else {
				mountErr = d.mountMgr.MountNFS(server, remotePath, mountPath, mountOptions)
			}
			if mountErr != nil {
				errMsg := fmt.Sprintf("mount failed: %v", mountErr)
				sendProgress(100, "mount", "failed", errMsg)
				d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, errMsg, steps)
				return
			}
		}
		sendProgress(50, "mount", "completed", "NAS mounted successfully")

		sendProgress(60, "write_test", "running", "Testing repository write permission")
		writeResult := mount.TestWriteSimple(mountPath)
		if !writeResult.Writable {
			errMsg := fmt.Sprintf("write test failed: %s", writeResult.Error)
			sendProgress(100, "write_test", "failed", errMsg)
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, errMsg, steps)
			return
		}
		sendProgress(70, "write_test", "completed", "Write test passed")

		kopiaConfig["type"] = "filesystem"
		kopiaConfig["path"] = mountPath
		kopiaConfig["mounted_path"] = mountPath

	case "local":
		localPath := getString(repoConfig, "path", "")
		if localPath == "" {
			sendProgress(100, "validate", "failed", "Local repository path is required")
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, "Local repository path is required", steps)
			return
		}
		if _, err := os.Stat(localPath); err != nil {
			errMsg := fmt.Sprintf("local path is not accessible: %v", err)
			sendProgress(100, "validate", "failed", errMsg)
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, errMsg, steps)
			return
		}
		sendProgress(60, "write_test", "running", "Testing local repository write permission")
		writeResult := mount.TestWriteSimple(localPath)
		if !writeResult.Writable {
			errMsg := fmt.Sprintf("write test failed: %s", writeResult.Error)
			sendProgress(100, "write_test", "failed", errMsg)
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, errMsg, steps)
			return
		}
		sendProgress(70, "write_test", "completed", "Write test passed")
		kopiaConfig["type"] = "filesystem"

	case "s3":
		bucket := getString(repoConfig, "bucket", "")
		accessKey := getString(repoConfig, "access_key", "")
		secretKey := getString(repoConfig, "secret_key", "")
		if bucket == "" || accessKey == "" || secretKey == "" {
			errMsg := "S3 bucket, access key and secret key are required"
			sendProgress(100, "validate", "failed", errMsg)
			d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, errMsg, steps)
			return
		}
		sendProgress(70, "validate", "completed", "S3 repository configuration validated")
	}

	sendProgress(80, "existing_check", "running", "Checking whether Kopia repository already exists")
	if err := d.kopia.ConnectRepo(kopiaConfig, password); err == nil {
		result := &kopia.CreateRepoResult{
			RepositoryID:  repositoryID,
			Path:          getString(kopiaConfig, "path", ""),
			Output:        "repository already initialized and password verified",
			AlreadyExists: true,
			Steps:         steps,
			CreatedAt:     time.Now(),
		}
		sendProgress(100, "existing_check", "completed", "Repository already exists and password is valid")
		d.sendRepoInitResult(msg.ID, taskID, repositoryID, result, "")
		return
	}

	// Execute repository creation
	sendProgress(85, "initialize", "running", "Creating Kopia repository")
	logger.Debug("Creating Kopia repository...", nil)
	result, err := d.kopia.CreateRepo(kopiaConfig, password)
	if err != nil {
		logger.Error("Failed to create repository", map[string]interface{}{
			"error": err.Error(),
		})
		sendProgress(100, "initialize", "failed", err.Error())
		d.sendRepoInitResult(msg.ID, taskID, repositoryID, nil, err.Error(), steps)
		return
	}
	result.Steps = steps

	logger.Debug("Repository created successfully", map[string]interface{}{
		"repository_id": result.RepositoryID,
		"path":          result.Path,
		"created_at":    result.CreatedAt,
	})

	sendProgress(100, "initialize", "completed", "Kopia repository initialized successfully")
	d.sendRepoInitResult(msg.ID, taskID, repositoryID, result, "")

	logger.Debug("Init repository task end", nil)
}

// sendRepoInitResult sends repository initialization result to server
func (d *Dispatcher) sendRepoInitResult(msgID, taskID, repositoryID string, result *kopia.CreateRepoResult, errMsg string, stepHistory ...[]map[string]interface{}) {
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
		fields["already_exists"] = result.AlreadyExists
	}
	logger.Debug("Sending repository init result", fields)

	if errMsg != "" {
		resultPayload := map[string]interface{}{}
		if len(stepHistory) > 0 {
			resultPayload["steps"] = stepHistory[0]
		}
		d.wsClient.Send(ws.Message{
			Type: message.MsgTypeInitRepositoryResult,
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":       taskID,
				"repository_id": repositoryID,
				"success":       false,
				"error":         errMsg,
				"result":        resultPayload,
				"timestamp":     time.Now(),
			},
		})
	} else {
		d.wsClient.Send(ws.Message{
			Type: message.MsgTypeInitRepositoryResult,
			ID:   msgID,
			Payload: map[string]interface{}{
				"task_id":        taskID,
				"success":        true,
				"repository_id":  result.RepositoryID,
				"path":           result.Path,
				"created_at":     result.CreatedAt,
				"already_exists": result.AlreadyExists,
				"result": map[string]interface{}{
					"repository_id":  result.RepositoryID,
					"path":           result.Path,
					"output":         result.Output,
					"already_exists": result.AlreadyExists,
					"steps":          result.Steps,
					"created_at":     result.CreatedAt,
				},
				"timestamp": time.Now(),
			},
		})
	}
	logger.Debug("Repository init result sent", nil)
}
