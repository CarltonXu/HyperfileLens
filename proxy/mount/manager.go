package mount

import (
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/hyperfilelens/proxy/logger"
)

// Manager handles mount operations (Sync Proxy only)
type Manager struct {
	mounts map[string]*MountInfo
	mu     sync.RWMutex
}

// MountInfo represents mount information
type MountInfo struct {
	Type   string `json:"type"`
	Server string `json:"server"`
	Path   string `json:"path"`
	Target string `json:"target"`
	Status string `json:"status"`
}

// ConnectivityResult represents NAS connectivity test result
type ConnectivityResult struct {
	Reachable    bool   `json:"reachable"`
	ResponseTime int64  `json:"response_time_ms"` // in milliseconds
	Error        string `json:"error,omitempty"`
}

// WriteTestResult represents NAS write test result
type WriteTestResult struct {
	Writable     bool   `json:"writable"`
	WriteSpeed   int64  `json:"write_speed_kbps"` // KB/s, 0 if not writable
	ReadSpeed    int64  `json:"read_speed_kbps"`  // KB/s, 0 if not readable
	TestFileSize int64  `json:"test_file_size"`
	Error        string `json:"error,omitempty"`
}

// NewManager creates a new mount manager
func NewManager() *Manager {
	return &Manager{
		mounts: make(map[string]*MountInfo),
	}
}

// MountNFS mounts an NFS share
// Note: Requires root privileges and nfs-utils installed
func (m *Manager) MountNFS(server, path, target string, options ...string) error {
	if server == "" || path == "" || target == "" {
		return fmt.Errorf("server, path and target are required")
	}

	// Create target directory
	if err := os.MkdirAll(target, 0755); err != nil {
		return fmt.Errorf("failed to create mount point: %w", err)
	}

	// Build mount options: default + user custom options
	// Default options for better compatibility and write access
	defaultOptions := "rw,nolock,soft,timeo=30,retrans=3"
	var mountOptions string

	if len(options) > 0 && options[0] != "" {
		// User provided custom options, combine with defaults
		// Check if user options already contain 'ro' (read-only)
		if strings.Contains(options[0], "ro") {
			// Remove 'rw' from defaults if user wants read-only
			defaultOptions = strings.Replace(defaultOptions, "rw,", "", 1)
		}
		mountOptions = defaultOptions + "," + options[0]
	} else {
		mountOptions = defaultOptions
	}

	logger.Debug("Mounting NFS with options", map[string]interface{}{
		"server":       server,
		"path":         path,
		"target":       target,
		"options":      mountOptions,
		"user_options": options,
	})

	// Mount NFS
	source := fmt.Sprintf("%s:%s", server, path)
	args := []string{"-t", "nfs", "-o", mountOptions, source, target}
	cmd := exec.Command("mount", args...)
	logger.Debug("Executing mount command", map[string]interface{}{
		"args": args,
	})

	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Error("NFS mount command failed", map[string]interface{}{
			"error":  err.Error(),
			"output": string(output),
		})
		return fmt.Errorf("NFS mount failed: %w - %s", err, string(output))
	}

	// Track mount
	m.mu.Lock()
	m.mounts[target] = &MountInfo{
		Type:   "nfs",
		Server: server,
		Path:   path,
		Target: target,
		Status: "mounted",
	}
	m.mu.Unlock()

	logger.Info("NFS mounted", map[string]interface{}{"source": source, "target": target})
	return nil
}

