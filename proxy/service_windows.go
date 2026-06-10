//go:build windows

package main

import (
	"context"
	"fmt"
	"os"
	"sync"
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
	"golang.org/x/sys/windows/svc"
	"golang.org/x/sys/windows/svc/mgr"
)

// Windows service implementation
type proxyService struct {
	ctx       context.Context
	cancel    context.CancelFunc
	waitGroup sync.WaitGroup
}

func (p *proxyService) Execute(args []string, r <-chan svc.ChangeRequest, changes chan<- svc.Status) (ssec bool, errno uint32) {
	// Signal that we're starting
	changes <- svc.Status{State: svc.StartPending}

	// Create context that can be cancelled
	p.ctx, p.cancel = context.WithCancel(context.Background())

	// Parse config path from args (passed via --config flag)
	configPath := ""
	for i, arg := range args {
		if arg == "--config" && i+1 < len(args) {
			configPath = args[i+1]
			break
		}
	}
	// Fallback to environment variable
	if configPath == "" {
		configPath = os.Getenv("HFL_CONFIG_PATH")
	}

	// Signal that we're running
	changes <- svc.Status{State: svc.Running, Accepts: svc.AcceptStop | svc.AcceptShutdown}

	// Run the proxy in a goroutine so we can handle service commands
	p.waitGroup.Add(1)
	go func() {
		defer p.waitGroup.Done()
		if err := p.runProxyService(configPath); err != nil {
			fmt.Fprintf(os.Stderr, "Proxy failed: %v\n", err)
		}
	}()

	// Handle service control requests
	for {
		select {
		case c := <-r:
			switch c.Cmd {
			case svc.Interrogate:
				changes <- c.CurrentStatus
			case svc.Stop, svc.Shutdown:
				changes <- svc.Status{State: svc.StopPending}
				p.cancel()
				p.waitGroup.Wait()
				return
			}
		case <-p.ctx.Done():
			p.waitGroup.Wait()
			return
		}
	}
}

// runProxyService runs the proxy with the given config path
func (p *proxyService) runProxyService(configPath string) error {
	if configPath == "" {
		return fmt.Errorf("config path not specified")
	}

	// Load configuration
	cfg, err := config.Load(configPath)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	// Generate node ID if not set
	if cfg.NodeID == "" {
		cfg.NodeID = "node-" + uuid.New().String()[:8]
	}

	// Ensure directories
	if err := cfg.EnsureDirectories(); err != nil {
		utils.LogError("Failed to create directories: %v", err)
	}

	// Initialize logger
	var appLogger *logger.StructuredLogger
	if cfg.Logging.File != "" {
		appLogger, err = logger.NewFileLogger("proxy", cfg.Logging.File, logger.LevelInfo, cfg.Logging.Format == "json")
		if err != nil {
			utils.LogError("Failed to create file logger, falling back to stdout: %v", err)
			appLogger = logger.NewLogger("proxy", logger.LevelInfo, cfg.Logging.Format == "json")
		}
	} else {
		appLogger = logger.NewLogger("proxy", logger.LevelInfo, cfg.Logging.Format == "json")
	}

	// Set log level
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
	logger.SetLevel(logLevel)
	if cfg.Logging.Format == "json" {
		logger.SetJSONOutput(true)
	}

	// Log startup
	appLogger.Info("HyperFileLens Proxy starting as service", map[string]interface{}{
		"version":   Version,
		"git_commit": GitCommit,
		"build_time": BuildTime,
		"role":      cfg.Role,
		"node_id":    cfg.NodeID,
	})

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
		return fmt.Errorf("kopia not found")
	}
	utils.LogInfo("Kopia version: %s", kopiaClient.GetVersion())

	// Ensure registered
	if err := p.ensureRegistered(cfg, agentClient); err != nil {
		utils.LogError("Registration failed: %v", err)
		return err
	}

	// Start heartbeat
	go agentClient.StartHeartbeat(stopCh)

	// Create task dispatcher
	dispatcher := task.NewDispatcher(cfg, kopiaClient, mountMgr, nil)

	// Create WebSocket client
	wsClient := ws.NewClient(cfg, dispatcher.HandleMessage)
	dispatcher.SetWSClient(wsClient)

	// Connect WebSocket
	if err := wsClient.Connect(); err != nil {
		utils.LogError("WebSocket connection failed: %v", err)
	}

	// Start WebSocket listener
	go wsClient.Listen(stopCh)

	// Wait for context cancellation (triggered by service stop)
	<-p.ctx.Done()
	utils.LogInfo("Service stopping...")

	// Cleanup
	close(stopCh)
	wsClient.Disconnect()
	agentClient.Unregister()
	agentClient.Close()

	if cfg.IsSyncProxy() {
		mountMgr.UnmountAll()
	}

	utils.LogInfo("Proxy stopped")
	return nil
}

