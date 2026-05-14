package kopia

import (
	"bufio"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/hyperfilelens/proxy/logger"
	"github.com/hyperfilelens/proxy/traffic"
)

// Client wraps Kopia operations with enhanced features
type Client struct {
	binaryPath  string
	indexPath   string
	cachePath   string
	rateLimiter *traffic.RateLimiter
	mu          sync.Mutex
	compression CompressionConfig
}

// CompressionConfig defines compression settings
type CompressionConfig struct {
	Enabled   bool
	Level     int    // 0-9, where 0 is no compression, 9 is maximum
	Algorithm string // gzip, zstd, lz4
}

// Snapshot represents a Kopia snapshot
type Snapshot struct {
	ID        string           `json:"id"`
	Manifest  SnapshotManifest `json:"manifest"`
	Root      string           `json:"root"`
	CreatedAt string           `json:"created_at"`
	Size      int64            `json:"size"`
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

// BackupFileEntry captures a file entry returned from a Kopia snapshot browser request.
type BackupFileEntry struct {
	OriginalPath string `json:"original_path,omitempty"`
	RelativePath string `json:"relative_path"`
	FileName     string `json:"file_name"`
	Size         int64  `json:"size"`
	Type         string `json:"type,omitempty"`
	Mode         string `json:"mode,omitempty"`
	ModifiedAt   string `json:"modified_at,omitempty"`
}

// BackupResult captures the high-level Kopia snapshot command result.
type BackupResult struct {
	TaskID         string    `json:"task_id"`
	SourcePath     string    `json:"source_path"`
	Output         string    `json:"output"`
	TotalFiles     int       `json:"total_files,omitempty"`
	BackedUpFiles  int       `json:"backed_up_files,omitempty"`
	TotalSize      int64     `json:"total_size,omitempty"`
	BackedUpSize   int64     `json:"backed_up_size,omitempty"`
	BytesPerSecond int64     `json:"bytes_per_second,omitempty"`
	StartedAt      time.Time `json:"started_at"`
	FinishedAt     time.Time `json:"finished_at"`
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
	RepositoryID  string                   `json:"repository_id"`
	Path          string                   `json:"path"`
	Output        string                   `json:"output"`
	AlreadyExists bool                     `json:"already_exists"`
	Steps         []map[string]interface{} `json:"steps,omitempty"`
	CreatedAt     time.Time                `json:"created_at"`
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
			Enabled:   false,
			Level:     6,
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
	args, repositoryPath := repositoryCommandArgs("connect", repoConfig, password)
	if len(args) == 0 {
		return fmt.Errorf("repository configuration is required")
	}

	logger.Debug("Executing kopia repository connect", map[string]interface{}{
		"repository_path": repositoryPath,
		"args":            sanitizeArgs(args),
		"password":        "[REDACTED]",
	})

	output, err := exec.CommandContext(context.Background(), c.binaryPath, args...).CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to connect repository: %w, output: %s", err, string(output))
	}
	return nil
}

// CreateRepo initializes a Kopia repository using the legacy dispatcher payload shape.
func (c *Client) CreateRepo(repoConfig map[string]interface{}, password string) (*CreateRepoResult, error) {
	args, repositoryPath := repositoryCommandArgs("create", repoConfig, password)
	if len(args) == 0 {
		logger.Error("Repository URL is required", nil)
		return nil, fmt.Errorf("repository configuration is required")
	}

	logger.Debug("Executing kopia repository create", map[string]interface{}{
		"repository_path": repositoryPath,
		"args":            sanitizeArgs(args),
		"password":        "[REDACTED]",
	})

	output, err := exec.CommandContext(context.Background(), c.binaryPath, args...).CombinedOutput()
	if err != nil {
		logger.Error("Kopia repository creation failed", map[string]interface{}{
			"error":  err.Error(),
			"output": string(output),
		})
		return nil, fmt.Errorf("failed to create repository: %w, output: %s", err, string(output))
	}

	logger.Info("Repository created successfully", map[string]interface{}{
		"output": string(output),
	})

	return &CreateRepoResult{
		RepositoryID: stringFromMap(repoConfig, "id", ""),
		Path:         repositoryPath,
		Output:       string(output),
		CreatedAt:    time.Now(),
	}, nil
}