// MountSMB mounts an SMB/CIFS share
// Note: Requires root privileges and cifs-utils installed
func (m *Manager) MountSMB(server, share, target, username, password string, options ...string) error {
	if server == "" || share == "" || target == "" {
		return fmt.Errorf("server, share and target are required")
	}

	// Create target directory
	if err := os.MkdirAll(target, 0755); err != nil {
		return fmt.Errorf("failed to create mount point: %w", err)
	}

	// Build mount command
	source := fmt.Sprintf("//%s/%s", server, share)

	// Default options for SMB
	defaultOptions := "rw,soft,noserverino"
	var mountOptions string

	// Start with default options
	optsParts := []string{defaultOptions}

	// Add credentials
	if username != "" {
		optsParts = append(optsParts, fmt.Sprintf("username=%s", username))
		if password != "" {
			optsParts = append(optsParts, fmt.Sprintf("password=%s", password))
		}
	}

	// Add user custom options
	if len(options) > 0 && options[0] != "" {
		// Check if user options already contain 'ro' (read-only)
		if strings.Contains(options[0], "ro") {
			// Remove 'rw' from defaults if user wants read-only
			defaultOptions = strings.Replace(defaultOptions, "rw,", "", 1)
		}
		optsParts = append(optsParts, options[0])
	}

	mountOptions = strings.Join(optsParts, ",")

	logger.Debug("Mounting SMB with options", map[string]interface{}{
		"server":       server,
		"share":        share,
		"target":       target,
		"options":      mountOptions,
		"user_options": options,
	})

	args := []string{"-t", "cifs", "-o", mountOptions, source, target}
	cmd := exec.Command("mount", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Error("SMB mount command failed", map[string]interface{}{
			"error":  err.Error(),
			"output": string(output),
		})
		return fmt.Errorf("SMB mount failed: %w - %s", err, string(output))
	}

	// Track mount
	m.mu.Lock()
	m.mounts[target] = &MountInfo{
		Type:   "smb",
		Server: server,
		Path:   share,
		Target: target,
		Status: "mounted",
	}
	m.mu.Unlock()

	logger.Info("SMB mounted", map[string]interface{}{"source": source, "target": target})
	return nil
}

// Unmount unmounts a mount point
func (m *Manager) Unmount(target string) error {
	cmd := exec.Command("umount", target)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("unmount failed: %w - %s", err, string(output))
	}

	m.mu.Lock()
	delete(m.mounts, target)
	m.mu.Unlock()

	logger.Info("Unmounted", map[string]interface{}{"target": target})
	return nil
}

// UnmountAll unmounts all managed mounts
func (m *Manager) UnmountAll() {
	m.mu.Lock()
	defer m.mu.Unlock()

	for target := range m.mounts {
		cmd := exec.Command("umount", target)
		if err := cmd.Run(); err != nil {
			logger.Warn("Failed to unmount", map[string]interface{}{"target": target, "error": err})
		}
		delete(m.mounts, target)
	}
}

// List returns all managed mounts
func (m *Manager) List() []*MountInfo {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*MountInfo, 0, len(m.mounts))
	for _, info := range m.mounts {
		result = append(result, info)
	}
	return result
}

// IsMounted checks if a path is mounted
func (m *Manager) IsMounted(target string) bool {
	m.mu.RLock()
	_, exists := m.mounts[target]
	m.mu.RUnlock()
	return exists
}

// IsPathMounted checks the operating system mount table for a target path.
// This catches mounts that existed before the proxy process started.
func IsPathMounted(target string) bool {
	cleanTarget := filepath.Clean(target)
	if cleanTarget == "." || cleanTarget == "" {
		return false
	}

	if data, err := os.ReadFile("/proc/mounts"); err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			fields := strings.Fields(line)
			if len(fields) >= 2 && filepath.Clean(fields[1]) == cleanTarget {
				return true
			}
		}
	}

	output, err := exec.Command("mount").CombinedOutput()
	if err != nil {
		return false
	}
	for _, line := range strings.Split(string(output), "\n") {
		if strings.Contains(line, " on "+cleanTarget+" ") || strings.HasSuffix(line, " on "+cleanTarget) {
			return true
		}
		fields := strings.Fields(line)
		if len(fields) >= 3 && fields[1] == "on" && filepath.Clean(fields[2]) == cleanTarget {
			return true
		}
	}
	return false
}

// CheckMounts verifies mount status
func (m *Manager) CheckMounts() error {
	// Read /proc/mounts to verify
	data, err := os.ReadFile("/proc/mounts")
	if err != nil {
		return err
	}

	mounts := string(data)

	m.mu.Lock()
	defer m.mu.Unlock()

	for target, info := range m.mounts {
		if !strings.Contains(mounts, target) {
			info.Status = "disconnected"
		}
	}

	return nil
}

