package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// KopiaExecutor handles Kopia CLI operations
type KopiaExecutor struct {
	config     *Config
	kopiaPath  string
	repoConfig string
	password   string
	
	// Task management
	activeTasks map[string]*exec.Cmd
	tasksMutex  sync.RWMutex
}

// BackupResult represents backup operation result
type BackupResult struct {
	Status         string    `json:"status"`
	SnapshotID     string    `json:"snapshot_id"`
	SourcePath     string    `json:"source_path"`
	CompletedAt    time.Time `json:"completed_at"`
	FilesProcessed int       `json:"files_processed"`
	BytesProcessed int64     `json:"bytes_processed"`
	Duration       float64   `json:"duration"`
	Output         string    `json:"output,omitempty"`
}

// RestoreResult represents restore operation result
type RestoreResult struct {
	Status      string    `json:"status"`
	SnapshotID  string    `json:"snapshot_id"`
	TargetPath  string    `json:"target_path"`
	RestoreType string    `json:"restore_type"`
	CompletedAt time.Time `json:"completed_at"`
	Duration    float64   `json:"duration"`
	Output      string    `json:"output,omitempty"`
}

// SnapshotInfo represents snapshot information
type SnapshotInfo struct {
	ID           string    `json:"id"`
	SourcePath   string    `json:"source_path"`
	Hostname     string    `json:"hostname"`
	Username     string    `json:"username"`
	CreatedAt    time.Time `json:"created_at"`
	Size         int64     `json:"size"`
	Files        int       `json:"files"`
	Description  string    `json:"description"`
	Tags         []string  `json:"tags,omitempty"`
}

// FileInfo represents file/directory information
type FileInfo struct {
	Name     string    `json:"name"`
	Path     string    `json:"path"`
	Type     string    `json:"type"` // "file" or "dir"
	Size     int64     `json:"size"`
	Modified time.Time `json:"modified"`
	Mode     string    `json:"mode"`
}

// RepositoryConfig represents repository connection configuration
type RepositoryConfig struct {
	Type       string `json:"type"`       // filesystem, s3, azure, gcs
	Path       string `json:"path"`       // for filesystem
	Endpoint   string `json:"endpoint"`   // for object storage
	Bucket     string `json:"bucket"`     // for object storage
	AccessKey  string `json:"access_key"` // for object storage
	SecretKey  string `json:"secret_key"` // for object storage
	Password   string `json:"password"`
	ConfigPath string `json:"config_path"` // path to kopia config
}

// NewKopiaExecutor creates a new Kopia executor
func NewKopiaExecutor(cfg *Config) *KopiaExecutor {
	return &KopiaExecutor{
		config:      cfg,
		kopiaPath:   cfg.Backup.KopiaPath,
		activeTasks: make(map[string]*exec.Cmd),
	}
}

// SetRepository sets the repository configuration
func (k *KopiaExecutor) SetRepository(repoConfig string, password string) {
	k.repoConfig = repoConfig
	k.password = password
}

// CheckInstalled checks if Kopia is installed and accessible
func (k *KopiaExecutor) CheckInstalled() bool {
	cmd := exec.Command(k.kopiaPath, "--version")
	if err := cmd.Run(); err != nil {
		return false
	}
	return true
}

// GetVersion returns the Kopia version
func (k *KopiaExecutor) GetVersion() string {
	cmd := exec.Command(k.kopiaPath, "--version")
	output, err := cmd.Output()
	if err != nil {
		return "unknown"
	}
	
	// Parse version from output like "kopia 0.15.0 build ..."
	parts := strings.Fields(string(output))
	if len(parts) >= 2 {
		return parts[1]
	}
	return "unknown"
}

// CreateSnapshot creates a backup snapshot
func (k *KopiaExecutor) CreateSnapshot(taskID, sourcePath, repoPath string, password string, tags map[string]string) (*BackupResult, error) {
	startTime := time.Now()
	
	// Build command arguments
	args := []string{"snapshot", "create", sourcePath}
	
	if repoPath != "" {
		args = append(args, "--repo-path", repoPath)
	}
	
	if password != "" {
		args = append(args, "--password", password)
	}
	
	// Add description
	description := fmt.Sprintf("Task: %s", taskID)
	args = append(args, "--description", description)
	
	// Add tags
	for key, value := range tags {
		args = append(args, "--tags", fmt.Sprintf("%s=%s", key, value))
	}
	
	logInfo("Executing: %s %s", k.kopiaPath, strings.Join(args, " "))
	
	cmd := exec.Command(k.kopiaPath, args...)
	
	// Track the command for potential cancellation
	k.tasksMutex.Lock()
	k.activeTasks[taskID] = cmd
	k.tasksMutex.Unlock()
	
	defer func() {
		k.tasksMutex.Lock()
		delete(k.activeTasks, taskID)
		k.tasksMutex.Unlock()
	}()
	
	// Capture output
	output, err := cmd.CombinedOutput()
	
	result := &BackupResult{
		SourcePath:  sourcePath,
		CompletedAt: time.Now(),
		Duration:    time.Since(startTime).Seconds(),
		Output:      string(output),
	}
	
	if err != nil {
		result.Status = "failed"
		logError("Backup failed for task %s: %v", taskID, err)
		return result, fmt.Errorf("kopia backup failed: %w", err)
	}
	
	// Parse snapshot ID from output
	result.SnapshotID = k.parseSnapshotID(string(output))
	result.Status = "completed"
	
	logInfo("Backup completed for task %s: snapshot=%s", taskID, result.SnapshotID)
	return result, nil
}

