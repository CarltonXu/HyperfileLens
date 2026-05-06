package kopia

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// Client handles Kopia operations
type Client struct {
	path        string
	cachePath   string
	activeTasks map[string]*exec.Cmd
	tasksMu     sync.Mutex
}

// NewClient creates a new Kopia client
func NewClient(path, cachePath string) *Client {
	return &Client{
		path:        path,
		cachePath:   cachePath,
		activeTasks: make(map[string]*exec.Cmd),
	}
}

// CheckInstalled checks if Kopia is installed
func (c *Client) CheckInstalled() bool {
	cmd := exec.Command(c.path, "--version")
	return cmd.Run() == nil
}

// GetVersion returns Kopia version
func (c *Client) GetVersion() string {
	cmd := exec.Command(c.path, "--version")
	output, err := cmd.Output()
	if err != nil {
		return "unknown"
	}
	
	parts := strings.Fields(string(output))
	if len(parts) >= 2 {
		return parts[1]
	}
	return "unknown"
}

// BackupResult represents backup result
type BackupResult struct {
	SnapshotID  string    `json:"snapshot_id"`
	SourcePath  string    `json:"source_path"`
	Files       int       `json:"files"`
	Bytes       int64     `json:"bytes"`
	Duration    float64   `json:"duration"`
	CompletedAt time.Time `json:"completed_at"`
}

// RestoreResult represents restore result
type RestoreResult struct {
	SnapshotID  string    `json:"snapshot_id"`
	TargetPath  string    `json:"target_path"`
	Duration    float64   `json:"duration"`
	CompletedAt time.Time `json:"completed_at"`
}

// SnapshotInfo represents snapshot information
type SnapshotInfo struct {
	ID        string    `json:"id"`
	Path      string    `json:"path"`
	CreatedAt time.Time `json:"created_at"`
	Size      int64     `json:"size"`
}

// RepoConfig represents repository configuration
type RepoConfig struct {
	Type       string `json:"type"`       // filesystem, s3, azure, gcs
	Path       string `json:"path"`       // for filesystem
	Bucket     string `json:"bucket"`     // for object storage
	Endpoint   string `json:"endpoint"`   // for object storage
	AccessKey  string `json:"access_key"` // for object storage
	SecretKey  string `json:"secret_key"` // for object storage
	Password   string `json:"password"`
	ConfigPath string `json:"config_path"`
}

// ConnectRepo connects to a repository
func (c *Client) ConnectRepo(config map[string]interface{}, password string) error {
	repoType, _ := config["type"].(string)
	
	args := []string{"repository", "connect"}
	
	switch repoType {
	case "filesystem", "":
		args = append(args, "filesystem", "--path", getString(config, "path"))
	case "s3":
		args = append(args, "s3",
			"--bucket", getString(config, "bucket"),
			"--endpoint", getString(config, "endpoint"),
		)
		if ak := getString(config, "access_key"); ak != "" {
			args = append(args, "--access-key-id", ak)
		}
		if sk := getString(config, "secret_key"); sk != "" {
			args = append(args, "--secret-access-key", sk)
		}
	default:
		return fmt.Errorf("unsupported repository type: %s", repoType)
	}
	
	if password != "" {
		args = append(args, "--password", password)
	}
	
	cmd := exec.Command(c.path, args...)
	cmd.Env = append(os.Environ(), "KOPIA_PASSWORD="+password)
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("connect failed: %w - %s", err, string(output))
	}
	
	return nil
}

// Backup creates a backup snapshot
func (c *Client) Backup(taskID, sourcePath, password string) (*BackupResult, error) {
	startTime := time.Now()
	
	args := []string{
		"snapshot", "create",
		sourcePath,
		"--description", fmt.Sprintf("Task: %s", taskID),
		"--tags", fmt.Sprintf("task_id=%s", taskID),
	}
	
	fmt.Printf("[INFO] Executing: kopia %s\n", strings.Join(args, " "))
	
	cmd := exec.Command(c.path, args...)
	cmd.Env = append(os.Environ())
	if password != "" {
		cmd.Env = append(cmd.Env, "KOPIA_PASSWORD="+password)
	}
	
	// Track for cancellation
	c.tasksMu.Lock()
	c.activeTasks[taskID] = cmd
	c.tasksMu.Unlock()
	
	defer func() {
		c.tasksMu.Lock()
		delete(c.activeTasks, taskID)
		c.tasksMu.Unlock()
	}()
	
	output, err := cmd.CombinedOutput()
	
	result := &BackupResult{
		SourcePath:  sourcePath,
		CompletedAt: time.Now(),
		Duration:    time.Since(startTime).Seconds(),
	}
	
	if err != nil {
		return result, fmt.Errorf("backup failed: %w - %s", err, string(output))
	}
	
	// Parse snapshot ID from output
	result.SnapshotID = c.parseSnapshotID(string(output))
	
	return result, nil
}