// Backup creates a Kopia snapshot for a source path.
func (c *Client) Backup(taskID, sourcePath, password string) (*BackupResult, error) {
	startedAt := time.Now()
	logger.Debug("Starting Kopia backup", map[string]interface{}{
		"task_id":     taskID,
		"source_path": sourcePath,
		"password":    "[REDACTED]",
	})

	args := []string{"snapshot", "create", sourcePath}
	logger.Debug("Executing kopia snapshot create", map[string]interface{}{
		"source_path": sourcePath,
	})

	output, err := exec.CommandContext(context.Background(), c.binaryPath, args...).CombinedOutput()
	if err != nil {
		logger.Error("Kopia backup failed", map[string]interface{}{
			"task_id":     taskID,
			"error":       err.Error(),
			"output":      string(output),
			"source_path": sourcePath,
		})
		return nil, fmt.Errorf("kopia backup failed: %w, output: %s", err, string(output))
	}

	logger.Info("Backup completed successfully", map[string]interface{}{
		"task_id":     taskID,
		"source_path": sourcePath,
		"output":      string(output),
	})

	return &BackupResult{
		TaskID:     taskID,
		SourcePath: sourcePath,
		Output:     string(output),
		StartedAt:  startedAt,
		FinishedAt: time.Now(),
	}, nil
}

// BackupWithProgress creates a Kopia snapshot and streams parsed progress updates.
func (c *Client) BackupWithProgress(taskID, sourcePath, password string, onProgress func(BackupProgress)) (*BackupResult, error) {
	startedAt := time.Now()
	args := []string{"snapshot", "create", sourcePath}

	logger.Debug("Executing kopia snapshot create with streaming progress", map[string]interface{}{
		"task_id":     taskID,
		"source_path": sourcePath,
	})

	cmd := exec.CommandContext(context.Background(), c.binaryPath, args...)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to open kopia stdout: %w", err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to open kopia stderr: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to start kopia backup: %w", err)
	}

	var outputMu sync.Mutex
	var outputBuilder strings.Builder
	progressState := BackupProgress{StartedAt: startedAt}
	consume := func(reader io.Reader) {
		scanner := bufio.NewScanner(reader)
		scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
		scanner.Split(splitKopiaProgress)
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line == "" {
				continue
			}
			outputMu.Lock()
			outputBuilder.WriteString(line)
			outputBuilder.WriteByte('\n')
			outputMu.Unlock()

			if parsed, ok := parseBackupProgressLine(line, startedAt); ok {
				progressState = mergeBackupProgress(progressState, parsed)
				if onProgress != nil {
					onProgress(progressState)
				}
			}
		}
	}

	done := make(chan struct{}, 2)
	go func() {
		consume(stdout)
		done <- struct{}{}
	}()
	go func() {
		consume(stderr)
		done <- struct{}{}
	}()
	<-done
	<-done

	waitErr := cmd.Wait()
	output := outputBuilder.String()
	if waitErr != nil {
		logger.Error("Kopia backup failed", map[string]interface{}{
			"task_id":     taskID,
			"source_path": sourcePath,
			"error":       waitErr.Error(),
			"output":      output,
		})
		return nil, fmt.Errorf("kopia backup failed: %w, output: %s", waitErr, output)
	}

	finalFiles, finalSize := parseFinalSnapshotStats(output)
	if finalFiles > 0 {
		progressState.ProcessedFiles = finalFiles
		progressState.TotalFiles = finalFiles
	}
	if finalSize > 0 {
		progressState.ProcessedBytes = finalSize
		progressState.TotalBytes = finalSize
	}
	bytesPerSecond := int64(0)
	elapsed := time.Since(startedAt).Seconds()
	if elapsed > 0 && progressState.ProcessedBytes > 0 {
		bytesPerSecond = int64(float64(progressState.ProcessedBytes) / elapsed)
	}

	logger.Info("Backup completed successfully", map[string]interface{}{
		"task_id":     taskID,
		"source_path": sourcePath,
	})

	return &BackupResult{
		TaskID:         taskID,
		SourcePath:     sourcePath,
		Output:         output,
		TotalFiles:     progressState.TotalFiles,
		BackedUpFiles:  progressState.ProcessedFiles,
		TotalSize:      progressState.TotalBytes,
		BackedUpSize:   progressState.ProcessedBytes,
		BytesPerSecond: bytesPerSecond,
		StartedAt:      startedAt,
		FinishedAt:     time.Now(),
	}, nil
}

