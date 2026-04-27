package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
)

// Message represents a message from control plane
type Message struct {
	Type    string                 `json:"type"`
	ID      string                 `json:"id"`
	Payload map[string]interface{} `json:"payload"`
}

// Response represents a response to control plane
type Response struct {
	Type    string      `json:"type"`
	ID      string      `json:"id"`
	Success bool        `json:"success"`
	Result  interface{} `json:"result,omitempty"`
	Error   string      `json:"error,omitempty"`
}

// TaskStatus represents task execution status
type TaskStatus struct {
	TaskID    string    `json:"task_id"`
	Status    string    `json:"status"`
	Progress  int       `json:"progress"`
	Message   string    `json:"message"`
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time,omitempty"`
}

// Proxy represents the proxy agent
type Proxy struct {
	config      *Config
	conn        *websocket.Conn
	connMutex   sync.Mutex
	nodeClient  *NodeClient
	kopia       *KopiaExecutor
	tasks       map[string]*TaskStatus
	tasksMutex  sync.RWMutex
	stopCh      chan struct{}
	connected   bool
}

// NewProxy creates a new proxy instance
func NewProxy(cfg *Config) *Proxy {
	return &Proxy{
		config:     cfg,
		nodeClient: NewNodeClient(cfg),
		kopia:      NewKopiaExecutor(cfg),
		tasks:      make(map[string]*TaskStatus),
		stopCh:     make(chan struct{}),
	}
}

// Connect establishes WebSocket connection to control plane
func (p *Proxy) Connect() error {
	url := p.config.GetWebSocketURL()
	
	headers := make(map[string][]string)
	if p.config.Server.APIToken != "" {
		headers["Authorization"] = []string{"Token " + p.config.Server.APIToken}
	}

	dialer := websocket.DefaultDialer
	conn, _, err := dialer.Dial(url, headers)
	if err != nil {
		return fmt.Errorf("failed to connect to control plane: %w", err)
	}

	p.connMutex.Lock()
	p.conn = conn
	p.connected = true
	p.connMutex.Unlock()

	logInfo("Connected to control plane: %s", url)

	// Send registration message
	p.Send(Message{
		Type: "register",
		Payload: map[string]interface{}{
			"node_id":    p.config.NodeID,
			"version":    p.config.Version,
			"hostname":   p.config.Agent.Hostname,
			"platform":   getPlatform(),
			"kopia_path": p.config.Backup.KopiaPath,
			"agent_type": p.config.Agent.Type,
		},
	})

	return nil
}

// Disconnect closes WebSocket connection
func (p *Proxy) Disconnect() {
	p.connMutex.Lock()
	defer p.connMutex.Unlock()

	if p.conn != nil {
		p.conn.Close()
		p.conn = nil
	}
	p.connected = false
	logInfo("Disconnected from control plane")
}

// Send sends a message to control plane
func (p *Proxy) Send(msg Message) error {
	p.connMutex.Lock()
	defer p.connMutex.Unlock()

	if p.conn == nil {
		return fmt.Errorf("not connected")
	}

	return p.conn.WriteJSON(msg)
}

// Listen listens for messages from control plane
func (p *Proxy) Listen() {
	for {
		select {
		case <-p.stopCh:
			return
		default:
			p.connMutex.Lock()
			conn := p.conn
			p.connMutex.Unlock()

			if conn == nil {
				time.Sleep(1 * time.Second)
				continue
			}

			_, message, err := conn.ReadMessage()
			if err != nil {
				logError("Read error: %v", err)
				p.handleDisconnect()
				continue
			}

			var msg Message
			if err := json.Unmarshal(message, &msg); err != nil {
				logError("JSON parse error: %v", err)
				continue
			}

			go p.handleMessage(msg)
		}
	}
}

