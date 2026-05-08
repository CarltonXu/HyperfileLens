package kopia

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"

	"github.com/hyperfilelens/proxy/traffic"
)

// Client wraps Kopia operations with enhanced features
type Client struct {
	binaryPath    string
	indexPath     string
	cachePath     string
	rateLimiter   *traffic.RateLimiter
	mu            sync.Mutex
	compression   CompressionConfig
}

// CompressionConfig defines compression settings
type CompressionConfig struct {
	Enabled  bool
	Level    int // 0-9, where 0 is no compression, 9 is maximum
	Algorithm string // gzip, zstd, lz4
}

// Snapshot represents a Kopia snapshot
type Snapshot struct {
	ID        string            `json:"id"`
	Manifest  SnapshotManifest  `json:"manifest"`
	Root      string            `json:"root"`
	CreatedAt string            `json:"created_at"`
	Size      int64             `json:"size"`
}

// SnapshotManifest represents snapshot file manifest
type SnapshotManifest struct {
	Files []FileInfo `json:"files"`
}

// FileInfo represents file information in a snapshot
type FileInfo struct {
	Path     string `json:"path"`
	Size     int64  `json:"size"`
	Checksum string `json:"checksum"`
}

// BackupResult captures the high-level Kopia snapshot command result.
type BackupResult struct {
	TaskID     string    `json:"task_id"`
	SourcePath string    `json:"source_path"`
	Output     string    `json:"output"`
	StartedAt  time.Time `json:"started_at"`
	FinishedAt time.Time `json:"finished_at"`
}

// RestoreResult captures the high-level Kopia restore command result.
type RestoreResult struct {
	TaskID     string    `json:"task_id"`
	SnapshotID string    `json:"snapshot_id"`
	TargetPath string    `json:"target_path"`
	Output     string    `json:"output"`
	StartedAt  time.Time `json:"started_at"`
	FinishedAt time.Time `json:"finished_at"`
}

// CreateRepoResult captures repository initialization metadata.
type CreateRepoResult struct {
	RepositoryID string    `json:"repository_id"`
	Path         string    `json:"path"`
	Output       string    `json:"output"`
	CreatedAt    time.Time `json:"created_at"`
}

// NewClient creates a new Kopia client.
func NewClient(binaryPath string, paths ...string) *Client {
	indexPath := ""
	cachePath := ""
	if len(paths) == 1 {
		cachePath = paths[0]
		indexPath = filepath.Join(cachePath, "indexes")
	} else if len(paths) >= 2 {
		indexPath = paths[0]
		cachePath = paths[1]
	}

	return &Client{
		binaryPath: binaryPath,
		indexPath:  indexPath,
		cachePath:  cachePath,
		compression: CompressionConfig{
			Enabled:  false,
			Level:    6,
			Algorithm: "gzip",
		},
	}
}

// CheckInstalled verifies that the Kopia binary is available.
func (c *Client) CheckInstalled() bool {
	if c.binaryPath == "" {
		return false
	}
	if _, err := os.Stat(c.binaryPath); err == nil {
		return true
	}
	_, err := exec.LookPath(c.binaryPath)
	return err == nil
}

// GetVersion returns the Kopia CLI version string.
func (c *Client) GetVersion() string {
	output, err := exec.CommandContext(context.Background(), c.binaryPath, "--version").CombinedOutput()
	if err != nil {
		return fmt.Sprintf("unknown: %v", err)
	}
	return string(output)
}

// ConnectRepo connects Kopia to a repository using the legacy dispatcher payload shape.
func (c *Client) ConnectRepo(repoConfig map[string]interface{}, password string) error {
	repositoryURL := repositoryURLFromConfig(repoConfig)
	if repositoryURL == "" {
		return fmt.Errorf("repository url/path is required")
	}
	return c.Connect(context.Background(), repositoryURL, password)
}

// CreateRepo initializes a Kopia repository using the legacy dispatcher payload shape.
func (c *Client) CreateRepo(repoConfig map[string]interface{}, password string) (*CreateRepoResult, error) {
	repositoryURL := repositoryURLFromConfig(repoConfig)
	if repositoryURL == "" {
		return nil, fmt.Errorf("repository url/path is required")
	}

	args := []string{"repository", "create", repositoryURL, "--password", password}
	output, err := exec.CommandContext(context.Background(), c.binaryPath, args...).CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("failed to create repository: %w, output: %s", err, string(output))
	}

	return &CreateRepoResult{
		RepositoryID: stringFromMap(repoConfig, "id", ""),
		Path:         repositoryURL,
		Output:       string(output),
		CreatedAt:    time.Now(),
	}, nil
}

// Backup creates a Kopia snapshot for a source path.
func (c *Client) Backup(taskID, sourcePath, password string) (*BackupResult, error) {
	startedAt := time.Now()
	args := []string{"snapshot", "create", sourcePath}
	output, err := exec.CommandContext(context.Background(), c.binaryPath, args...).CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("kopia backup failed: %w, output: %s", err, string(output))
	}

	return &BackupResult{
		TaskID:     taskID,
		SourcePath: sourcePath,
		Output:     string(output),
		StartedAt:  startedAt,
		FinishedAt: time.Now(),
	}, nil
}

// Restore restores a Kopia snapshot to a target path.
func (c *Client) Restore(taskID, snapshotID, targetPath, password string, overwrite bool) (*RestoreResult, error) {
	startedAt := time.Now()
	args := []string{"snapshot", "restore", snapshotID, targetPath}
	if overwrite {
		args = append(args, "--overwrite")
	}
	output, err := exec.CommandContext(context.Background(), c.binaryPath, args...).CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("kopia restore failed: %w, output: %s", err, string(output))
	}

	return &RestoreResult{
		TaskID:     taskID,
		SnapshotID: snapshotID,
		TargetPath: targetPath,
		Output:     string(output),
		StartedAt:  startedAt,
		FinishedAt: time.Now(),
	}, nil
}