// Restore restores a Kopia snapshot to a target path.
func (c *Client) Restore(taskID, snapshotID, targetPath, password string, overwrite bool) (*RestoreResult, error) {
	startedAt := time.Now()
	logger.Debug("Starting Kopia restore", map[string]interface{}{
		"task_id":     taskID,
		"snapshot_id": snapshotID,
		"target_path": targetPath,
		"overwrite":   overwrite,
		"password":    "[REDACTED]",
	})

	args := []string{"snapshot", "restore", snapshotID, targetPath}
	if overwrite {
		args = append(args, "--overwrite")
	}

	logger.Debug("Executing kopia snapshot restore", map[string]interface{}{
		"snapshot_id": snapshotID,
		"target_path": targetPath,
		"overwrite":   overwrite,
	})

	output, err := exec.CommandContext(context.Background(), c.binaryPath, args...).CombinedOutput()
	if err != nil {
		logger.Error("Kopia restore failed", map[string]interface{}{
			"task_id":     taskID,
			"snapshot_id": snapshotID,
			"target_path": targetPath,
			"error":       err.Error(),
			"output":      string(output),
		})
		return nil, fmt.Errorf("kopia restore failed: %w, output: %s", err, string(output))
	}

	logger.Info("Restore completed successfully", map[string]interface{}{
		"task_id":     taskID,
		"snapshot_id": snapshotID,
		"target_path": targetPath,
		"output":      string(output),
	})

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
	logger.Debug("Starting Kopia snapshot list", map[string]interface{}{
		"password": "[REDACTED]",
	})

	output, err := exec.CommandContext(context.Background(), c.binaryPath, "snapshot", "list", "--json").CombinedOutput()
	if err != nil {
		logger.Error("Failed to list snapshots", map[string]interface{}{
			"error":  err.Error(),
			"output": string(output),
		})
		return nil, fmt.Errorf("failed to list snapshots: %w, output: %s", err, string(output))
	}

	logger.Debug("Snapshots listed successfully", map[string]interface{}{
		"output_length": len(output),
		"password":      "[REDACTED]",
	})

	return string(output), nil
}

// ListSnapshotFiles lists files inside a Kopia snapshot root object on demand.
func (c *Client) ListSnapshotFiles(objectID, path, password string) ([]BackupFileEntry, error) {
	path = strings.TrimSpace(path)
	objectPath := strings.TrimRight(objectID, "/")
	if path != "" {
		objectPath = objectPath + "/" + strings.TrimLeft(path, "/")
	}
	args := []string{"ls", "--long", objectPath}

	logger.Debug("Executing kopia snapshot file browser", map[string]interface{}{
		"object_id":   objectID,
		"object_path": objectPath,
		"path":        path,
	})

	output, err := exec.CommandContext(context.Background(), c.binaryPath, args...).CombinedOutput()
	if err != nil {
		logger.Error("Kopia object ls failed", map[string]interface{}{
			"object_id": objectID,
			"path":      path,
			"error":     err.Error(),
			"output":    string(output),
		})
		return nil, fmt.Errorf("failed to list snapshot files: %w, output: %s", err, string(output))
	}
	return parseSnapshotFilesText(string(output), path), nil
}

// BackupProgress is the subset of Kopia CLI progress that can be parsed safely.
type BackupProgress struct {
	ProcessedFiles int
	TotalFiles     int
	ProcessedBytes int64
	TotalBytes     int64
	Percent        int
	SpeedMBps      float64
	ETA            string
	StartedAt      time.Time
}