// handleMessage processes incoming messages
func (p *Proxy) handleMessage(msg Message) {
	logInfo("Received message: type=%s, id=%s", msg.Type, msg.ID)

	switch msg.Type {
	case "ping":
		p.Send(Message{Type: "pong", ID: msg.ID})

	case "backup", "backup_task":
		go p.executeBackup(msg)

	case "restore", "recovery_task":
		go p.executeRestore(msg)

	case "mount":
		go p.executeMount(msg)

	case "list_snapshots":
		go p.listSnapshots(msg)

	case "list_contents":
		go p.listContents(msg)

	case "status":
		p.reportStatus(msg.ID)

	case "cancel":
		p.cancelTask(msg)

	case "verify_repo":
		go p.verifyRepository(msg)

	default:
		logInfo("Unknown message type: %s", msg.Type)
	}
}

// executeBackup executes a backup task
func (p *Proxy) executeBackup(msg Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	sourcePath := getString(msg.Payload, "source_path", "")
	repoPath := getString(msg.Payload, "repo_path", "")
	password := getString(msg.Payload, "password", "")
	snapshotPrefix := getString(msg.Payload, "snapshot_prefix", "hyperfilelens")

	if sourcePath == "" {
		p.sendError(msg.ID, taskID, "source_path is required")
		return
	}

	// Initialize task status
	status := &TaskStatus{
		TaskID:    taskID,
		Status:    "running",
		Progress:  0,
		Message:   "Starting backup",
		StartTime: time.Now(),
	}
	p.tasksMutex.Lock()
	p.tasks[taskID] = status
	p.tasksMutex.Unlock()

	// Send start notification
	p.Send(Message{
		Type: "task_start",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":    taskID,
			"task_type":  "backup",
			"start_time": status.StartTime,
		},
	})

	// Execute Kopia backup
	tags := map[string]string{
		"task_id": taskID,
		"prefix":  snapshotPrefix,
	}
	
	result, err := p.kopia.CreateSnapshot(taskID, sourcePath, repoPath, password, tags)

	p.tasksMutex.Lock()
	defer p.tasksMutex.Unlock()

	if err != nil {
		status.Status = "failed"
		status.Message = fmt.Sprintf("Backup failed: %v", err)
		status.EndTime = time.Now()

		// Report error to control server
		p.nodeClient.ReportTaskError(taskID, err.Error())

		p.Send(Message{
			Type: "task_failed",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":  taskID,
				"error":    err.Error(),
				"output":   result.Output,
				"end_time": status.EndTime,
			},
		})
	} else {
		status.Status = "completed"
		status.Progress = 100
		status.Message = "Backup completed successfully"
		status.EndTime = time.Now()

		// Report success to control server
		p.nodeClient.ReportTaskResult(taskID, map[string]interface{}{
			"snapshot_id":     result.SnapshotID,
			"source_path":     result.SourcePath,
			"files_processed": result.FilesProcessed,
			"bytes_processed": result.BytesProcessed,
			"duration":        result.Duration,
		})

		p.Send(Message{
			Type: "task_completed",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":     taskID,
				"snapshot_id": result.SnapshotID,
				"output":      result.Output,
				"end_time":    status.EndTime,
				"duration":    result.Duration,
			},
		})
	}
}

