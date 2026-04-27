package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
)

// Config holds proxy configuration
type Config struct {
	ControlURL   string
	NodeID       string
	Token        string
	KopiaPath    string
	RepoPath     string
	LogLevel     string
	ReconnectDelay time.Duration
}

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
	tasks       map[string]*TaskStatus
	tasksMutex  sync.RWMutex
	stopCh      chan struct{}
	connected   bool
}

// NewProxy creates a new proxy instance
func NewProxy(cfg *Config) *Proxy {
	return &Proxy{
		config: cfg,
		tasks:  make(map[string]*TaskStatus),
		stopCh: make(chan struct{}),
	}
}

// Connect establishes WebSocket connection to control plane
func (p *Proxy) Connect() error {
	url := fmt.Sprintf("%s%s", p.config.ControlURL, p.config.NodeID)
	
	headers := make(map[string][]string)
	if p.config.Token != "" {
		headers["Authorization"] = []string{"Bearer " + p.config.Token}
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

	log.Printf("Connected to control plane: %s", url)
	
	// Send registration message
	p.Send(Message{
		Type: "register",
		Payload: map[string]interface{}{
			"node_id":    p.config.NodeID,
			"version":    "1.0.0",
			"hostname":   getHostname(),
			"platform":   getPlatform(),
			"kopia_path": p.config.KopiaPath,
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
	log.Println("Disconnected from control plane")
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
				log.Printf("Read error: %v", err)
				p.handleDisconnect()
				continue
			}

			var msg Message
			if err := json.Unmarshal(message, &msg); err != nil {
				log.Printf("JSON parse error: %v", err)
				continue
			}

			go p.handleMessage(msg)
		}
	}
}

// handleMessage processes incoming messages
func (p *Proxy) handleMessage(msg Message) {
	log.Printf("Received message: type=%s, id=%s", msg.Type, msg.ID)

	switch msg.Type {
	case "ping":
		p.Send(Message{Type: "pong", ID: msg.ID})

	case "backup":
		go p.executeBackup(msg)

	case "restore":
		go p.executeRestore(msg)

	case "mount":
		go p.executeMount(msg)

	case "status":
		p.reportStatus(msg.ID)

	case "cancel":
		p.cancelTask(msg)

	default:
		log.Printf("Unknown message type: %s", msg.Type)
	}
}

// executeBackup executes a backup task
func (p *Proxy) executeBackup(msg Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	sourcePath := getString(msg.Payload, "source_path", "")
	repoPath := getString(msg.Payload, "repo_path", p.config.RepoPath)
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	
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
			"task_id":  taskID,
			"task_type": "backup",
			"start_time": status.StartTime,
		},
	})

	// Execute Kopia snapshot create command
	args := []string{"snapshot", "create", sourcePath}
	if repoPath != "" {
		args = append(args, "--repo", repoPath)
	}
	if snapshotID != "" {
		args = append(args, "--hostname", snapshotID)
	}

	log.Printf("Executing: kopia %s", strings.Join(args, " "))
	
	cmd := exec.Command(p.config.KopiaPath, args...)
	cmd.Env = append(os.Environ(), 
		"KOPIA_PASSWORD="+getString(msg.Payload, "password", ""),
	)
	
	output, err := cmd.CombinedOutput()
	
	p.tasksMutex.Lock()
	defer p.tasksMutex.Unlock()
	
	if err != nil {
		status.Status = "failed"
		status.Message = fmt.Sprintf("Backup failed: %v", err)
		status.EndTime = time.Now()
		
		p.Send(Message{
			Type: "task_failed",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":  taskID,
				"error":    err.Error(),
				"output":   string(output),
				"end_time": status.EndTime,
			},
		})
	} else {
		status.Status = "completed"
		status.Progress = 100
		status.Message = "Backup completed successfully"
		status.EndTime = time.Now()
		
		p.Send(Message{
			Type: "task_completed",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":    taskID,
				"output":     string(output),
				"end_time":   status.EndTime,
				"duration":   status.EndTime.Sub(status.StartTime).Seconds(),
			},
		})
	}
}

// executeRestore executes a restore task
func (p *Proxy) executeRestore(msg Message) {
	taskID := getString(msg.Payload, "task_id", msg.ID)
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	targetPath := getString(msg.Payload, "target_path", "")
	repoPath := getString(msg.Payload, "repo_path", p.config.RepoPath)
	
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
			"task_id":   taskID,
			"task_type": "restore",
			"start_time": status.StartTime,
		},
	})

	// Execute Kopia restore command
	args := []string{"snapshot", "restore", snapshotID, targetPath}
	if repoPath != "" {
		args = append(args, "--repo", repoPath)
	}

	log.Printf("Executing: kopia %s", strings.Join(args, " "))
	
	cmd := exec.Command(p.config.KopiaPath, args...)
	cmd.Env = append(os.Environ(), 
		"KOPIA_PASSWORD="+getString(msg.Payload, "password", ""),
	)
	
	output, err := cmd.CombinedOutput()
	
	p.tasksMutex.Lock()
	defer p.tasksMutex.Unlock()
	
	if err != nil {
		status.Status = "failed"
		status.Message = fmt.Sprintf("Restore failed: %v", err)
		status.EndTime = time.Now()
		
		p.Send(Message{
			Type: "task_failed",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":  taskID,
				"error":    err.Error(),
				"output":   string(output),
				"end_time": status.EndTime,
			},
		})
	} else {
		status.Status = "completed"
		status.Progress = 100
		status.Message = "Restore completed successfully"
		status.EndTime = time.Now()
		
		p.Send(Message{
			Type: "task_completed",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":    taskID,
				"output":     string(output),
				"end_time":   status.EndTime,
				"duration":   status.EndTime.Sub(status.StartTime).Seconds(),
			},
		})
	}
}