func splitKopiaProgress(data []byte, atEOF bool) (advance int, token []byte, err error) {
	for i, b := range data {
		if b == '\n' || b == '\r' {
			return i + 1, data[:i], nil
		}
	}
	if atEOF && len(data) > 0 {
		return len(data), data, nil
	}
	return 0, nil, nil
}

func mergeBackupProgress(current, parsed BackupProgress) BackupProgress {
	if parsed.ProcessedFiles > 0 {
		current.ProcessedFiles = parsed.ProcessedFiles
		if parsed.ProcessedFiles > current.TotalFiles {
			current.TotalFiles = parsed.ProcessedFiles
		}
	}
	if parsed.ProcessedBytes > 0 {
		current.ProcessedBytes = parsed.ProcessedBytes
		if parsed.ProcessedBytes > current.TotalBytes {
			current.TotalBytes = parsed.ProcessedBytes
		}
	}
	if parsed.TotalBytes > 0 {
		current.TotalBytes = parsed.TotalBytes
	}
	if parsed.Percent > 0 {
		current.Percent = parsed.Percent
	}
	if parsed.SpeedMBps > 0 {
		current.SpeedMBps = parsed.SpeedMBps
	}
	if parsed.ETA != "" {
		current.ETA = parsed.ETA
	}
	if current.Percent == 0 && current.TotalBytes > 0 && current.ProcessedBytes > 0 {
		current.Percent = int(float64(current.ProcessedBytes) / float64(current.TotalBytes) * 100)
	}
	if current.SpeedMBps == 0 && !current.StartedAt.IsZero() && current.ProcessedBytes > 0 {
		elapsed := time.Since(current.StartedAt).Seconds()
		if elapsed > 0 {
			current.SpeedMBps = float64(current.ProcessedBytes) / elapsed / 1024 / 1024
		}
	}
	return current
}

func parseBackupProgressLine(line string, startedAt time.Time) (BackupProgress, bool) {
	progress := BackupProgress{StartedAt: startedAt}
	matches := regexp.MustCompile(`(\d+)\s+hashed\s+\(([\d.]+)\s*([KMGT]?B)\)`).FindStringSubmatch(line)
	if len(matches) == 4 {
		files, _ := strconv.Atoi(matches[1])
		progress.ProcessedFiles = files
		progress.ProcessedBytes = parseHumanBytes(matches[2], matches[3])
	}
	estimated := regexp.MustCompile(`estimated\s+([\d.]+)\s*([KMGT]?B)\s+\(([\d.]+)%\)`).FindStringSubmatch(line)
	if len(estimated) == 4 {
		progress.TotalBytes = parseHumanBytes(estimated[1], estimated[2])
		percent, _ := strconv.ParseFloat(estimated[3], 64)
		progress.Percent = int(percent)
	}
	if strings.Contains(line, "left") {
		etaMatch := regexp.MustCompile(`(\d+[smhd]\s*)+left`).FindString(line)
		progress.ETA = strings.TrimSuffix(strings.TrimSpace(etaMatch), " left")
	}
	return progress, progress.ProcessedFiles > 0 || progress.ProcessedBytes > 0 || progress.Percent > 0
}

func parseFinalSnapshotStats(output string) (int, int64) {
	matches := regexp.MustCompile(`(\d+)\s+hashed\s+\(([\d.]+)\s*([KMGT]?B)\)`).FindAllStringSubmatch(output, -1)
	if len(matches) == 0 {
		return 0, 0
	}
	last := matches[len(matches)-1]
	files, _ := strconv.Atoi(last[1])
	return files, parseHumanBytes(last[2], last[3])
}

func parseHumanBytes(value, unit string) int64 {
	number, _ := strconv.ParseFloat(value, 64)
	multiplier := float64(1)
	switch strings.ToUpper(unit) {
	case "KB":
		multiplier = 1024
	case "MB":
		multiplier = 1024 * 1024
	case "GB":
		multiplier = 1024 * 1024 * 1024
	case "TB":
		multiplier = 1024 * 1024 * 1024 * 1024
	}
	return int64(number * multiplier)
}

