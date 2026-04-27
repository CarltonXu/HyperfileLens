package mount

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
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
