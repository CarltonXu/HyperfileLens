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
	NodeID string `json:"node_id"`
	ID     string `json:"id"`
	Status string `json:"status"`
	Error  string `json:"error,omitempty"`
}

// HeartbeatPayload represents heartbeat data
type HeartbeatPayload struct {
	NodeID      string                   `json:"node_id"`
	Status      string                   `json:"status"`
	Metrics     *monitor.Metrics         `json:"metrics"`
	HostInfo    map[string]interface{}   `json:"host_info"`
	DiskInfo    []monitor.DiskPartition  `json:"disk_info,omitempty"`
	NetworkInfo []map[string]interface{} `json:"network_info,omitempty"`
	Timestamp   int64                    `json:"timestamp"`
}

// Client handles agent operations
type Client struct {
	config  *config.Config
	client  *http.Client
	apiURL  string
	nodeID  string
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

	// Save node ID to file for persistence
	c.saveNodeID()

	return c.nodeID, nil
}

// Heartbeat sends periodic heartbeat to control plane
func (c *Client) Heartbeat() error {
	if c.nodeID == "" {
		return fmt.Errorf("node not registered")
	}

	payload := HeartbeatPayload{
		NodeID:    c.nodeID,
		Status:    "healthy",
		Metrics:   c.collector.GetCurrent(),
		HostInfo:  monitor.GetHostInfo(),
		DiskInfo:  monitor.GetDiskPartitions(),
		NetworkInfo: monitor.GetNetworkInterfaces(),
		Timestamp: time.Now().Unix(),
	}

	body, _ := json.Marshal(payload)

	req, _ := http.NewRequest("POST",
		fmt.Sprintf("%s/nodes/%s/heartbeat/", c.apiURL, c.nodeID),
		bytes.NewReader(body))

	req.Header.Set("Content-Type", "application/json")
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
		fmt.Sprintf("%s/nodes/%s/", c.apiURL, c.nodeID), nil)

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

// GetSystemInfo returns complete system information
func (c *Client) GetSystemInfo() map[string]interface{} {
	return map[string]interface{}{
		"node_id":       c.nodeID,
		"metrics":       c.collector.GetCurrent(),
		"host_info":     monitor.GetHostInfo(),
		"disk_partitions": monitor.GetDiskPartitions(),
		"network_info":  monitor.GetNetworkInterfaces(),
		"timestamp":     time.Now().Unix(),
	}
}

// saveNodeID persists node ID to file
func (c *Client) saveNodeID() {
	nodeIDFile := "/var/lib/hyperfilelens/node_id"
	os.MkdirAll("/var/lib/hyperfilelens", 0755)
	os.WriteFile(nodeIDFile, []byte(c.nodeID), 0644)
}

// loadNodeID loads node ID from file
func (c *Client) loadNodeID() string {
	nodeIDFile := "/var/lib/hyperfilelens/node_id"
	data, err := os.ReadFile(nodeIDFile)
	if err != nil {
		return ""
	}
	return string(data)
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