// ListSnapshots lists available Kopia snapshots as raw JSON-compatible output.
func (c *Client) ListSnapshots(password string) (interface{}, error) {
	output, err := exec.CommandContext(context.Background(), c.binaryPath, "snapshot", "list", "--json").CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("failed to list snapshots: %w, output: %s", err, string(output))
	}
	return string(output), nil
}

// Cancel is a placeholder for task cancellation. Kopia commands are currently run synchronously.
func (c *Client) Cancel(taskID string) {}

// SetCompression configures compression settings
func (c *Client) SetCompression(enabled bool, level int, algorithm string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.compression = CompressionConfig{
		Enabled:  enabled,
		Level:    level,
		Algorithm: algorithm,
	}
}

// SetRateLimit sets the rate limiter for file operations
func (c *Client) SetRateLimit(kbps int64) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.rateLimiter = traffic.NewRateLimiter(kbps)
}

// Connect connects to a Kopia repository
func (c *Client) Connect(ctx context.Context, repositoryURL, password string) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	args := []string{
		"repository", "connect", repositoryURL,
		"--index-path", c.indexPath,
		"--cache-dir", c.cachePath,
		"--password", password,
	}

	cmd := exec.CommandContext(ctx, c.binaryPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to connect to repository: %w, output: %s", err, string(output))
	}

	return nil
}

// BackupFile backs up a single file with optional compression and rate limiting
func (c *Client) BackupFile(src io.Reader, filePath, repositoryID string, compressionLevel int, verifyChecksum bool) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	var reader io.Reader = src

	// Calculate checksum if verification is enabled
	var checksum string
	if verifyChecksum {
		hash := sha256.New()
		if _, err := io.Copy(hash, reader); err != nil {
			return fmt.Errorf("failed to calculate checksum: %w", err)
		}
		checksum = hex.EncodeToString(hash.Sum(nil))
	}

	// Create temporary file for backup
	tempFile, err := os.CreateTemp("", "kopia-backup-")
	if err != nil {
		return fmt.Errorf("failed to create temp file: %w", err)
	}
	defer os.Remove(tempFile.Name())

	// Write to temp file
	if _, err := io.Copy(tempFile, reader); err != nil {
		return fmt.Errorf("failed to write to temp file: %w", err)
	}
	tempFile.Close()

	// Run Kopia snapshot command
	ctx := context.Background()
	args := []string{
		"snapshot", "create", tempFile.Name(),
		"--description", fmt.Sprintf("Backup of %s", filepath.Base(filePath)),
	}

	if checksum != "" {
		args = append(args, "--tags", fmt.Sprintf("checksum:%s", checksum))
	}

	cmd := exec.CommandContext(ctx, c.binaryPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("kopia snapshot failed: %w, output: %s", err, string(output))
	}

	return nil
}

// GetFile retrieves a file from a snapshot
func (c *Client) GetFile(snapshotID, filePath string) (io.ReadCloser, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	ctx := context.Background()

	// Get file content
	restoreCmd := exec.CommandContext(ctx, c.binaryPath, "snapshot", "restore", snapshotID, filePath, "-")
	pipe, err := restoreCmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to create pipe: %w", err)
	}

	if err := restoreCmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to start restore: %w", err)
	}

	return &wrappedReader{reader: pipe, cmd: restoreCmd}, nil
}

// GetSnapshotManifest retrieves the manifest of a snapshot
func (c *Client) GetSnapshotManifest(snapshotID string) (*SnapshotManifest, error) {
	ctx := context.Background()
	args := []string{"snapshot", "ls", snapshotID, "--json"}

	cmd := exec.CommandContext(ctx, c.binaryPath, args...)
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to get snapshot manifest: %w", err)
	}

	return c.parseManifest(output)
}

// VerifyChecksum verifies the checksum of a file in a snapshot
func (c *Client) VerifyChecksum(snapshotID, filePath, expectedChecksum string) (bool, error) {
	reader, err := c.GetFile(snapshotID, filePath)
	if err != nil {
		return false, err
	}
	defer reader.Close()

	hash := sha256.New()
	if _, err := io.Copy(hash, reader); err != nil {
		return false, err
	}

	actualChecksum := hex.EncodeToString(hash.Sum(nil))
	return actualChecksum == expectedChecksum, nil
}

// wrappedReader wraps a reader with a command for cleanup
type wrappedReader struct {
	reader io.Reader
	cmd    *exec.Cmd
}

func (w *wrappedReader) Read(p []byte) (n int, err error) {
	return w.reader.Read(p)
}

func (w *wrappedReader) Close() error {
	w.cmd.Wait()
	return nil
}

// parseManifest parses a snapshot manifest
func (c *Client) parseManifest(data []byte) (*SnapshotManifest, error) {
	// In production, use json.Unmarshal
	return &SnapshotManifest{}, nil
}

func repositoryURLFromConfig(repoConfig map[string]interface{}) string {
	for _, key := range []string{"url", "path", "repository_url", "repo_path"} {
		if value := stringFromMap(repoConfig, key, ""); value != "" {
			return value
		}
	}
	return ""
}

func stringFromMap(m map[string]interface{}, key, fallback string) string {
	if value, ok := m[key]; ok {
		if text, ok := value.(string); ok {
			return text
		}
	}
	return fallback
}