// executeMount executes a mount operation
func (p *Proxy) executeMount(msg Message) {
	snapshotID := getString(msg.Payload, "snapshot_id", "")
	mountPath := getString(msg.Payload, "mount_path", "/mnt/kopia")
	repoPath := getString(msg.Payload, "repo_path", p.config.RepoPath)

	if snapshotID == "" {
		p.sendError(msg.ID, "", "snapshot_id is required")
		return
	}

	// Execute Kopia mount command
	args := []string{"mount", snapshotID, mountPath}
	if repoPath != "" {
		args = append(args, "--repo", repoPath)
	}

	cmd := exec.Command(p.config.KopiaPath, args...)
	cmd.Env = append(os.Environ(), 
		"KOPIA_PASSWORD="+getString(msg.Payload, "password", ""),
	)
	
	if err := cmd.Start(); err != nil {
		p.sendError(msg.ID, "", fmt.Sprintf("Mount failed: %v", err))
		return
	}

	p.Send(Message{
		Type: "mount_started",
		ID:   msg.ID,
		Payload: map[string]interface{}{
			"snapshot_id": snapshotID,
			"mount_path":  mountPath,
			"pid":         cmd.Process.Pid,
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
			"node_id":     p.config.NodeID,
			"connected":   p.connected,
			"active_tasks": len(tasks),
			"tasks":       tasks,
			"hostname":    getHostname(),
			"platform":    getPlatform(),
		},
	})
}

// cancelTask cancels a running task
func (p *Proxy) cancelTask(msg Message) {
	taskID := getString(msg.Payload, "task_id", "")
	
	p.tasksMutex.Lock()
	defer p.tasksMutex.Unlock()
	
	if status, exists := p.tasks[taskID]; exists {
		status.Status = "cancelled"
		status.Message = "Task cancelled by user"
		status.EndTime = time.Now()
		
		p.Send(Message{
			Type: "task_cancelled",
			ID:   msg.ID,
			Payload: map[string]interface{}{
				"task_id":  taskID,
				"end_time": status.EndTime,
			},
		})
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
		log.Printf("Attempting to reconnect in %v...", p.config.ReconnectDelay)
		time.Sleep(p.config.ReconnectDelay)
		
		if err := p.Connect(); err != nil {
			log.Printf("Reconnect failed: %v", err)
			continue
		}
		
		break
	}
}

// heartbeat sends periodic heartbeats
func (p *Proxy) heartbeat() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-p.stopCh:
			return
		case <-ticker.C:
			p.Send(Message{
				Type: "heartbeat",
				Payload: map[string]interface{}{
					"node_id":   p.config.NodeID,
					"timestamp": time.Now(),
					"status":    "healthy",
				},
			})
		}
	}
}

// Run starts the proxy
func (p *Proxy) Run() error {
	// Connect to control plane
	if err := p.Connect(); err != nil {
		return err
	}

	// Start heartbeat goroutine
	go p.heartbeat()

	// Listen for messages
	p.Listen()

	return nil
}

// Stop stops the proxy
func (p *Proxy) Stop() {
	close(p.stopCh)
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

func getHostname() string {
	hostname, err := os.Hostname()
	if err != nil {
		return "unknown"
	}
	return hostname
}

func getPlatform() string {
	return fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)
}

func main() {
	// Parse command line flags
	controlURL := flag.String("control", os.Getenv("CONTROL_URL"), "Control plane WebSocket URL")
	nodeID := flag.String("node", os.Getenv("NODE_ID"), "Node ID")
	token := flag.String("token", os.Getenv("TOKEN"), "Authentication token")
	kopiaPath := flag.String("kopia", os.Getenv("KOPIA_PATH"), "Path to Kopia binary")
	repoPath := flag.String("repo", os.Getenv("REPO_PATH"), "Default repository path")
	logLevel := flag.String("log", os.Getenv("LOG_LEVEL"), "Log level (debug, info, warn, error)")
	flag.Parse()

	// Set defaults
	if *controlURL == "" {
		*controlURL = "ws://localhost:8000/ws/node/"
	}
	if *nodeID == "" {
		*nodeID = "proxy-" + uuid.New().String()[:8]
	}
	if *kopiaPath == "" {
		*kopiaPath = "kopia"
	}
	if *logLevel == "" {
		*logLevel = "info"
	}

	// Create config
	cfg := &Config{
		ControlURL:     *controlURL,
		NodeID:         *nodeID,
		Token:          *token,
		KopiaPath:      *kopiaPath,
		RepoPath:       *repoPath,
		LogLevel:       *logLevel,
		ReconnectDelay: 5 * time.Second,
	}

	// Create proxy
	proxy := NewProxy(cfg)

	// Handle shutdown signals
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	
	go func() {
		<-sigCh
		log.Println("Received shutdown signal")
		proxy.Stop()
		os.Exit(0)
	}()

	// Run proxy
	log.Printf("Starting HyperFileLens Proxy (node: %s)", cfg.NodeID)
	log.Printf("Control plane: %s", cfg.ControlURL)
	log.Printf("Kopia path: %s", cfg.KopiaPath)
	
	if err := proxy.Run(); err != nil {
		log.Fatalf("Proxy error: %v", err)
	}
}
