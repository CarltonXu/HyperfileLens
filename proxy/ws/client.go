package ws

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/hyperfilelens/proxy/config"
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
	config   *config.Config
	conn     *websocket.Conn
	connMu   sync.Mutex
	handler  Handler
	connected bool
}

// NewClient creates a new WebSocket client
func NewClient(cfg *config.Config, handler Handler) *Client {
	return &Client{
		config:  cfg,
		handler: handler,
	}
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
	c.connMu.Unlock()
	
	fmt.Printf("[INFO] WebSocket connected: %s\n", url)
	
	// Send registration message
	c.Send(Message{
		Type: "register",
		Payload: map[string]interface{}{
			"node_id":  c.config.NodeID,
			"role":     c.config.Role,
			"version":  c.config.Version,
		},
	})
	
	return nil
}

// Disconnect closes WebSocket connection
func (c *Client) Disconnect() {
	c.connMu.Lock()
	defer c.connMu.Unlock()
	
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
				fmt.Printf("[WARN] Read error: %v\n", err)
				c.handleDisconnect()
				continue
			}
			
			var msg Message
			if err := json.Unmarshal(message, &msg); err != nil {
				fmt.Printf("[WARN] JSON parse error: %v\n", err)
				continue
			}
			
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
		fmt.Printf("[INFO] Reconnecting in %v...\n", c.config.Server.ReconnectDelay)
		time.Sleep(c.config.Server.ReconnectDelay)
		
		if err := c.Connect(); err != nil {
			fmt.Printf("[ERROR] Reconnect failed: %v\n", err)
			continue
		}
		break
	}
}
