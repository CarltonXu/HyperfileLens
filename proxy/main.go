package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/hyperfilelens/proxy/agent"
	"github.com/hyperfilelens/proxy/config"
	"github.com/hyperfilelens/proxy/kopia"
	"github.com/hyperfilelens/proxy/logger"
	"github.com/hyperfilelens/proxy/monitor"
	"github.com/hyperfilelens/proxy/mount"
	"github.com/hyperfilelens/proxy/task"
	"github.com/hyperfilelens/proxy/utils"
	"github.com/hyperfilelens/proxy/ws"
)

var (
	Version   = "1.0.9"
	GitCommit = "unknown"
	BuildTime = "unknown"
)

func main() {
	// Parse flags
	configPath := flag.String("config", os.Getenv("CONFIG_PATH"), "Path to config file")
	role := flag.String("role", os.Getenv("PROXY_ROLE"), "Proxy role (agent or sync)")
	serverURL := flag.String("server", os.Getenv("SERVER_URL"), "Control server URL")
	apiToken := flag.String("token", os.Getenv("API_TOKEN"), "API token")
	nodeID := flag.String("node", os.Getenv("NODE_ID"), "Node ID")
	showVersion := flag.Bool("version", false, "Show version")

	// Service management flags
	installService := flag.Bool("install-service", false, "Install as Windows service")
	uninstallService := flag.Bool("uninstall-service", false, "Uninstall Windows service")
	startService := flag.Bool("start-service", false, "Start Windows service")
	stopService := flag.Bool("stop-service", false, "Stop Windows service")
	runAsService := flag.Bool("run-as-service", false, "Run as Windows service")

	flag.Parse()

	if *showVersion {
		fmt.Printf("HyperFileLens Proxy v%s\n", Version)
		fmt.Printf("Git Commit: %s\n", GitCommit)
		fmt.Printf("Build Time: %s\n", BuildTime)
		return
	}

	// Handle service management commands (Windows only)
	if *installService {
		if err := registerWindowsService(*configPath); err != nil {
			fmt.Fprintf(os.Stderr, "Failed to install service: %v\n", err)
			os.Exit(1)
		}
		return
	}

	if *uninstallService {
		if err := unregisterWindowsService(); err != nil {
			fmt.Fprintf(os.Stderr, "Failed to uninstall service: %v\n", err)
			os.Exit(1)
		}
		return
	}

	if *startService {
		if err := startWindowsService(); err != nil {
			fmt.Fprintf(os.Stderr, "Failed to start service: %v\n", err)
			os.Exit(1)
		}
		return
	}

	if *stopService {
		if err := stopWindowsService(); err != nil {
			fmt.Fprintf(os.Stderr, "Failed to stop service: %v\n", err)
			os.Exit(1)
		}
		return
	}

	// Run as Windows service
	if *runAsService {
		if err := runWindowsService(); err != nil {
			fmt.Fprintf(os.Stderr, "Failed to run as service: %v\n", err)
			os.Exit(1)
		}
		return
	}

	// Load configuration
	cfg, err := config.Load(*configPath)
	if err != nil {
		utils.LogError("Failed to load config: %v", err)
		os.Exit(1)
	}

	// Apply command line overrides
	if *role != "" {
		cfg.Role = config.Role(*role)
	}
	if *serverURL != "" {
		cfg.Server.URL = *serverURL
	}
	if *apiToken != "" {
		cfg.Server.APIToken = *apiToken
	}
	if *nodeID != "" {
		cfg.NodeID = *nodeID
	}

	// Generate node ID if not set
	if cfg.NodeID == "" {
		cfg.NodeID = "node-" + uuid.New().String()[:8]
	}

	// Ensure directories
	if err := cfg.EnsureDirectories(); err != nil {
		utils.LogError("Failed to create directories: %v", err)
	}

	// Print banner
	printBanner(cfg)

	// Initialize logger based on configuration
	var appLogger *logger.StructuredLogger

	// Try to create file logger if log file path is specified
	if cfg.Logging.File != "" {
		appLogger, err = logger.NewFileLogger("proxy", cfg.Logging.File, logger.LevelInfo, cfg.Logging.Format == "json")
		if err != nil {
			utils.LogError("Failed to create file logger, falling back to stdout: %v", err)
			appLogger = logger.NewLogger("proxy", logger.LevelInfo, cfg.Logging.Format == "json")
		} else {
			utils.LogInfo("Logging to file: %s", cfg.Logging.File)
		}
	} else {
		appLogger = logger.NewLogger("proxy", logger.LevelInfo, cfg.Logging.Format == "json")
	}

	// Set log level from configuration
	logLevel := logger.LevelInfo
	switch cfg.Logging.Level {
	case "debug":
		logLevel = logger.LevelDebug
	case "info":
		logLevel = logger.LevelInfo
	case "warn":
		logLevel = logger.LevelWarn
	case "error":
		logLevel = logger.LevelError
	}
	appLogger.SetLevel(logLevel)

	// Replace the global logger with our configured one
	logger.SetLevel(logLevel)
	if cfg.Logging.Format == "json" {
		logger.SetJSONOutput(true)
	}

	// Log startup information
	appLogger.Info("HyperFileLens Proxy starting", map[string]interface{}{
		"version":    Version,
		"git_commit": GitCommit,
		"build_time": BuildTime,
		"role":       cfg.Role,
		"node_id":    cfg.NodeID,
		"log_level":  cfg.Logging.Level,
		"log_file":   cfg.Logging.File,
	})

	// Create stop channel
	stopCh := make(chan struct{})

	// Initialize components
	metrics := monitor.NewCollector()
	agentClient := agent.NewClient(cfg, metrics)
	kopiaClient := kopia.NewClient(cfg.Kopia.Path, cfg.Kopia.CachePath)
	mountMgr := mount.NewManager()
	var wsClient *ws.Client

	logger.Info("Proxy-side metric alerting disabled; control plane policies evaluate alerts", nil)

	// Check Kopia installation
	if !kopiaClient.CheckInstalled() {
		utils.LogError("Kopia not found at: %s", cfg.Kopia.Path)
		utils.LogInfo("Please install Kopia: https://kopia.io/docs/installation/")
		os.Exit(1)
	}
	utils.LogInfo("Kopia version: %s", kopiaClient.GetVersion())

	if err := ensureRegistered(cfg, agentClient); err != nil {
		utils.LogError("Registration failed: %v", err)
		os.Exit(1)
	}

	// Start heartbeat
	go agentClient.StartHeartbeat(stopCh)

	// Create task dispatcher
	dispatcher := task.NewDispatcher(cfg, kopiaClient, mountMgr, nil)

	// Create WebSocket client with dispatcher handler
	wsClient = ws.NewClient(cfg, dispatcher.HandleMessage)
	dispatcher.SetWSClient(wsClient)

	// Connect WebSocket
	if err := wsClient.Connect(); err != nil {
		utils.LogError("WebSocket connection failed: %v", err)
		utils.LogInfo("Will retry connection in background...")
	}

	// Start WebSocket listener
	go wsClient.Listen(stopCh)

	// Handle shutdown signals
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	// Wait for shutdown signal
	<-sigCh
	utils.LogInfo("Received shutdown signal, stopping...")

	// Cleanup
	close(stopCh)
	wsClient.Disconnect()
	agentClient.Unregister()
	agentClient.Close()

	// Unmount all if Sync Proxy
	if cfg.IsSyncProxy() {
		mountMgr.UnmountAll()
	}

	utils.LogInfo("Proxy stopped")
}