// RestoreSnapshot restores from a snapshot
func (k *KopiaExecutor) RestoreSnapshot(taskID, snapshotID, targetPath, repoPath string, password string, overwrite bool) (*RestoreResult, error) {
	startTime := time.Now()
	
	// Build command arguments
	args := []string{"snapshot", "restore", snapshotID, targetPath}
	
	if repoPath != "" {
		args = append(args, "--repo-path", repoPath)
	}
	
	if password != "" {
		args = append(args, "--password", password)
	}
	
	if overwrite {
		args = append(args, "--overwrite")
	}
	
	logInfo("Executing: %s %s", k.kopiaPath, strings.Join(args, " "))
	
	cmd := exec.Command(k.kopiaPath, args...)
	
	// Track the command for potential cancellation
	k.tasksMutex.Lock()
	k.activeTasks[taskID] = cmd
	k.tasksMutex.Unlock()
	
	defer func() {
		k.tasksMutex.Lock()
		delete(k.activeTasks, taskID)
		k.tasksMutex.Unlock()
	}()
	
	output, err := cmd.CombinedOutput()
	
	result := &RestoreResult{
		SnapshotID:  snapshotID,
		TargetPath:  targetPath,
		RestoreType: "original",
		CompletedAt: time.Now(),
		Duration:    time.Since(startTime).Seconds(),
		Output:      string(output),
	}
	
	if overwrite {
		result.RestoreType = "new_location"
	}
	
	if err != nil {
		result.Status = "failed"
		logError("Restore failed for task %s: %v", taskID, err)
		return result, fmt.Errorf("kopia restore failed: %w", err)
	}
	
	result.Status = "completed"
	logInfo("Restore completed for task %s", taskID)
	return result, nil
}

// ListSnapshots lists all snapshots in a repository
func (k *KopiaExecutor) ListSnapshots(repoPath string, password string, sourcePath string) ([]SnapshotInfo, error) {
	args := []string{"snapshot", "list", "--json"}
	
	if repoPath != "" {
		args = append(args, "--repo-path", repoPath)
	}
	
	if password != "" {
		args = append(args, "--password", password)
	}
	
	if sourcePath != "" {
		args = append(args, "--path", sourcePath)
	}
	
	cmd := exec.Command(k.kopiaPath, args...)
	cmd.Env = append(os.Environ())
	
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to list snapshots: %w", err)
	}
	
	var snapshots []SnapshotInfo
	if err := json.Unmarshal(output, &snapshots); err != nil {
		// Try to parse non-JSON output
		return k.parseSnapshotList(string(output))
	}
	
	return snapshots, nil
}

// GetSnapshotContents lists contents of a snapshot
func (k *KopiaExecutor) GetSnapshotContents(snapshotID, repoPath string, password string, recursive bool) ([]FileInfo, error) {
	args := []string{"snapshot", "ls", snapshotID, "--json"}
	
	if repoPath != "" {
		args = append(args, "--repo-path", repoPath)
	}
	
	if password != "" {
		args = append(args, "--password", password)
	}
	
	if recursive {
		args = append(args, "--recursive")
	}
	
	cmd := exec.Command(k.kopiaPath, args...)
	
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to get snapshot contents: %w", err)
	}
	
	var files []FileInfo
	if err := json.Unmarshal(output, &files); err != nil {
		return k.parseFileList(string(output))
	}
	
	return files, nil
}

// MountSnapshot mounts a snapshot to a directory
func (k *KopiaExecutor) MountSnapshot(snapshotID, mountPath, repoPath string, password string) (int, error) {
	args := []string{"mount", snapshotID, mountPath}
	
	if repoPath != "" {
		args = append(args, "--repo-path", repoPath)
	}
	
	if password != "" {
		args = append(args, "--password", password)
	}
	
	logInfo("Mounting snapshot %s to %s", snapshotID, mountPath)
	
	cmd := exec.Command(k.kopiaPath, args...)
	
	if err := cmd.Start(); err != nil {
		return 0, fmt.Errorf("mount failed: %w", err)
	}
	
	logInfo("Mount started with PID %d", cmd.Process.Pid)
	return cmd.Process.Pid, nil
}

