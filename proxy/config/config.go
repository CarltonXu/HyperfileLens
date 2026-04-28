package config

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"gopkg.in/yaml.v3"
)

// Role defines the proxy role type
type Role string

const (
	RoleAgent Role = "agent" // Source-side agent (on business servers)
	RoleSync  Role = "sync"  // Sync proxy (collector node)
)

// Config holds the complete proxy configuration
type Config struct {
	Version string `yaml:"version"`
	Role    Role   `yaml:"role"`
	Server  Server `yaml:"server"`
	Agent   Agent  `yaml:"agent"`
	Kopia   Kopia  `yaml:"kopia"`
	Mount   Mount  `yaml:"mount"`
	Logging Logging `yaml:"logging"`
	
	// Runtime state
	NodeID string `yaml:"-"`
}

// Server holds server connection configuration
type Server struct {
	URL              string        `yaml:"url"`
	APIToken         string        `yaml:"api_token"`
	WSProtocol       string        `yaml:"ws_protocol"`
	ReconnectDelay   time.Duration `yaml:"reconnect_delay"`
	HeartbeatInterval time.Duration `yaml:"heartbeat_interval"`
}

// Agent holds agent-specific configuration
type Agent struct {
	Name     string `yaml:"name"`
	Hostname string `yaml:"hostname"`
}

// Kopia holds Kopia configuration
type Kopia struct {
	Path        string `yaml:"path"`
	CachePath   string `yaml:"cache_path"`
	ConfigPath  string `yaml:"config_path"`
}

// Mount holds mount configuration (for Sync Proxy only)
type Mount struct {
	Enabled bool   `yaml:"enabled"`
	NFS     NFSMount `yaml:"nfs"`
	SMB     SMBMount `yaml:"smb"`
}

// NFSMount holds NFS mount configuration
type NFSMount struct {
	Server string `yaml:"server"`
	Path   string `yaml:"path"`
	Target string `yaml:"target"`
}

// SMBMount holds SMB mount configuration
type SMBMount struct {
	Server   string `yaml:"server"`
	Share    string `yaml:"share"`
	Target   string `yaml:"target"`
	Username string `yaml:"username"`
	Password string `yaml:"password"`
}

// Logging holds logging configuration
type Logging struct {
	Level      string `yaml:"level"`
	File       string `yaml:"file"`
	MaxSize    string `yaml:"max_size"`
	MaxBackups int    `yaml:"max_backups"`
}

// DefaultConfig returns configuration with sensible defaults
func DefaultConfig() *Config {
	hostname, _ := os.Hostname()
	
	return &Config{
		Version: "1.0.0",
		Role:    RoleAgent,
		Server: Server{
			URL:               "http://localhost:8000",
			WSProtocol:        "ws",
			ReconnectDelay:    5 * time.Second,
			HeartbeatInterval: 10 * time.Second,
		},
		Agent: Agent{
			Hostname: hostname,
		},
		Kopia: Kopia{
			Path:      "kopia",
			CachePath: "/var/lib/hyperfilelens/cache",
		},
		Mount: Mount{
			Enabled: false,
		},
		Logging: Logging{
			Level:      "info",
			File:       "/var/log/hyperfilelens/proxy.log",
			MaxSize:    "100MB",
			MaxBackups: 5,
		},
	}
}

// Load loads configuration from file and environment
func Load(path string) (*Config, error) {
	cfg := DefaultConfig()
	
	// Try default locations if path not specified
	if path == "" {
		locations := []string{
			"/opt/hyperfilelens/config.yaml",
			"/etc/hyperfilelens/config.yaml",
			"./config.yaml",
		}
		for _, loc := range locations {
			if _, err := os.Stat(loc); err == nil {
				path = loc
				break
			}
		}
	}
	
	// Load from file if exists
	if path != "" {
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("failed to read config file: %w", err)
		}
		
		if err := yaml.Unmarshal(data, cfg); err != nil {
			return nil, fmt.Errorf("failed to parse config file: %w", err)
		}
	}
	
	// Override with environment variables
	cfg.applyEnvironment()
	
	return cfg, nil
}

// applyEnvironment applies environment variable overrides
func (c *Config) applyEnvironment() {
	if v := os.Getenv("SERVER_URL"); v != "" {
		c.Server.URL = v
	}
	if v := os.Getenv("API_TOKEN"); v != "" {
		c.Server.APIToken = v
	}
	if v := os.Getenv("NODE_ID"); v != "" {
		c.NodeID = v
	}
	if v := os.Getenv("PROXY_ROLE"); v != "" {
		c.Role = Role(v)
	}
	if v := os.Getenv("KOPIA_PATH"); v != "" {
		c.Kopia.Path = v
	}
	if v := os.Getenv("LOG_LEVEL"); v != "" {
		c.Logging.Level = v
	}
}

// GetWebSocketURL returns the WebSocket connection URL
func (c *Config) GetWebSocketURL() string {
	protocol := c.Server.WSProtocol
	if protocol == "" {
		protocol = "ws"
	}
	
	// Strip protocol from URL
	base := c.Server.URL
	if len(base) > 7 && base[:7] == "http://" {
		base = base[7:]
	} else if len(base) > 8 && base[:8] == "https://" {
		base = base[8:]
	}
	
	nodeID := c.NodeID
	if nodeID == "" {
		nodeID = "unknown"
	}
	
	return fmt.Sprintf("%s://%s/ws/proxy/%s/", protocol, base, nodeID)
}

// GetAPIURL returns the API base URL
func (c *Config) GetAPIURL() string {
	return c.Server.URL + "/api/v1"
}

// IsSyncProxy returns true if this is a Sync Proxy
func (c *Config) IsSyncProxy() bool {
	return c.Role == RoleSync
}

// IsAgentProxy returns true if this is an Agent Proxy
func (c *Config) IsAgentProxy() bool {
	return c.Role == RoleAgent
}

// EnsureDirectories creates necessary directories
func (c *Config) EnsureDirectories() error {
	dirs := []string{
		filepath.Dir(c.Logging.File),
		c.Kopia.CachePath,
	}
	
	for _, dir := range dirs {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return err
		}
	}
	
	return nil
}