// TestConnectivity tests NAS server connectivity
// For NFS, tests TCP port 2049; For SMB/CIFS, tests TCP port 445
func TestConnectivity(server string, port int) *ConnectivityResult {
	result := &ConnectivityResult{}

	logger.Debug("Connectivity test start", map[string]interface{}{
		"server": server,
		"port":   port,
	})

	if port == 0 {
		// Default ports
		port = 2049 // NFS default
		logger.Debug("Using default NFS port", map[string]interface{}{"port": port})
	}

	logger.Debug("Attempting TCP connection", map[string]interface{}{"server": server, "port": port})

	start := time.Now()

	// Try TCP connection with 5 second timeout
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", server, port), 5*time.Second)
	result.ResponseTime = time.Since(start).Milliseconds()

	if err != nil {
		result.Reachable = false
		result.Error = err.Error()
		logger.Debug("Connectivity test failed", map[string]interface{}{
			"error":         err.Error(),
			"response_time": result.ResponseTime,
			"reachable":     false,
		})
		return result
	}

	conn.Close()
	result.Reachable = true
	logger.Debug("Connectivity test success", map[string]interface{}{
		"response_time": result.ResponseTime,
		"reachable":     true,
	})
	return result
}

// TestNFSConnectivity tests NFS server connectivity (port 2049)
func TestNFSConnectivity(server string) *ConnectivityResult {
	logger.Debug("Testing NFS connectivity", map[string]interface{}{"server": server, "port": 2049})
	return TestConnectivity(server, 2049)
}

// TestSMBConnectivity tests SMB/CIFS server connectivity (port 445)
func TestSMBConnectivity(server string) *ConnectivityResult {
	logger.Debug("Testing SMB/CIFS connectivity", map[string]interface{}{"server": server, "port": 445})
	return TestConnectivity(server, 445)
}

// TestWrite performs a write test on a mounted path
// Creates a test file, writes data, reads it back, and deletes it
func TestWrite(mountPath string, testSizeKB int64) *WriteTestResult {
	result := &WriteTestResult{}

	if testSizeKB == 0 {
		testSizeKB = 1024 // Default 1MB test
	}
	result.TestFileSize = testSizeKB * 1024

	// Create test directory if needed
	testDir := filepath.Join(mountPath, ".hyperfilelens_test")
	logger.Debug("Creating test directory", map[string]interface{}{"test_dir": testDir})
	if err := os.MkdirAll(testDir, 0755); err != nil {
		result.Error = fmt.Sprintf("failed to create test directory: %v", err)
		logger.Debug("Failed to create test directory", map[string]interface{}{"error": err})
		return result
	}
	defer os.RemoveAll(testDir)

	testFile := filepath.Join(testDir, "write_test.tmp")
	logger.Debug("Test file", map[string]interface{}{"test_file": testFile})

	// Test write
	testData := make([]byte, testSizeKB*1024)
	for i := range testData {
		testData[i] = byte(i % 256)
	}

	logger.Debug("Starting write test", map[string]interface{}{"test_size_kb": testSizeKB})
	writeStart := time.Now()
	if err := os.WriteFile(testFile, testData, 0644); err != nil {
		result.Error = fmt.Sprintf("write test failed: %v", err)
		logger.Debug("Write failed", map[string]interface{}{"error": err})
		return result
	}
	writeDuration := time.Since(writeStart)
	result.WriteSpeed = (testSizeKB * 1024) / (writeDuration.Milliseconds() + 1) * 1000 / 1024 // KB/s
	logger.Debug("Write completed", map[string]interface{}{
		"duration_ms": writeDuration.Milliseconds(),
		"speed_kbps":  result.WriteSpeed,
	})

	// Test read
	logger.Debug("Starting read test", nil)
	readStart := time.Now()
	readData, err := os.ReadFile(testFile)
	if err != nil {
		result.Error = fmt.Sprintf("read test failed: %v", err)
		logger.Debug("Read failed", map[string]interface{}{"error": err})
		return result
	}
	readDuration := time.Since(readStart)
	result.ReadSpeed = (testSizeKB * 1024) / (readDuration.Milliseconds() + 1) * 1000 / 1024 // KB/s
	logger.Debug("Read completed", map[string]interface{}{
		"duration_ms": readDuration.Milliseconds(),
		"speed_kbps":  result.ReadSpeed,
	})

	// Verify data
	if len(readData) != len(testData) {
		result.Error = "read data size mismatch"
		logger.Debug("Data verification failed", map[string]interface{}{
			"expected_bytes": len(testData),
			"got_bytes":      len(readData),
		})
		return result
	}
	logger.Debug("Data verification passed", nil)

	// Clean up
	logger.Debug("Deleting test file...", nil)
	os.Remove(testFile)

	result.Writable = true
	logger.Debug("Write test successful", nil)
	return result
}