func ensureRegistered(cfg *config.Config, agentClient *agent.Client) error {
	if cfg.Server.APIToken != "" && cfg.Agent.ID != "" {
		utils.LogInfo("Using existing API token for node: %s", cfg.NodeID)
		agentClient.SetNodeID(cfg.NodeID)
		return nil
	}

	if cfg.Agent.ID == "" {
		return fmt.Errorf("agent.id is required")
	}
	if cfg.Agent.InstallToken == "" {
		return fmt.Errorf("agent.install_token is required when api_token is empty")
	}

	delay := cfg.Server.ReconnectDelay
	if delay <= 0 {
		delay = 5 * time.Second
	}

	for {
		utils.LogInfo("Registering with control plane...")
		if _, err := agentClient.Register(); err != nil {
			utils.LogError("Registration failed: %v", err)
			utils.LogInfo("Retrying registration in %s...", delay)
			time.Sleep(delay)
			continue
		}

		cfg.NodeID = agentClient.GetNodeID()
		cfg.TenantID = agentClient.GetTenantID()
		utils.LogInfo("Registered with node ID: %s", cfg.NodeID)
		if cfg.TenantID != "" {
			utils.LogInfo("Assigned to tenant: %s", cfg.TenantID)
		}
		return nil
	}
}

func printBanner(cfg *config.Config) {
	fmt.Println()
	fmt.Println("╔══════════════════════════════════════════╗")
	fmt.Println("║        HyperFileLens Proxy               ║")
	fmt.Printf("║  Version: %-30s ║\n", Version)
	fmt.Printf("║  Role:    %-30s ║\n", cfg.Role)
	fmt.Printf("║  Node ID: %-30s ║\n", cfg.NodeID)
	if cfg.TenantID != "" {
		fmt.Printf("║  Tenant:  %-30s ║\n", cfg.TenantID)
	}
	fmt.Printf("║  Server:  %-30s ║\n", cfg.Server.URL)
	fmt.Println("╚══════════════════════════════════════════╝")
	fmt.Println()
}
