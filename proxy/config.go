package main

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"gopkg.in/yaml.v3"
)

// ServerConfig holds server connection configuration
type ServerConfig struct {
	URL             string        `yaml:"url"`
	APIToken        string        `yaml:"api_token"`
	WSProtocol      string        `yaml:"ws_protocol"`
	ReconnectDelay  time.Duration `yaml:"reconnect_delay"`
	HeartbeatInterval time.Duration `yaml:"heartbeat_interval"`
}

// AgentSettings holds agent-specific configuration
type AgentSettings struct {
	Type     string `yaml:"type"`
	Name     string `yaml:"name"`
	Hostname string `yaml:"hostname"`
}

// BackupSettings holds backup-related configuration
type BackupSettings struct {
	DataPath            string `yaml:"data_path"`
	TempPath            string `yaml:"temp_path"`
	MaxConcurrentBackups int   `yaml:"max_concurrent_backups"`
	KopiaPath           string `yaml:"kopia_path"`
}

// LoggingSettings holds logging configuration
type LoggingSettings struct {
	Level      string `yaml:"level"`
	File       string `yaml:"file"`
	MaxSize    string `yaml:"max_size"`
	MaxBackups int    `yaml:"max_backups"`
}

// PerformanceSettings holds performance tuning configuration
type PerformanceSettings struct {
	WorkerThreads int  `yaml:"worker_threads"`
	BufferSize    int  `yaml:"buffer_size"`
	Compression   bool `yaml:"compression"`
}

// Config holds the complete proxy configuration
type Config struct {
	Version     string             `yaml:"version"`
	Server      ServerConfig       `yaml:"server"`
	Agent       AgentSettings      `yaml:"agent"`
	Backup      BackupSettings     `yaml:"backup"`
	Logging     LoggingSettings    `yaml:"logging"`
	Performance PerformanceSettings `yaml:"performance"`
	
	// Runtime state (not from config file)
	NodeID     string `yaml:"-"`
	Registered bool   `yaml:"-"`
}

// DefaultConfig returns a configuration with sensible defaults
func DefaultConfig() *Config {
	hostname, _ := os.Hostname()
	
	return &Config{
		Version: "1.0.0",
		Server: ServerConfig{
			URL:              "http://localhost:8000",
			APIToken:         "",
			WSProtocol:       "ws",
			ReconnectDelay:   5 * time.Second,
			HeartbeatInterval: 30 * time.Second,
		},
		Agent: AgentSettings{
			Type:     "source",
			Name:     "",
			Hostname: hostname,
		},
		Backup: BackupSettings{
			DataPath:            "/var/lib/hyperfilelens/data",
			TempPath:            "/tmp/hyperfilelens",
			MaxConcurrentBackups: 2,
			KopiaPath:           "kopia",
		},
		Logging: LoggingSettings{
			Level:      "info",
			File:       "/var/log/hyperfilelens/proxy.log",
			MaxSize:    "100MB",
			MaxBackups: 5,
		},
		Performance: PerformanceSettings{
			WorkerThreads: 4,
			BufferSize:    8192,
			Compression:   true,
		},
	}
}

// LoadConfig loads configuration from a YAML file
func LoadConfig(path string) (*Config, error) {
	cfg := DefaultConfig()
	
	// If path is empty, try default locations
	if path == "" {
		// Try common locations
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
	
	// If no config file found, use defaults from environment
	if path == "" {
		return loadFromEnvironment(cfg), nil
	}
	
	// Read config file
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}
	
	// Parse YAML
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}
	
	// Override with environment variables
	cfg = loadFromEnvironment(cfg)
	
	return cfg, nil
}

// loadFromEnvironment overrides config with environment variables
func loadFromEnvironment(cfg *Config) *Config {
	if v := os.Getenv("SERVER_URL"); v != "" {
		cfg.Server.URL = v
	}
	if v := os.Getenv("API_TOKEN"); v != "" {
		cfg.Server.APIToken = v
	}
	if v := os.Getenv("WS_PROTOCOL"); v != "" {
		cfg.Server.WSProtocol = v
	}
	if v := os.Getenv("RECONNECT_DELAY"); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			cfg.Server.ReconnectDelay = d
		}
	}
	if v := os.Getenv("HEARTBEAT_INTERVAL"); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			cfg.Server.HeartbeatInterval = d
		}
	}
	
	if v := os.Getenv("AGENT_TYPE"); v != "" {
		cfg.Agent.Type = v
	}
	if v := os.Getenv("AGENT_NAME"); v != "" {
		cfg.Agent.Name = v
	}
	if v := os.Getenv("AGENT_HOSTNAME"); v != "" {
		cfg.Agent.Hostname = v
	}
	
	if v := os.Getenv("BACKUP_DATA_PATH"); v != "" {
		cfg.Backup.DataPath = v
	}
	if v := os.Getenv("BACKUP_TEMP_PATH"); v != "" {
		cfg.Backup.TempPath = v
	}
	if v := os.Getenv("KOPIA_PATH"); v != "" {
		cfg.Backup.KopiaPath = v
	}
	
	if v := os.Getenv("LOG_LEVEL"); v != "" {
		cfg.Logging.Level = v
	}
	if v := os.Getenv("LOG_FILE"); v != "" {
		cfg.Logging.File = v
	}
	
	if v := os.Getenv("NODE_ID"); v != "" {
		cfg.NodeID = v
	}
	
	return cfg
}

// GetWebSocketURL returns the WebSocket connection URL
func (c *Config) GetWebSocketURL() string {
	// Convert HTTP URL to WebSocket URL
	baseURL := c.Server.URL
	if c.Server.WSProtocol == "wss" {
		baseURL = "wss://" + stripProtocol(c.Server.URL)
	} else {
		baseURL = "ws://" + stripProtocol(c.Server.URL)
	}
	
	nodeID := c.NodeID
	if nodeID == "" {
		nodeID = "unknown"
	}
	
	return fmt.Sprintf("%s/ws/node/%s/", baseURL, nodeID)
}

// GetAPIBase returns the API base URL
func (c *Config) GetAPIBase() string {
	return c.Server.URL + "/api/v1"
}

// stripProtocol removes http:// or https:// prefix
func stripProtocol(url string) string {
	if len(url) > 7 && url[:7] == "http://" {
		return url[7:]
	}
	if len(url) > 8 && url[:8] == "https://" {
		return url[8:]
	}
	return url
}

// EnsureLogDir ensures the log directory exists
func (c *Config) EnsureLogDir() error {
	dir := filepath.Dir(c.Logging.File)
	return os.MkdirAll(dir, 0755)
}

// EnsureDataDir ensures the data directory exists
func (c *Config) EnsureDataDir() error {
	if err := os.MkdirAll(c.Backup.DataPath, 0755); err != nil {
		return err
	}
	return os.MkdirAll(c.Backup.TempPath, 0755)
}