// executeRestore executes a restore task
func (p *Proxy) executeRestore(msg Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	targetPath := getString(msg.Payload, "target_path", "")
	repoPath := getString(msg.Payload, "repo_path", "")
	password := getString(msg.Payload, "password", "")
	overwrite := getBool(msg.Payload, "overwrite", false)

	if snapshotID == "" || targetPath == "" {
		p.sendError(msg.ID, taskID, "snapshot_id and target_path are required")
		return
	}

	status := &TaskStatus{
		TaskID:    taskID,
		Status:    "running",
		Progress:  0,
		Message:   "Starting restore",
		StartTime: time.Now(),
	}
	p.tasksMutex.Lock()
	p.tasks[taskID] = status
	p.tasksMutex.Unlock()

	p.Send(Message{
		Type: "task_start",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"task_id":    taskID,
			"task_type":  "restore",
			"start_time": status.StartTime,
		},
	})

	// Execute Kopia restore
	result, err := p.kopia.RestoreSnapshot(taskID, snapshotID, targetPath, repoPath, password, overwrite)

	p.tasksMutex.Lock()
	defer p.tasksMutex.Unlock()

	if err != nil {
		status.Status = "failed"
		status.Message = fmt.Sprintf("Restore failed: %v", err)
		status.EndTime = time.Now()

		p.nodeClient.ReportTaskError(taskID, err.Error())

		p.Send(Message{
			Type: "task_failed",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":  taskID,
				"error":    err.Error(),
				"output":   result.Output,
				"end_time": status.EndTime,
			},
		})
	} else {
		status.Status = "completed"
		status.Progress = 100
		status.Message = "Restore completed successfully"
		status.EndTime = time.Now()

		p.nodeClient.ReportTaskResult(taskID, map[string]interface{}{
			"snapshot_id":  result.SnapshotID,
			"target_path":  result.TargetPath,
			"restore_type": result.RestoreType,
			"duration":     result.Duration,
		})

		p.Send(Message{
			Type: "task_completed",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":     taskID,
				"snapshot_id": result.SnapshotID,
				"target_path": result.TargetPath,
				"output":      result.Output,
				"end_time":    status.EndTime,
				"duration":    result.Duration,
			},
		})
	}
}

// executeMount executes a mount operation
func (p *Proxy) executeMount(msg Message) {
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	mountPath := getString(msg.Payload, "mount_path", "/mnt/kopia")
	repoPath := getString(msg.Payload, "repo_path", "")
	password := getString(msg.Payload, "password", "")

	if snapshotID == "" {
		p.sendError(msg.ID, "", "snapshot_id is required")
		return
	}

	pid, err := p.kopia.MountSnapshot(snapshotID, mountPath, repoPath, password)
	if err != nil {
		p.sendError(msg.ID, "", fmt.Sprintf("Mount failed: %v", err))
		return
	}

	p.Send(Message{
		Type: "mount_started",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"snapshot_id": snapshotID,
			"mount_path":  mountPath,
			"pid":         pid,
		},
	})
}

// listSnapshots lists available snapshots
func (p *Proxy) listSnapshots(msg Message) {
	repoPath := getString(msg.Payload, "repo_path", "")
	password := getString(msg.Payload, "password", "")
	sourcePath := getString(msg.Payload, "source_path", "")

	snapshots, err := p.kopia.ListSnapshots(repoPath, password, sourcePath)
	if err != nil {
		p.sendError(msg.ID, "", fmt.Sprintf("Failed to list snapshots: %v", err))
		return
	}

	p.Send(Message{
		Type: "snapshot_list",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"snapshots": snapshots,
		},
	})
}

// listContents lists contents of a snapshot
func (p *Proxy) listContents(msg Message) {
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	repoPath := getString(msg.Payload, "repo_path", "")
	password := getString(msg.Payload, "password", "")
	recursive := getBool(msg.Payload, "recursive", true)

	if snapshotID == "" {
		p.sendError(msg.ID, "", "snapshot_id is required")
		return
	}

	files, err := p.kopia.GetSnapshotContents(snapshotID, repoPath, password, recursive)
	if err != nil {
		p.sendError(msg.ID, "", fmt.Sprintf("Failed to list contents: %v", err))
		return
	}

	p.Send(Message{
		Type: "content_list",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"snapshot_id": snapshotID,
			"files":       files,
		},
	})
}

// verifyRepository verifies repository connectivity
func (p *Proxy) verifyRepository(msg Message) {
	repoPath := getString(msg.Payload, "repo_path", "")
	password := getString(msg.Payload, "password", "")

	err := p.kopia.VerifyRepository(repoPath, password)
	if err != nil {
		p.Send(Message{
			Type: "repo_verification",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"success": false,
				"error":   err.Error(),
			},
		})
		return
	}

	p.Send(Message{
		Type: "repo_verification",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"success": true,
		},
	})
}

