package ws

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"github.com/hyperfilelens/proxy/config"
	"github.com/hyperfilelens/proxy/logger"
	"github.com/hyperfilelens/proxy/message"
	"github.com/hyperfilelens/proxy/monitor"
)

// Message represents a WebSocket message
type Message struct {
	Type    string                 `json:"type"`
	ID      string                 `json:"id"`
	Payload map[string]interface{} `json:"payload"`
}

// Handler handles incoming messages
type Handler func(msg Message)

// Client handles WebSocket communication
type Client struct {
	config    *config.Config
	conn      *websocket.Conn
	connMu    sync.Mutex
	handler   Handler
	connected bool
	stopCh    chan struct{}
	metrics   *monitor.Collector
	metricsMu sync.RWMutex
}

// NewClient creates a new WebSocket client
func NewClient(cfg *config.Config, handler Handler) *Client {
	return &Client{
		config:  cfg,
		handler: handler,
	}
}

// SetMetrics sets the metrics collector
func (c *Client) SetMetrics(metrics *monitor.Collector) {
	c.metricsMu.Lock()
	defer c.metricsMu.Unlock()
	c.metrics = metrics
}

// Connect establishes WebSocket connection
func (c *Client) Connect() error {
	url := c.config.GetWebSocketURL()

	headers := make(map[string][]string)
	if c.config.Server.APIToken != "" {
		headers["Authorization"] = []string{"Token " + c.config.Server.APIToken}
	}

	dialer := websocket.DefaultDialer
	conn, _, err := dialer.Dial(url, headers)
	if err != nil {
		return fmt.Errorf("failed to connect: %w", err)
	}

	c.connMu.Lock()
	c.conn = conn
	c.connected = true
	c.stopCh = make(chan struct{})
	c.connMu.Unlock()

	logger.Info("WebSocket connected", map[string]interface{}{"url": url})

	// Send registration message to confirm connection
	c.Send(Message{
		Type: message.MsgTypeRegister,
	})

	// Start heartbeat goroutine
	go c.heartbeat()

	return nil
}

// Disconnect closes WebSocket connection
func (c *Client) Disconnect() {
	c.connMu.Lock()
	defer c.connMu.Unlock()

	if c.stopCh != nil {
		close(c.stopCh)
		c.stopCh = nil
	}

	if c.conn != nil {
		c.conn.Close()
		c.conn = nil
	}
	c.connected = false
}

// Send sends a message to control plane
func (c *Client) Send(msg Message) error {
	c.connMu.Lock()
	defer c.connMu.Unlock()

	if c.conn == nil {
		return fmt.Errorf("not connected")
	}

	return c.conn.WriteJSON(msg)
}

// Listen starts listening for messages
func (c *Client) Listen(stopCh <-chan struct{}) {
	for {
		select {
		case <-stopCh:
			return
		default:
			c.connMu.Lock()
			conn := c.conn
			c.connMu.Unlock()

			if conn == nil {
				time.Sleep(1 * time.Second)
				continue
			}

			_, message, err := conn.ReadMessage()
			if err != nil {
				logger.Warn("Read error", map[string]interface{}{"error": err.Error()})
				c.handleDisconnect()
				continue
			}

			var msg Message
			if err := json.Unmarshal(message, &msg); err != nil {
				logger.Warn("JSON parse error", map[string]interface{}{"error": err.Error()})
				continue
			}

			logger.Debug("Received message", map[string]interface{}{
				"type":    msg.Type,
				"id":      msg.ID,
				"payload": msg.Payload,
			})

			if c.handler != nil {
				go c.handler(msg)
			}
		}
	}
}

// IsConnected returns connection status
func (c *Client) IsConnected() bool {
	c.connMu.Lock()
	defer c.connMu.Unlock()
	return c.connected
}

// handleDisconnect handles disconnection and reconnect
func (c *Client) handleDisconnect() {
	c.Disconnect()

	// Reconnect with backoff
	for {
		logger.Info("Reconnecting", map[string]interface{}{"delay": c.config.Server.ReconnectDelay})
		time.Sleep(c.config.Server.ReconnectDelay)

		if err := c.Connect(); err != nil {
			logger.Error("Reconnect failed", map[string]interface{}{"error": err.Error()})
			continue
		}
		break
	}
}

// heartbeat sends periodic heartbeat messages
func (c *Client) heartbeat() {
	if c.config.Server.HeartbeatInterval <= 0 {
		return
	}

	ticker := time.NewTicker(c.config.Server.HeartbeatInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			if c.IsConnected() {
				payload := map[string]interface{}{
					"timestamp": time.Now().Format(time.RFC3339),
				}

				// Add metrics if available
				c.metricsMu.RLock()
				if c.metrics != nil {
					metrics := c.metrics.GetCurrent()
					payload["metrics"] = map[string]interface{}{
						// CPU
						"cpu_usage":    metrics.CPUUsage,
						"cpu_cores":    metrics.CPUCores,
						"cpu_physical": metrics.CPUPhysical,

						// Memory
						"memory_usage": metrics.MemoryUsage,
						"memory_total": metrics.MemoryTotal,
						"memory_used":  metrics.MemoryUsed,
						"memory_free":  metrics.MemoryFree,

						// Disk
						"disk_usage": metrics.DiskUsage,
						"disk_total": metrics.DiskTotal,
						"disk_used":  metrics.DiskUsed,
						"disk_free":  metrics.DiskFree,

						// Network
						"network_bytes_sent":   metrics.NetworkBytesSent,
						"network_bytes_recv":   metrics.NetworkBytesRecv,
						"network_packets_sent": metrics.NetworkPacketsSent,
						"network_packets_recv": metrics.NetworkPacketsRecv,

						// System
						"uptime":     metrics.Uptime,
						"goroutines": metrics.Goroutines,
					}
				}
				c.metricsMu.RUnlock()

				c.Send(Message{
					Type:    message.MsgTypeHeartbeat,
					ID:      uuid.New().String(),
					Payload: payload,
				})
			}
		case <-c.stopCh:
			return
		}
	}
}