// ensureRegistered handles agent registration for the service
func (p *proxyService) ensureRegistered(cfg *config.Config, agentClient *agent.Client) error {
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

// registerWindowsService registers the proxy as a Windows service
func registerWindowsService(configPath string) error {
	if configPath == "" {
		configPath = `C:\Program Files\HyperFileLens\Proxy\config\config.yaml`
	}

	// Get the path to the current executable
	exePath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("failed to get executable path: %w", err)
	}

	// Connect to service manager
	m, err := mgr.Connect()
	if err != nil {
		return fmt.Errorf("failed to connect to service manager: %w", err)
	}
	defer m.Disconnect()

	// Create service configuration
	// SERVICE_AUTO_START = 2
	conf := mgr.Config{
		DisplayName: "HyperFileLens Proxy",
		Description: "HyperFileLens source-side proxy agent",
		StartType:   2, // SERVICE_AUTO_START
	}

	// Try to create new service
	s, err := m.CreateService("HyperFileLensProxy", exePath, conf, "--config", configPath, "--run-as-service")
	if err != nil {
		// If service already exists, update it
		existing, err := m.OpenService("HyperFileLensProxy")
		if err != nil {
			return fmt.Errorf("failed to create or open service: %w", err)
		}
		defer existing.Close()

		err = existing.UpdateConfig(conf)
		if err != nil {
			return fmt.Errorf("failed to update service config: %w", err)
		}
		fmt.Println("Service updated successfully")
		return nil
	}
	defer s.Close()

	fmt.Println("Service registered successfully")
	return nil
}

// unregisterWindowsService removes the Windows service
func unregisterWindowsService() error {
	m, err := mgr.Connect()
	if err != nil {
		return fmt.Errorf("failed to connect to service manager: %w", err)
	}
	defer m.Disconnect()

	s, err := m.OpenService("HyperFileLensProxy")
	if err != nil {
		return fmt.Errorf("service not found: %w", err)
	}
	defer s.Close()

	// Stop service if running
	status, _ := s.Query()
	if status.State == svc.Running {
		s.Control(svc.Stop)
	}

	// Delete service
	err = s.Delete()
	if err != nil {
		return fmt.Errorf("failed to delete service: %w", err)
	}

	fmt.Println("Service unregistered successfully")
	return nil
}

// startWindowsService starts the Windows service
func startWindowsService() error {
	m, err := mgr.Connect()
	if err != nil {
		return fmt.Errorf("failed to connect to service manager: %w", err)
	}
	defer m.Disconnect()

	s, err := m.OpenService("HyperFileLensProxy")
	if err != nil {
		return fmt.Errorf("failed to open service: %w", err)
	}
	defer s.Close()

	err = s.Start()
	if err != nil {
		return fmt.Errorf("failed to start service: %w", err)
	}

	fmt.Println("Service started successfully")
	return nil
}

// stopWindowsService stops the Windows service
func stopWindowsService() error {
	m, err := mgr.Connect()
	if err != nil {
		return fmt.Errorf("failed to connect to service manager: %w", err)
	}
	defer m.Disconnect()

	s, err := m.OpenService("HyperFileLensProxy")
	if err != nil {
		return fmt.Errorf("failed to open service: %w", err)
	}
	defer s.Close()

	status, err := s.Query()
	if err != nil {
		return fmt.Errorf("failed to query service: %w", err)
	}

	if status.State == svc.Running {
		_, err = s.Control(svc.Stop)
		if err != nil {
			return fmt.Errorf("failed to stop service: %w", err)
		}
		fmt.Println("Service stopped successfully")
	} else {
		fmt.Println("Service is not running")
	}

	return nil
}

// runWindowsService runs the proxy as a Windows service
func runWindowsService() error {
	// Recover from any panic in the service
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "Service panicked: %v\n", r)
		}
	}()

	// Run the service
	err := svc.Run("HyperFileLensProxy", &proxyService{})
	if err != nil {
		return fmt.Errorf("service failed: %w", err)
	}
	return nil
}