// TestWriteSimple performs a simple write test (creates and deletes a small file)
func TestWriteSimple(mountPath string) *WriteTestResult {
	logger.Debug("Write test start", map[string]interface{}{
		"mount_path": mountPath,
		"test_size":  "100 KB",
	})

	result := TestWrite(mountPath, 100) // 100KB test

	logger.Debug("Write test results", map[string]interface{}{
		"writable":    result.Writable,
		"write_speed": result.WriteSpeed,
		"read_speed":  result.ReadSpeed,
		"error":       result.Error,
	})

	return result
}

// GetMountSpaceInfo returns space information for a mount point
func GetMountSpaceInfo(mountPath string) (total, used, free uint64, err error) {
	logger.Debug("Space info start", map[string]interface{}{"mount_path": mountPath})

	// Use df command to get space info
	cmd := exec.Command("df", "-B1", mountPath)

	output, err := cmd.Output()
	if err != nil {
		logger.Debug("Space info failed", map[string]interface{}{"error": err})
		return 0, 0, 0, err
	}

	// Parse df output
	lines := strings.Split(string(output), "\n")
	if len(lines) < 2 {
		logger.Debug("Space info failed", map[string]interface{}{"error": "unexpected df output format"})
		return 0, 0, 0, fmt.Errorf("unexpected df output")
	}

	// Parse second line
	fields := strings.Fields(lines[1])
	if len(fields) < 4 {
		logger.Debug("Space info failed", map[string]interface{}{"error": fmt.Sprintf("unexpected df output format (only %d fields)", len(fields))})
		return 0, 0, 0, fmt.Errorf("unexpected df output format")
	}

	fmt.Sscanf(fields[1], "%d", &total)
	fmt.Sscanf(fields[2], "%d", &used)
	fmt.Sscanf(fields[3], "%d", &free)

	logger.Debug("Space info results", map[string]interface{}{
		"total_gb":    float64(total) / 1024 / 1024 / 1024,
		"total_bytes": total,
		"used_gb":     float64(used) / 1024 / 1024 / 1024,
		"used_bytes":  used,
		"free_gb":     float64(free) / 1024 / 1024 / 1024,
		"free_bytes":  free,
	})

	return total, used, free, nil
}

// ListDirectory lists directory contents
func ListDirectory(path string) ([]map[string]interface{}, error) {
	entries, err := os.ReadDir(path)
	if err != nil {
		return nil, err
	}

	result := make([]map[string]interface{}, 0, len(entries))
	for _, entry := range entries {
		info := map[string]interface{}{
			"name":  entry.Name(),
			"isDir": entry.IsDir(),
		}

		if fi, err := entry.Info(); err == nil {
			info["size"] = fi.Size()
			info["modTime"] = fi.ModTime()
			info["mode"] = fi.Mode().String()
		}

		result = append(result, info)
	}

	return result, nil
}

// CopyFile copies a file from src to dst
func CopyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destFile.Close()

	_, err = io.Copy(destFile, sourceFile)
	return err
}
