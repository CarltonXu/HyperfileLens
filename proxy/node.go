package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"runtime"
	"time"
)

// NodeClient handles communication with the control server
type NodeClient struct {
	config  *Config
	client  *http.Client
	nodeID  string
	apiBase string
}

// NodeRegistration represents registration request payload
type NodeRegistration struct {
	Name         string                 `json:"name"`
	Type         string                 `json:"type"`
	Hostname     string                 `json:"hostname"`
	IPAddress    string                 `json:"ip_address"`
	Port         int                    `json:"port"`
	Capabilities map[string]interface{} `json:"capabilities"`
	Version      string                 `json:"version"`
}

// NodeResponse represents node API response
type NodeResponse struct {
	NodeID string                 `json:"node_id"`
	ID     string                 `json:"id"`
	Status string                 `json:"status"`
	Error  string                 `json:"error,omitempty"`
}

// TaskResponse represents task API response
type TaskResponse struct {
	TaskID string                 `json:"task_id"`
	ID     string                 `json:"id"`
	Status string                 `json:"status"`
	Result map[string]interface{} `json:"result,omitempty"`
	Error  string                 `json:"error,omitempty"`
}

// NewNodeClient creates a new node client
func NewNodeClient(cfg *Config) *NodeClient {
	return &NodeClient{
		config:  cfg,
		apiBase: cfg.GetAPIBase(),
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Register registers this node with the control server
func (n *NodeClient) Register() (string, error) {
	logInfo("Registering node with server: %s", n.config.Server.URL)

	payload := NodeRegistration{
		Name:      n.config.Agent.Name,
		Type:      n.config.Agent.Type,
		Hostname:  n.config.Agent.Hostname,
		IPAddress: n.getIPAddress(),
		Port:      9090,
		Capabilities: map[string]interface{}{
			"backup":         true,
			"recovery":       true,
			"compression":    n.config.Performance.Compression,
			"max_concurrent": n.config.Backup.MaxConcurrentBackups,
			"platform":       getPlatform(),
			"kopia_version":  n.getKopiaVersion(),
		},
		Version: n.config.Version,
	}

	// Use name if set, otherwise use hostname
	if payload.Name == "" {
		payload.Name = payload.Hostname
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("failed to marshal registration: %w", err)
	}

	req, err := http.NewRequest("POST", n.apiBase+"/nodes/register/", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if n.config.Server.APIToken != "" {
		req.Header.Set("Authorization", "Token "+n.config.Server.APIToken)
	}

	resp, err := n.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("registration request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		return "", fmt.Errorf("registration failed: %s - %s", resp.Status, string(respBody))
	}

	var result NodeResponse
	if err := json.Unmarshal(respBody, &result); err != nil {
		return "", fmt.Errorf("failed to parse response: %w", err)
	}

	n.nodeID = result.NodeID
	if n.nodeID == "" {
		n.nodeID = result.ID
	}

	logInfo("Node registered successfully: %s", n.nodeID)
	return n.nodeID, nil
}

// Unregister unregisters this node from the control server
func (n *NodeClient) Unregister() error {
	if n.nodeID == "" {
		return nil
	}

	logInfo("Unregistering node: %s", n.nodeID)

	req, err := http.NewRequest("DELETE", fmt.Sprintf("%s/nodes/%s/", n.apiBase, n.nodeID), nil)
	if err != nil {
		return err
	}

	if n.config.Server.APIToken != "" {
		req.Header.Set("Authorization", "Token "+n.config.Server.APIToken)
	}

	resp, err := n.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 || resp.StatusCode == 204 {
		logInfo("Node unregistered successfully")
	}
	return nil
}

// GetPendingTasks retrieves pending tasks for this node
func (n *NodeClient) GetPendingTasks() ([]map[string]interface{}, error) {
	if n.nodeID == "" {
		return nil, fmt.Errorf("node not registered")
	}

	req, err := http.NewRequest("GET", fmt.Sprintf("%s/nodes/%s/pending-tasks/", n.apiBase, n.nodeID), nil)
	if err != nil {
		return nil, err
	}

	if n.config.Server.APIToken != "" {
		req.Header.Set("Authorization", "Token "+n.config.Server.APIToken)
	}

	resp, err := n.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("failed to get tasks: %s", resp.Status)
	}

	var result struct {
		Tasks []map[string]interface{} `json:"tasks"`
	}
	body, _ := io.ReadAll(resp.Body)
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	return result.Tasks, nil
}

// ReportTaskResult reports task execution result
func (n *NodeClient) ReportTaskResult(taskID string, result map[string]interface{}) error {
	payload := map[string]interface{}{
		"status": "completed",
		"result": result,
	}
	return n.updateTask(taskID, payload)
}

// ReportTaskError reports task execution error
func (n *NodeClient) ReportTaskError(taskID string, errMsg string) error {
	payload := map[string]interface{}{
		"status":        "failed",
		"error_message": errMsg,
	}
	return n.updateTask(taskID, payload)
}

// UpdateStatus updates node status
func (n *NodeClient) UpdateStatus(status string, details map[string]interface{}) error {
	if n.nodeID == "" {
		return nil
	}

	payload := map[string]interface{}{
		"status":  status,
		"details": details,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("PATCH", fmt.Sprintf("%s/nodes/%s/", n.apiBase, n.nodeID), bytes.NewReader(body))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	if n.config.Server.APIToken != "" {
		req.Header.Set("Authorization", "Token "+n.config.Server.APIToken)
	}

	resp, err := n.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}

// updateTask updates a task via API
func (n *NodeClient) updateTask(taskID string, payload map[string]interface{}) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("PATCH", fmt.Sprintf("%s/backup-tasks/%s/", n.apiBase, taskID), bytes.NewReader(body))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	if n.config.Server.APIToken != "" {
		req.Header.Set("Authorization", "Token "+n.config.Server.APIToken)
	}

	resp, err := n.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}

// getIPAddress returns the primary IP address
func (n *NodeClient) getIPAddress() string {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		return "127.0.0.1"
	}
	defer conn.Close()

	localAddr := conn.LocalAddr().(*net.UDPAddr)
	return localAddr.IP.String()
}

// getKopiaVersion returns the installed Kopia version
func (n *NodeClient) getKopiaVersion() string {
	// This will be called from Kopia module
	return "unknown"
}

// getPlatform returns the current platform
func getPlatform() string {
	return fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)
}

// Close closes the HTTP client
func (n *NodeClient) Close() {
	n.client.CloseIdleConnections()
}

// logInfo logs an info message
func logInfo(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Printf("[%s] [INFO] %s\n", timestamp, fmt.Sprintf(format, args...))
}

// logError logs an error message
func logError(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Fprintf(os.Stderr, "[%s] [ERROR] %s\n", timestamp, fmt.Sprintf(format, args...))
}

// logDebug logs a debug message
func logDebug(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Printf("[%s] [DEBUG] %s\n", timestamp, fmt.Sprintf(format, args...))
}
