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
func (m *Manager) MountNFS(server, path, target string) error {
	if server == "" || path == "" || target == "" {
		return fmt.Errorf("server, path and target are required")
	}

	// Create target directory
	if err := os.MkdirAll(target, 0755); err != nil {
		return fmt.Errorf("failed to create mount point: %w", err)
	}

	// Mount NFS
	source := fmt.Sprintf("%s:%s", server, path)

	cmd := exec.Command("mount", "-t", "nfs", source, target)
	output, err := cmd.CombinedOutput()
	if err != nil {
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

	fmt.Printf("[INFO] NFS mounted: %s -> %s\n", source, target)
	return nil
}

// MountSMB mounts an SMB/CIFS share
// Note: Requires root privileges and cifs-utils installed
func (m *Manager) MountSMB(server, share, target, username, password string) error {
	if server == "" || share == "" || target == "" {
		return fmt.Errorf("server, share and target are required")
	}

	// Create target directory
	if err := os.MkdirAll(target, 0755); err != nil {
		return fmt.Errorf("failed to create mount point: %w", err)
	}

	// Build mount command
	source := fmt.Sprintf("//%s/%s", server, share)

	args := []string{"-t", "cifs", source, target}

	// Add credentials
	if username != "" {
		opts := fmt.Sprintf("username=%s", username)
		if password != "" {
			opts += fmt.Sprintf(",password=%s", password)
		}
		args = append(args, "-o", opts)
	}

	cmd := exec.Command("mount", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
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

	fmt.Printf("[INFO] SMB mounted: %s -> %s\n", source, target)
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

	fmt.Printf("[INFO] Unmounted: %s\n", target)
	return nil
}

// UnmountAll unmounts all managed mounts
func (m *Manager) UnmountAll() {
	m.mu.Lock()
	defer m.mu.Unlock()

	for target := range m.mounts {
		cmd := exec.Command("umount", target)
		if err := cmd.Run(); err != nil {
			fmt.Printf("[WARN] Failed to unmount %s: %v\n", target, err)
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
	
	if port == 0 {
		// Default ports
		port = 2049 // NFS default
	}

	start := time.Now()
	
	// Try TCP connection with 5 second timeout
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", server, port), 5*time.Second)
	result.ResponseTime = time.Since(start).Milliseconds()
	
	if err != nil {
		result.Reachable = false
		result.Error = err.Error()
		return result
	}
	
	conn.Close()
	result.Reachable = true
	return result
}

// TestNFSConnectivity tests NFS server connectivity (port 2049)
func TestNFSConnectivity(server string) *ConnectivityResult {
	return TestConnectivity(server, 2049)
}

// TestSMBConnectivity tests SMB/CIFS server connectivity (port 445)
func TestSMBConnectivity(server string) *ConnectivityResult {
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
	if err := os.MkdirAll(testDir, 0755); err != nil {
		result.Error = fmt.Sprintf("failed to create test directory: %v", err)
		return result
	}
	defer os.RemoveAll(testDir)
	
	testFile := filepath.Join(testDir, "write_test.tmp")
	
	// Test write
	testData := make([]byte, testSizeKB*1024)
	for i := range testData {
		testData[i] = byte(i % 256)
	}
	
	writeStart := time.Now()
	if err := os.WriteFile(testFile, testData, 0644); err != nil {
		result.Error = fmt.Sprintf("write test failed: %v", err)
		return result
	}
	writeDuration := time.Since(writeStart)
	result.WriteSpeed = (testSizeKB * 1024) / (writeDuration.Milliseconds() + 1) * 1000 / 1024 // KB/s
	
	// Test read
	readStart := time.Now()
	readData, err := os.ReadFile(testFile)
	if err != nil {
		result.Error = fmt.Sprintf("read test failed: %v", err)
		return result
	}
	readDuration := time.Since(readStart)
	result.ReadSpeed = (testSizeKB * 1024) / (readDuration.Milliseconds() + 1) * 1000 / 1024 // KB/s
	
	// Verify data
	if len(readData) != len(testData) {
		result.Error = "read data size mismatch"
		return result
	}
	
	// Clean up
	os.Remove(testFile)
	
	result.Writable = true
	return result
}

// TestWriteSimple performs a simple write test (creates and deletes a small file)
func TestWriteSimple(mountPath string) *WriteTestResult {
	return TestWrite(mountPath, 100) // 100KB test
}

// GetMountSpaceInfo returns space information for a mount point
func GetMountSpaceInfo(mountPath string) (total, used, free uint64, err error) {
	// Use df command to get space info
	cmd := exec.Command("df", "-B1", mountPath)
	output, err := cmd.Output()
	if err != nil {
		return 0, 0, 0, err
	}
	
	// Parse df output
	lines := strings.Split(string(output), "\n")
	if len(lines) < 2 {
		return 0, 0, 0, fmt.Errorf("unexpected df output")
	}
	
	// Parse second line
	fields := strings.Fields(lines[1])
	if len(fields) < 4 {
		return 0, 0, 0, fmt.Errorf("unexpected df output format")
	}
	
	fmt.Sscanf(fields[1], "%d", &total)
	fmt.Sscanf(fields[2], "%d", &used)
	fmt.Sscanf(fields[3], "%d", &free)
	
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