func parseSnapshotFilesJSON(output []byte, basePath string) ([]BackupFileEntry, error) {
	var raw interface{}
	if err := json.Unmarshal(output, &raw); err != nil {
		return nil, err
	}

	var items []interface{}
	switch value := raw.(type) {
	case []interface{}:
		items = value
	case map[string]interface{}:
		for _, key := range []string{"entries", "files", "items"} {
			if arr, ok := value[key].([]interface{}); ok {
				items = arr
				break
			}
		}
	}

	files := make([]BackupFileEntry, 0, len(items))
	for _, item := range items {
		obj, ok := item.(map[string]interface{})
		if !ok {
			continue
		}
		name := stringFromAny(obj["name"])
		path := stringFromAny(obj["path"])
		if path == "" {
			path = name
		}
		if basePath != "" && !strings.HasPrefix(path, basePath) {
			path = strings.Trim(strings.TrimRight(basePath, "/")+"/"+path, "/")
		}
		files = append(files, BackupFileEntry{
			RelativePath: path,
			FileName:     firstNonEmpty(name, filepath.Base(path)),
			Size:         int64FromAny(obj["size"]),
			Type:         stringFromAny(obj["type"]),
			Mode:         stringFromAny(obj["mode"]),
			ModifiedAt:   firstNonEmpty(stringFromAny(obj["mtime"]), stringFromAny(obj["modified_at"])),
		})
	}
	return files, nil
}

func parseSnapshotFilesText(output, basePath string) []BackupFileEntry {
	lines := strings.Split(output, "\n")
	files := make([]BackupFileEntry, 0, len(lines))
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "total ") {
			continue
		}
		fields := strings.Fields(line)
		name := fields[len(fields)-1]
		path := name
		if basePath != "" && !strings.HasPrefix(path, basePath) {
			path = strings.Trim(strings.TrimRight(basePath, "/")+"/"+path, "/")
		}
		files = append(files, BackupFileEntry{
			RelativePath: path,
			FileName:     filepath.Base(path),
			Size:         parseSizeFromFields(fields),
			Type:         parseTypeFromLine(line),
		})
	}
	return files
}

func parseTypeFromLine(line string) string {
	if line == "" {
		return ""
	}
	switch line[0] {
	case 'd':
		return "d"
	case '-':
		return "f"
	case 'l':
		return "l"
	default:
		return ""
	}
}

func parseSizeFromFields(fields []string) int64 {
	for _, field := range fields {
		if value, err := strconv.ParseInt(field, 10, 64); err == nil {
			return value
		}
	}
	return 0
}

func stringFromAny(value interface{}) string {
	if value == nil {
		return ""
	}
	switch v := value.(type) {
	case string:
		return v
	default:
		return fmt.Sprintf("%v", v)
	}
}

func int64FromAny(value interface{}) int64 {
	switch v := value.(type) {
	case int64:
		return v
	case int:
		return int64(v)
	case float64:
		return int64(v)
	case json.Number:
		result, _ := v.Int64()
		return result
	case string:
		result, _ := strconv.ParseInt(v, 10, 64)
		return result
	default:
		return 0
	}
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value != "" && value != "." {
			return value
		}
	}
	return ""
}

// Cancel is a placeholder for task cancellation. Kopia commands are currently run synchronously.
func (c *Client) Cancel(taskID string) {}

