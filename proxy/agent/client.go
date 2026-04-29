package agent

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

	"github.com/hyperfilelens/proxy/config"
	"github.com/hyperfilelens/proxy/monitor"
)

// Registration represents registration request
type Registration struct {
	Name         string                 `json:"name"`
	Role         string                 `json:"role"`
	Hostname     string                 `json:"hostname"`
	IPAddress    string                 `json:"ip_address"`
	Platform     string                 `json:"platform"`
	Capabilities map[string]interface{} `json:"capabilities"`
	Version      string                 `json:"version"`
}

// RegistrationResponse represents registration response
type RegistrationResponse struct {
	NodeID   string `json:"node_id"`
	ID       string `json:"id"`
	TenantID string `json:"tenant_id"`
	Status   string `json:"status"`
	Error    string `json:"error,omitempty"`
}

// HeartbeatPayload represents heartbeat data
// HeartbeatPayload matches backend ProxyHeartbeatCreateSerializer fields
type HeartbeatPayload struct {
	// Required fields
	NodeID   string `json:"node_id"`
	APIToken string `json:"api_token"`

	// Optional fields - version info
	Version      string `json:"version,omitempty"`
	KopiaVersion string `json:"kopia_version,omitempty"`

	// Host info
	Hostname    string `json:"hostname,omitempty"`
	InternalIP  string `json:"internal_ip,omitempty"`
	OS          string `json:"os,omitempty"`
	OSVersion   string `json:"os_version,omitempty"`

	// Hardware info
	CPUCores   int   `json:"cpu_cores,omitempty"`
	MemoryTotal int64 `json:"memory_total,omitempty"`
	DiskTotal  int64 `json:"disk_total,omitempty"`

	// Current usage
	CPUUsage    float64 `json:"cpu_usage,omitempty"`
	MemoryUsage float64 `json:"memory_usage,omitempty"`
	DiskUsage   float64 `json:"disk_usage,omitempty"`

	// Network
	NetworkIn       int64 `json:"network_in,omitempty"`
	NetworkOut      int64 `json:"network_out,omitempty"`
	MemoryUsed       int64 `json:"memory_used,omitempty"`
	MemoryFree       int64 `json:"memory_free,omitempty"`
	DiskUsed         int64 `json:"disk_used,omitempty"`
	DiskFree         int64 `json:"disk_free,omitempty"`
	NetworkBytesSent int64 `json:"network_bytes_sent,omitempty"`
	NetworkBytesRecv int64 `json:"network_bytes_recv,omitempty"`
	NetworkInterfaces []monitor.NetworkInterfaceInfo `json:"network_interfaces"`
	DiskIOStats       []monitor.DiskIOStats          `json:"disk_io_stats"`

	// Task stats
	ActiveTasks     int `json:"active_tasks,omitempty"`
	CompletedTasks  int `json:"completed_tasks,omitempty"`
	FailedTasks     int `json:"failed_tasks,omitempty"`

	// Additional info
	Capabilities map[string]interface{} `json:"capabilities,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}


// Client handles agent operations
type Client struct {
	config    *config.Config
	client    *http.Client
	apiURL    string
	nodeID    string
	tenantID  string
	collector *monitor.Collector
}

// NewClient creates a new agent client
func NewClient(cfg *config.Config, collector *monitor.Collector) *Client {
	return &Client{
		config:    cfg,
		apiURL:    cfg.GetAPIURL(),
		collector: collector,
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Register registers this proxy with the control plane
func (c *Client) Register() (string, error) {
	hostInfo := monitor.GetHostInfo()
	
	reg := Registration{
		Name:      c.config.Agent.Name,
		Role:      string(c.config.Role),
		Hostname:  c.config.Agent.Hostname,
		IPAddress: c.getIPAddress(),
		Platform:  getPlatform(),
		Capabilities: map[string]interface{}{
			"backup":         true,
			"restore":        true,
			"mount":          c.config.IsSyncProxy(),
			"max_concurrent": 2,
			"os":             runtime.GOOS,
			"arch":           runtime.GOARCH,
			"cpu_cores":      runtime.NumCPU(),
		},
		Version: c.config.Version,
	}

	// Use hostname as name if not set
	if reg.Name == "" {
		reg.Name = reg.Hostname
	}
	
	// Add hostname from hostInfo if not set
	if reg.Hostname == "" {
		if hn, ok := hostInfo["hostname"].(string); ok {
			reg.Hostname = hn
		}
	}

	body, err := json.Marshal(reg)
	if err != nil {
		return "", fmt.Errorf("failed to marshal registration: %w", err)
	}

	req, err := http.NewRequest("POST", c.apiURL+"/proxies/register/", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if c.config.Server.APIToken != "" {
		req.Header.Set("Authorization", "Token "+c.config.Server.APIToken)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("registration request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		return "", fmt.Errorf("registration failed: %s - %s", resp.Status, string(respBody))
	}

	var result RegistrationResponse
	if err := json.Unmarshal(respBody, &result); err != nil {
		return "", fmt.Errorf("failed to parse response: %w", err)
	}

	// Store node ID
	c.nodeID = result.NodeID
	if c.nodeID == "" {
		c.nodeID = result.ID
	}

	// Store tenant ID
	c.tenantID = result.TenantID

	// Save node ID to file for persistence
	c.saveNodeID()

	return c.nodeID, nil
}

// Heartbeat sends periodic heartbeat to control plane
func (c *Client) Heartbeat() error {
	if c.nodeID == "" {
		return fmt.Errorf("node not registered")
	}

	// Collect metrics
	metrics := c.collector.GetCurrent()
	hostInfo := monitor.GetHostInfo()

	// Build flat payload matching backend serializer
	payload := HeartbeatPayload{
		NodeID:   c.nodeID,
		APIToken: c.config.Server.APIToken,
		Version:  c.config.Version,
	}

	// Add host info if available
	if hostInfo != nil {
		if hn, ok := hostInfo["hostname"].(string); ok {
			payload.Hostname = hn
		}
		if ip, ok := hostInfo["internal_ip"].(string); ok {
			payload.InternalIP = ip
		}
		if os, ok := hostInfo["os"].(string); ok {
			payload.OS = os
		}
		if osVer, ok := hostInfo["os_version"].(string); ok {
			payload.OSVersion = osVer
		}
	}

		// Add metrics if available
		if metrics != nil {
			payload.CPUUsage = metrics.CPUUsage
			payload.MemoryUsage = metrics.MemoryUsage
			payload.DiskUsage = metrics.DiskUsage
			payload.CPUCores = metrics.CPUCores
			payload.MemoryTotal = int64(metrics.MemoryTotal)
			payload.DiskTotal = int64(metrics.DiskTotal)
			payload.MemoryUsed = int64(metrics.MemoryUsed)
			payload.DiskUsed = int64(metrics.DiskUsed)
			payload.MemoryFree = int64(metrics.MemoryFree)
			payload.DiskFree = int64(metrics.DiskFree)
			payload.NetworkBytesSent = int64(metrics.NetworkBytesSent)
			payload.NetworkBytesRecv = int64(metrics.NetworkBytesRecv)
		}


	// Add network interfaces
	payload.NetworkInterfaces = monitor.GetNetworkInterfaces()

	// Add disk I/O stats
	payload.DiskIOStats = monitor.GetDiskIOStats()

	body, _ := json.Marshal(payload)

	req, _ := http.NewRequest("POST",
		fmt.Sprintf("%s/proxies/heartbeat/", c.apiURL),
		bytes.NewReader(body))

	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}

// StartHeartbeat starts periodic heartbeat goroutine
func (c *Client) StartHeartbeat(stopCh <-chan struct{}) {
	ticker := time.NewTicker(c.config.Server.HeartbeatInterval)
	defer ticker.Stop()

	for {
		select {
		case <-stopCh:
			return
		case <-ticker.C:
			if err := c.Heartbeat(); err != nil {
				fmt.Printf("[ERROR] Heartbeat failed: %v\n", err)
			}
		}
	}
}

// Unregister unregisters this proxy
func (c *Client) Unregister() error {
	if c.nodeID == "" {
		return nil
	}

	req, _ := http.NewRequest("DELETE",
		fmt.Sprintf("%s/proxies/%s/", c.apiURL, c.nodeID), nil)

	if c.config.Server.APIToken != "" {
		req.Header.Set("Authorization", "Token "+c.config.Server.APIToken)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}

// GetNodeID returns the node ID
func (c *Client) GetNodeID() string {
	return c.nodeID
}

// SetNodeID sets the node ID
func (c *Client) SetNodeID(id string) {
	c.nodeID = id
}

// GetTenantID returns the tenant ID
func (c *Client) GetTenantID() string {
	return c.tenantID
}

// SetTenantID sets the tenant ID
func (c *Client) SetTenantID(id string) {
	c.tenantID = id
}

// GetSystemInfo returns complete system information
func (c *Client) GetSystemInfo() map[string]interface{} {
	return map[string]interface{}{
		"node_id":         c.nodeID,
		"tenant_id":       c.tenantID,
		"metrics":         c.collector.GetCurrent(),
		"host_info":       monitor.GetHostInfo(),
		"disk_partitions": monitor.GetDiskPartitions(),
		"network_info":    monitor.GetNetworkInterfaces(),
		"timestamp":       time.Now().Unix(),
	}
}

// saveNodeID persists node ID and tenant ID to file
func (c *Client) saveNodeID() {
	nodeIDFile := "/var/lib/hyperfilelens/node_id"
	os.MkdirAll("/var/lib/hyperfilelens", 0755)
	
	data := map[string]string{
		"node_id":   c.nodeID,
		"tenant_id": c.tenantID,
	}
	jsonData, _ := json.Marshal(data)
	os.WriteFile(nodeIDFile, jsonData, 0644)
}

// loadNodeID loads node ID and tenant ID from file
func (c *Client) loadNodeID() (string, string) {
	nodeIDFile := "/var/lib/hyperfilelens/node_id"
	data, err := os.ReadFile(nodeIDFile)
	if err != nil {
		return "", ""
	}
	
	var result map[string]string
	if err := json.Unmarshal(data, &result); err != nil {
		return string(data), "" // Legacy format - just node_id
	}
	
	return result["node_id"], result["tenant_id"]
}

// getIPAddress returns the primary IP address
func (c *Client) getIPAddress() string {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		return "127.0.0.1"
	}
	defer conn.Close()

	localAddr := conn.LocalAddr().(*net.UDPAddr)
	return localAddr.IP.String()
}

// getPlatform returns platform string
func getPlatform() string {
	return fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)
}

// Close closes the HTTP client
func (c *Client) Close() {
	c.client.CloseIdleConnections()
}