// reportStatus reports current status
func (p *Proxy) reportStatus(msgID string) {
	p.tasksMutex.RLock()
	tasks := make([]map[string]interface{}, 0)
	for _, status := range p.tasks {
		tasks = append(tasks, map[string]interface{}{
			"task_id":    status.TaskID,
			"status":     status.Status,
			"progress":   status.Progress,
			"message":    status.Message,
			"start_time": status.StartTime,
			"end_time":   status.EndTime,
		})
	}
	p.tasksMutex.RUnlock()

	p.Send(Message{
		Type: "status_report",
		ID:   msgID,
		Payload: map[string]interface{}{
			"node_id":      p.config.NodeID,
			"connected":    p.connected,
			"active_tasks": len(tasks),
			"tasks":        tasks,
			"hostname":     p.config.Agent.Hostname,
			"platform":     getPlatform(),
			"kopia_version": p.kopia.GetVersion(),
			"agent_type":   p.config.Agent.Type,
		},
	})
}

// cancelTask cancels a running task
func (p *Proxy) cancelTask(msg Message) {
	taskID := getString(msg.Payload, "task_id", "")

	// Try to cancel via Kopia executor
	cancelled := p.kopia.CancelTask(taskID)

	p.tasksMutex.Lock()
	defer p.tasksMutex.Unlock()

	if status, exists := p.tasks[taskID]; exists || cancelled {
		if status != nil {
			status.Status = "cancelled"
			status.Message = "Task cancelled by user"
			status.EndTime = time.Now()
		}

		p.Send(Message{
			Type: "task_cancelled",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":  taskID,
				"end_time": time.Now(),
			},
		})
	} else {
		p.sendError(msg.ID, taskID, "task not found or cannot be cancelled")
	}
}

// sendError sends an error response
func (p *Proxy) sendError(msgID, taskID, errMsg string) {
	p.Send(Message{
		Type: "error",
		ID:   msgID,
		Payload: map[string]interface{}{
			"task_id": taskID,
			"error":   errMsg,
		},
	})
}

// handleDisconnect handles disconnection
func (p *Proxy) handleDisconnect() {
	p.Disconnect()

	// Reconnect with backoff
	for {
		logInfo("Attempting to reconnect in %v...", p.config.Server.ReconnectDelay)
		time.Sleep(p.config.Server.ReconnectDelay)

		if err := p.Connect(); err != nil {
			logError("Reconnect failed: %v", err)
			continue
		}

		break
	}
}

// heartbeat sends periodic heartbeats
func (p *Proxy) heartbeat() {
	ticker := time.NewTicker(p.config.Server.HeartbeatInterval)
	defer ticker.Stop()

	for {
		select {
		case <-p.stopCh:
			return
		case <-ticker.C:
			p.Send(Message{
				Type: "heartbeat",
				Payload: map[string]interface{}{
					"node_id":     p.config.NodeID,
					"timestamp":   time.Now(),
					"status":      "healthy",
					"active_tasks": len(p.tasks),
				},
			})
			
			// Also update status via API
			p.nodeClient.UpdateStatus("online", map[string]interface{}{
				"active_tasks": len(p.tasks),
			})
		}
	}
}

// taskPolling polls for pending tasks
func (p *Proxy) taskPolling() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-p.stopCh:
			return
		case <-ticker.C:
			tasks, err := p.nodeClient.GetPendingTasks()
			if err != nil {
				logDebug("Failed to get pending tasks: %v", err)
				continue
			}

			for _, task := range tasks {
				taskType := getString(task, "type", "")
				taskID := getString(task, "id", "")
				
				if taskType == "" || taskID == "" {
					continue
				}

				// Create message from task
				msg := Message{
					Type:    taskType + "_task",
					ID:      taskID,
					Payload: task,
				}

				go p.handleMessage(msg)
			}
		}
	}
}

