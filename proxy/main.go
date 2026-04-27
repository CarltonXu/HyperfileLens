package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/google/uuid"
	"github.com/hyperfilelens/proxy/agent"
	"github.com/hyperfilelens/proxy/config"
	"github.com/hyperfilelens/proxy/kopia"
	"github.com/hyperfilelens/proxy/monitor"
	"github.com/hyperfilelens/proxy/mount"
	"github.com/hyperfilelens/proxy/task"
	"github.com/hyperfilelens/proxy/utils"
	"github.com/hyperfilelens/proxy/ws"
)

var (
	Version   = "1.0.0"
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
	flag.Parse()

	if *showVersion {
		fmt.Printf("HyperFileLens Proxy v%s\n", Version)
		fmt.Printf("Git Commit: %s\n", GitCommit)
		fmt.Printf("Build Time: %s\n", BuildTime)
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

	// Create stop channel
	stopCh := make(chan struct{})

	// Initialize components
	metrics := monitor.NewCollector()
	agentClient := agent.NewClient(cfg, metrics)
	kopiaClient := kopia.NewClient(cfg.Kopia.Path, cfg.Kopia.CachePath)
	mountMgr := mount.NewManager()

	// Check Kopia installation
	if !kopiaClient.CheckInstalled() {
		utils.LogError("Kopia not found at: %s", cfg.Kopia.Path)
		utils.LogInfo("Please install Kopia: https://kopia.io/docs/installation/")
		os.Exit(1)
	}
	utils.LogInfo("Kopia version: %s", kopiaClient.GetVersion())

	// Register with control plane
	utils.LogInfo("Registering with control plane...")
	if _, err := agentClient.Register(); err != nil {
		utils.LogError("Registration failed: %v", err)
		utils.LogInfo("Continuing without registration...")
	} else {
		cfg.NodeID = agentClient.GetNodeID()
		utils.LogInfo("Registered with node ID: %s", cfg.NodeID)
	}

	// Start heartbeat
	go agentClient.StartHeartbeat(stopCh)

	// Create task dispatcher
	dispatcher := task.NewDispatcher(cfg, kopiaClient, mountMgr, nil)

	// Create WebSocket client with dispatcher handler
	wsClient := ws.NewClient(cfg, dispatcher.HandleMessage)
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

func printBanner(cfg *config.Config) {
	fmt.Println()
	fmt.Println("╔══════════════════════════════════════════╗")
	fmt.Println("║        HyperFileLens Proxy               ║")
	fmt.Printf("║  Version: %-30s ║\n", Version)
	fmt.Printf("║  Role:    %-30s ║\n", cfg.Role)
	fmt.Printf("║  Node ID: %-30s ║\n", cfg.NodeID)
	fmt.Printf("║  Server:  %-30s ║\n", cfg.Server.URL)
	fmt.Println("╚══════════════════════════════════════════╝")
	fmt.Println()
}
