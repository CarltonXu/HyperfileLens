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
	Version     string      `yaml:"version"`
	Role        Role        `yaml:"role"`
	Server      Server      `yaml:"server"`
	Agent       Agent       `yaml:"agent"`
	Kopia       Kopia       `yaml:"kopia"`
	Mount       Mount       `yaml:"mount"`
	Logging     Logging     `yaml:"logging"`
	Performance Performance `yaml:"performance"`
	Security    Security    `yaml:"security"`
	Storage     Storage     `yaml:"storage"`

	// Runtime state
	NodeID     string `yaml:"-"`
	TenantID   string `yaml:"-"` // Assigned by control plane during registration
	ConfigPath string `yaml:"-"`
}

// Server holds server connection configuration
type Server struct {
	URL               string        `yaml:"url"`
	APIToken          string        `yaml:"api_token"`
	WSProtocol        string        `yaml:"ws_protocol"`
	ReconnectDelay    time.Duration `yaml:"reconnect_delay"`
	HeartbeatInterval time.Duration `yaml:"heartbeat_interval"`
	VerifySSL         bool          `yaml:"verify_ssl"`
	Timeout           time.Duration `yaml:"timeout"`
}

// Agent holds agent-specific configuration
type Agent struct {
	ID           string `yaml:"id"` // Proxy ID from control plane
	Name         string `yaml:"name"`
	Hostname     string `yaml:"hostname"`
	InstallToken string `yaml:"install_token"`
}

// Kopia holds Kopia configuration
type Kopia struct {
	Path       string `yaml:"path"`
	CachePath  string `yaml:"cache_path"`
	ConfigPath string `yaml:"config_path"`
}

// Mount holds mount configuration (for Sync Proxy only)
type Mount struct {
	Enabled bool     `yaml:"enabled"`
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
	Format     string `yaml:"format"` // "text" or "json"
	Remote     bool   `yaml:"remote"`
}

// Performance holds performance configuration
type Performance struct {
	MaxConcurrentTasks int   `yaml:"max_concurrent_tasks"`
	TaskTimeoutSeconds int   `yaml:"task_timeout_seconds"`
	CompressionEnabled bool  `yaml:"compression_enabled"`
	CompressionLevel   int   `yaml:"compression_level"`
	RateLimitKBPS      int64 `yaml:"rate_limit_kbps"`
	BufferSizeMB       int   `yaml:"buffer_size_mb"`
	ChunkSizeMB        int   `yaml:"chunk_size_mb"`
}

// Security holds security configuration
type Security struct {
	TLSVerify         bool     `yaml:"tls_verify"`
	TLSCertPath       string   `yaml:"tls_cert_path"`
	TLSKeyPath        string   `yaml:"tls_key_path"`
	AllowedHosts      []string `yaml:"allowed_hosts"`
	EnableMetricsAuth bool     `yaml:"enable_metrics_auth"`
	MetricsPassword   string   `yaml:"metrics_password"`
}

// Storage holds storage configuration
type Storage struct {
	CacheSizeMB     int    `yaml:"cache_size_mb"`
	TempDirectory   string `yaml:"temp_directory"`
	TempCleanup     bool   `yaml:"temp_cleanup"`
	RetentionPolicy string `yaml:"retention_policy"` // "delete", "archive"
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
			VerifySSL:         true,
			Timeout:           30 * time.Second,
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
			Format:     "text",
			Remote:     false,
		},
		Performance: Performance{
			MaxConcurrentTasks: 5,
			TaskTimeoutSeconds: 3600,
			CompressionEnabled: true,
			CompressionLevel:   6,
			RateLimitKBPS:      0, // 0 = no limit
			BufferSizeMB:       100,
			ChunkSizeMB:        50,
		},
		Security: Security{
			TLSVerify:         true,
			AllowedHosts:      []string{"localhost", "127.0.0.1"},
			EnableMetricsAuth: true,
		},
		Storage: Storage{
			CacheSizeMB:   1024,
			TempDirectory: "/var/lib/hyperfilelens/tmp",
			TempCleanup:   true,
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
		cfg.ConfigPath = path
	}

	// Override with environment variables
	cfg.applyEnvironment()

	// Use Agent.ID as NodeID if set in config
	if cfg.Agent.ID != "" {
		cfg.NodeID = cfg.Agent.ID
	}

	return cfg, nil
}

// SaveRuntimeCredentials persists runtime registration credentials to config.yaml.
func (c *Config) SaveRuntimeCredentials(apiToken string, installToken string) error {
	if apiToken != "" {
		c.Server.APIToken = apiToken
	}
	c.Agent.InstallToken = installToken

	if c.ConfigPath == "" {
		return nil
	}

	data, err := os.ReadFile(c.ConfigPath)
	if err != nil {
		return fmt.Errorf("failed to read config file: %w", err)
	}

	var root yaml.Node
	if err := yaml.Unmarshal(data, &root); err != nil {
		return fmt.Errorf("failed to parse config file: %w", err)
	}

	setYAMLScalar(&root, []string{"server", "api_token"}, c.Server.APIToken)
	setYAMLScalar(&root, []string{"agent", "install_token"}, c.Agent.InstallToken)

	output, err := yaml.Marshal(&root)
	if err != nil {
		return fmt.Errorf("failed to render config file: %w", err)
	}
	if err := os.WriteFile(c.ConfigPath, output, 0600); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}
	return nil
}

func setYAMLScalar(root *yaml.Node, path []string, value string) {
	if root.Kind == yaml.DocumentNode && len(root.Content) > 0 {
		setYAMLScalar(root.Content[0], path, value)
		return
	}
	if root.Kind != yaml.MappingNode || len(path) == 0 {
		return
	}

	for i := 0; i < len(root.Content)-1; i += 2 {
		key := root.Content[i]
		child := root.Content[i+1]
		if key.Value != path[0] {
			continue
		}
		if len(path) == 1 {
			child.Kind = yaml.ScalarNode
			child.Tag = "!!str"
			child.Value = value
			child.Content = nil
			return
		}
		setYAMLScalar(child, path[1:], value)
		return
	}
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