// Run starts the proxy
func (p *Proxy) Run() error {
	// Check Kopia installation
	if !p.kopia.CheckInstalled() {
		logError("Kopia is not installed or not accessible at: %s", p.config.Backup.KopiaPath)
		return fmt.Errorf("kopia not found")
	}
	
	logInfo("Kopia version: %s", p.kopia.GetVersion())

	// Register with control server
	nodeID, err := p.nodeClient.Register()
	if err != nil {
		logError("Failed to register with control server: %v", err)
		// Continue anyway, WebSocket connection might work
	} else {
		p.config.NodeID = nodeID
	}

	// Connect to WebSocket
	if err := p.Connect(); err != nil {
		return err
	}

	// Start heartbeat goroutine
	go p.heartbeat()

	// Start task polling goroutine
	go p.taskPolling()

	// Listen for messages
	p.Listen()

	return nil
}

// Stop stops the proxy
func (p *Proxy) Stop() {
	close(p.stopCh)
	p.nodeClient.Unregister()
	p.nodeClient.Close()
	p.Disconnect()
}

// Helper functions

func getString(m map[string]interface{}, key, defaultValue string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return defaultValue
}

func getBool(m map[string]interface{}, key string, defaultValue bool) bool {
	if v, ok := m[key]; ok {
		if b, ok := v.(bool); ok {
			return b
		}
	}
	return defaultValue
}

func main() {
	// Parse command line flags
	configPath := flag.String("config", os.Getenv("CONFIG_PATH"), "Path to config file")
	controlURL := flag.String("control", os.Getenv("CONTROL_URL"), "Control plane URL")
	nodeID := flag.String("node", os.Getenv("NODE_ID"), "Node ID")
	token := flag.String("token", os.Getenv("API_TOKEN"), "Authentication token")
	kopiaPath := flag.String("kopia", os.Getenv("KOPIA_PATH"), "Path to Kopia binary")
	showVersion := flag.Bool("version", false, "Show version information")
	flag.Parse()

	if *showVersion {
		fmt.Println("HyperFileLens Proxy v1.0.0")
		fmt.Println("Platform:", getPlatform())
		return
	}

	// Load configuration
	cfg, err := LoadConfig(*configPath)
	if err != nil {
		logError("Failed to load config: %v", err)
		os.Exit(1)
	}

	// Override with command line flags
	if *controlURL != "" {
		cfg.Server.URL = *controlURL
	}
	if *nodeID != "" {
		cfg.NodeID = *nodeID
	}
	if *token != "" {
		cfg.Server.APIToken = *token
	}
	if *kopiaPath != "" {
		cfg.Backup.KopiaPath = *kopiaPath
	}

	// Generate node ID if not set
	if cfg.NodeID == "" {
		cfg.NodeID = "proxy-" + uuid.New().String()[:8]
	}

	// Ensure directories exist
	if err := cfg.EnsureDataDir(); err != nil {
		logError("Failed to create data directories: %v", err)
	}

	// Create proxy
	proxy := NewProxy(cfg)

	// Handle shutdown signals
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigCh
		logInfo("Received shutdown signal")
		proxy.Stop()
		os.Exit(0)
	}()

	// Run proxy
	logInfo("Starting HyperFileLens Proxy v%s", cfg.Version)
	logInfo("Node ID: %s", cfg.NodeID)
	logInfo("Control plane: %s", cfg.Server.URL)
	logInfo("Kopia path: %s", cfg.Backup.KopiaPath)
	logInfo("Agent type: %s", cfg.Agent.Type)

	if err := proxy.Run(); err != nil {
		logError("Proxy error: %v", err)
		os.Exit(1)
	}
}