// Restore restores from a snapshot
func (c *Client) Restore(taskID, snapshotID, targetPath, password string, overwrite bool) (*RestoreResult, error) {
	startTime := time.Now()
	
	args := []string{"snapshot", "restore", snapshotID, targetPath}
	if overwrite {
		args = append(args, "--overwrite")
	}
	
	fmt.Printf("[INFO] Executing: kopia %s\n", strings.Join(args, " "))
	
	cmd := exec.Command(c.path, args...)
	cmd.Env = append(os.Environ())
	if password != "" {
		cmd.Env = append(cmd.Env, "KOPIA_PASSWORD="+password)
	}
	
	c.tasksMu.Lock()
	c.activeTasks[taskID] = cmd
	c.tasksMu.Unlock()
	
	defer func() {
		c.tasksMu.Lock()
		delete(c.activeTasks, taskID)
		c.tasksMu.Unlock()
	}()
	
	output, err := cmd.CombinedOutput()
	
	result := &RestoreResult{
		SnapshotID:  snapshotID,
		TargetPath:  targetPath,
		CompletedAt: time.Now(),
		Duration:    time.Since(startTime).Seconds(),
	}
	
	if err != nil {
		return result, fmt.Errorf("restore failed: %w - %s", err, string(output))
	}
	
	return result, nil
}

// ListSnapshots lists available snapshots
func (c *Client) ListSnapshots(password string) ([]SnapshotInfo, error) {
	args := []string{"snapshot", "list", "--json"}
	
	cmd := exec.Command(c.path, args...)
	cmd.Env = append(os.Environ())
	if password != "" {
		cmd.Env = append(cmd.Env, "KOPIA_PASSWORD="+password)
	}
	
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("list failed: %w", err)
	}
	
	var snapshots []SnapshotInfo
	if err := json.Unmarshal(output, &snapshots); err != nil {
		// Try parsing non-JSON output
		return c.parseSnapshotList(string(output))
	}
	
	return snapshots, nil
}

// Cancel cancels a running task
func (c *Client) Cancel(taskID string) bool {
	c.tasksMu.Lock()
	defer c.tasksMu.Unlock()
	
	cmd, exists := c.activeTasks[taskID]
	if !exists {
		return false
	}
	
	if cmd.Process != nil {
		cmd.Process.Kill()
	}
	
	return true
}

// parseSnapshotID extracts snapshot ID from output
func (c *Client) parseSnapshotID(output string) string {
	lines := strings.Split(output, "\n")
	for _, line := range lines {
		if strings.Contains(strings.ToLower(line), "snapshot") {
			parts := strings.Fields(line)
			if len(parts) >= 1 {
				return parts[0]
			}
		}
	}
	return ""
}

// parseSnapshotList parses non-JSON snapshot list
func (c *Client) parseSnapshotList(output string) ([]SnapshotInfo, error) {
	var snapshots []SnapshotInfo
	lines := strings.Split(output, "\n")
	
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		
		parts := strings.Fields(line)
		if len(parts) >= 1 {
			snapshots = append(snapshots, SnapshotInfo{
				ID: parts[0],
			})
		}
	}
	
	return snapshots, nil
}

// CreateRepoResult represents repository creation result
type CreateRepoResult struct {
	RepositoryID string    `json:"repository_id"`
	Path         string    `json:"path"`
	CreatedAt    time.Time `json:"created_at"`
}

// CreateRepo creates a new Kopia repository
// This initializes a new repository on the storage backend
func (c *Client) CreateRepo(config map[string]interface{}, password string) (*CreateRepoResult, error) {
	repoType, _ := config["type"].(string)

	args := []string{"repository", "create"}

	switch repoType {
	case "filesystem", "":
		args = append(args, "filesystem", "--path", getString(config, "path"))
	case "s3":
		args = append(args, "s3",
			"--bucket", getString(config, "bucket"),
			"--endpoint", getString(config, "endpoint"),
		)
		if ak := getString(config, "access_key"); ak != "" {
			args = append(args, "--access-key-id", ak)
		}
		if sk := getString(config, "secret_key"); sk != "" {
			args = append(args, "--secret-access-key", sk)
		}
	default:
		return nil, fmt.Errorf("unsupported repository type: %s", repoType)
	}

	if password != "" {
		args = append(args, "--password", password)
	}

	// Add encryption algorithm if specified
	if encryption := getString(config, "encryption"); encryption != "" {
		args = append(args, "--encryption", encryption)
	}

	fmt.Printf("[INFO] Executing: kopia %s\n", strings.Join(args, " "))

	cmd := exec.Command(c.path, args...)
	cmd.Env = append(os.Environ(), "KOPIA_PASSWORD="+password)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("repository creation failed: %w - %s", err, string(output))
	}

	result := &CreateRepoResult{
		CreatedAt: time.Now(),
	}

	// Extract repository ID from output
	result.RepositoryID = c.parseRepositoryID(string(output))
	result.Path = getString(config, "path")

	return result, nil
}

// parseRepositoryID extracts repository ID from output
func (c *Client) parseRepositoryID(output string) string {
	lines := strings.Split(output, "\n")
	for _, line := range lines {
		if strings.Contains(strings.ToLower(line), "repository") {
			parts := strings.Fields(line)
			if len(parts) >= 1 {
				return parts[0]
			}
		}
	}
	return ""
}

func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}