// CancelTask cancels a running task
func (k *KopiaExecutor) CancelTask(taskID string) bool {
	k.tasksMutex.Lock()
	defer k.tasksMutex.Unlock()
	
	cmd, exists := k.activeTasks[taskID]
	if !exists {
		return false
	}
	
	if err := cmd.Process.Kill(); err != nil {
		logError("Failed to cancel task %s: %v", taskID, err)
		return false
	}
	
	logInfo("Task %s cancelled", taskID)
	return true
}

// ConnectRepository connects to an existing repository
func (k *KopiaExecutor) ConnectRepository(repoConfig *RepositoryConfig) error {
	args := []string{"repository", "connect"}
	
	switch repoConfig.Type {
	case "filesystem":
		args = append(args, "filesystem", "--path", repoConfig.Path)
	case "s3":
		args = append(args, "s3",
			"--bucket", repoConfig.Bucket,
			"--endpoint", repoConfig.Endpoint,
		)
		if repoConfig.AccessKey != "" {
			args = append(args, "--access-key-id", repoConfig.AccessKey)
		}
		if repoConfig.SecretKey != "" {
			args = append(args, "--secret-access-key", repoConfig.SecretKey)
		}
	case "azure":
		args = append(args, "azure", "--container", repoConfig.Bucket)
	case "gcs":
		args = append(args, "gcs", "--bucket", repoConfig.Bucket)
	default:
		return fmt.Errorf("unsupported repository type: %s", repoConfig.Type)
	}
	
	if repoConfig.Password != "" {
		args = append(args, "--password", repoConfig.Password)
	}
	
	if repoConfig.ConfigPath != "" {
		args = append(args, "--config-file", repoConfig.ConfigPath)
	}
	
	cmd := exec.Command(k.kopiaPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to connect to repository: %w - %s", err, string(output))
	}
	
	logInfo("Connected to repository: %s", repoConfig.Type)
	return nil
}

// CreateRepository creates a new repository
func (k *KopiaExecutor) CreateRepository(repoConfig *RepositoryConfig) error {
	args := []string{"repository", "create"}
	
	switch repoConfig.Type {
	case "filesystem":
		args = append(args, "filesystem", "--path", repoConfig.Path)
	case "s3":
		args = append(args, "s3",
			"--bucket", repoConfig.Bucket,
			"--endpoint", repoConfig.Endpoint,
		)
		if repoConfig.AccessKey != "" {
			args = append(args, "--access-key-id", repoConfig.AccessKey)
		}
		if repoConfig.SecretKey != "" {
			args = append(args, "--secret-access-key", repoConfig.SecretKey)
		}
	default:
		return fmt.Errorf("unsupported repository type: %s", repoConfig.Type)
	}
	
	if repoConfig.Password != "" {
		args = append(args, "--password", repoConfig.Password)
	}
	
	cmd := exec.Command(k.kopiaPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to create repository: %w - %s", err, string(output))
	}
	
	logInfo("Created repository: %s", repoConfig.Type)
	return nil
}

// VerifyRepository verifies repository connectivity
func (k *KopiaExecutor) VerifyRepository(repoPath string, password string) error {
	args := []string{"repository", "status"}
	
	if repoPath != "" {
		args = append(args, "--repo-path", repoPath)
	}
	
	if password != "" {
		args = append(args, "--password", password)
	}
	
	cmd := exec.Command(k.kopiaPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("repository verification failed: %w - %s", err, string(output))
	}
	
	return nil
}

// parseSnapshotID extracts snapshot ID from Kopia output
func (k *KopiaExecutor) parseSnapshotID(output string) string {
	scanner := bufio.NewScanner(strings.NewReader(output))
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(strings.ToLower(line), "snapshot") {
			parts := strings.Fields(line)
			if len(parts) >= 2 {
				return parts[0]
			}
		}
	}
	return ""
}

// parseSnapshotList parses snapshot list from non-JSON output
func (k *KopiaExecutor) parseSnapshotList(output string) ([]SnapshotInfo, error) {
	var snapshots []SnapshotInfo
	scanner := bufio.NewScanner(strings.NewReader(output))
	
	for scanner.Scan() {
		line := scanner.Text()
		if strings.TrimSpace(line) == "" {
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

// parseFileList parses file list from non-JSON output
func (k *KopiaExecutor) parseFileList(output string) ([]FileInfo, error) {
	var files []FileInfo
	scanner := bufio.NewScanner(strings.NewReader(output))
	
	for scanner.Scan() {
		line := scanner.Text()
		if strings.TrimSpace(line) == "" {
			continue
		}
		
		// Parse line format: "drwxr-xr-x  100 2024-01-01 12:00 dirname/"
		// or: "-rw-r--r--  1000 2024-01-01 12:00 filename"
		parts := strings.Fields(line)
		if len(parts) >= 4 {
			fileType := "file"
			if strings.HasPrefix(parts[0], "d") {
				fileType = "dir"
			}
			
			name := parts[len(parts)-1]
			files = append(files, FileInfo{
				Name: name,
				Type: fileType,
				Mode: parts[0],
			})
		}
	}
	
	return files, nil
}