// SetCompression configures compression settings
func (c *Client) SetCompression(enabled bool, level int, algorithm string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.compression = CompressionConfig{
		Enabled:   enabled,
		Level:     level,
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
	logger.Debug("Starting Kopia repository connection", map[string]interface{}{
		"repository_url": repositoryURL,
		"password":       "[REDACTED]",
	})

	c.mu.Lock()
	defer c.mu.Unlock()

	args := []string{
		"repository", "connect", repositoryURL,
		"--index-path", c.indexPath,
		"--cache-dir", c.cachePath,
		"--password", password,
	}

	logger.Debug("Executing kopia repository connect", map[string]interface{}{
		"repository_url": repositoryURL,
		"index_path":     c.indexPath,
		"cache_dir":      c.cachePath,
		"password":       "[REDACTED]",
	})

	cmd := exec.CommandContext(ctx, c.binaryPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Error("Failed to connect to repository", map[string]interface{}{
			"repository_url": repositoryURL,
			"error":          err.Error(),
			"output":         string(output),
		})
		return fmt.Errorf("failed to connect to repository: %w, output: %s", err, string(output))
	}

	logger.Info("Connected to repository successfully", map[string]interface{}{
		"repository_url": repositoryURL,
	})

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

func repositoryCommandArgs(action string, repoConfig map[string]interface{}, password string) ([]string, string) {
	repoType := stringFromMap(repoConfig, "type", "filesystem")
	repositoryPath := repositoryURLFromConfig(repoConfig)

	switch repoType {
	case "nas", "nfs", "local", "filesystem":
		if repositoryPath == "" {
			return nil, ""
		}
		return []string{"repository", action, "filesystem", "--path", repositoryPath, "--password", password}, repositoryPath
	case "s3":
		bucket := stringFromMap(repoConfig, "bucket", "")
		if bucket == "" {
			return nil, ""
		}
		endpoint := s3EndpointFromConfig(repoConfig, bucket)
		displayPath := "s3://" + bucket
		if prefix := stringFromMap(repoConfig, "prefix", ""); prefix != "" {
			displayPath += "/" + strings.Trim(prefix, "/")
		}
		if endpoint != "" {
			displayPath += " endpoint=" + endpoint
		}
		args := []string{"repository", action, "s3", "--bucket", bucket, "--password", password}
		if endpoint != "" {
			args = append(args, "--endpoint", endpoint)
		}
		if region := stringFromMap(repoConfig, "region", ""); region != "" {
			args = append(args, "--region", region)
		}
		if prefix := stringFromMap(repoConfig, "prefix", ""); prefix != "" {
			args = append(args, "--prefix", prefix)
		}
		if accessKey := stringFromMap(repoConfig, "access_key", ""); accessKey != "" {
			args = append(args, "--access-key", accessKey)
		}
		if secretKey := stringFromMap(repoConfig, "secret_key", ""); secretKey != "" {
			args = append(args, "--secret-access-key", secretKey)
		}
		if !boolFromMap(repoConfig, "use_tls", true) {
			args = append(args, "--disable-tls")
		}
		return args, displayPath
	default:
		if repositoryPath == "" {
			return nil, ""
		}
		return []string{"repository", action, "filesystem", "--path", repositoryPath, "--password", password}, repositoryPath
	}
}

func s3EndpointFromConfig(repoConfig map[string]interface{}, bucket string) string {
	endpoint := strings.TrimSpace(stringFromMap(repoConfig, "endpoint", ""))
	if endpoint == "" {
		return ""
	}

	host := endpoint
	if parsed, err := url.Parse(endpoint); err == nil && parsed.Host != "" {
		host = parsed.Host
	} else {
		host = strings.Trim(endpoint, "/")
	}

	urlStyle := strings.ToLower(stringFromMap(repoConfig, "url_style", ""))
	if urlStyle == "virtual" && bucket != "" && !strings.HasPrefix(host, bucket+".") && isCustomS3Endpoint(host) {
		return bucket + "." + host
	}

	return host
}

func boolFromMap(m map[string]interface{}, key string, fallback bool) bool {
	if value, ok := m[key]; ok {
		if boolValue, ok := value.(bool); ok {
			return boolValue
		}
	}
	return fallback
}

func isCustomS3Endpoint(host string) bool {
	return !strings.Contains(host, "amazonaws.com") &&
		!strings.Contains(host, "googleapis.com") &&
		!strings.Contains(host, "aliyuncs.com")
}

func sanitizeArgs(args []string) []string {
	sanitized := make([]string, len(args))
	copy(sanitized, args)

	for i := 0; i < len(sanitized)-1; i++ {
		switch sanitized[i] {
		case "--password", "--access-key", "--secret-access-key", "--session-token":
			sanitized[i+1] = "[REDACTED]"
		}
	}

	return sanitized
}
