package utils

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/hyperfilelens/proxy/logger"
)

// EnsureDir creates directory if not exists
func EnsureDir(path string) error {
	return os.MkdirAll(path, 0755)
}

// FileExists checks if file exists
func FileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// IsDir checks if path is directory
func IsDir(path string) bool {
	info, err := os.Stat(path)
	if err != nil {
		return false
	}
	return info.IsDir()
}

// GetFileSize returns file size
func GetFileSize(path string) int64 {
	info, err := os.Stat(path)
	if err != nil {
		return 0
	}
	return info.Size()
}

// FormatBytes formats bytes to human readable string
func FormatBytes(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

// FormatDuration formats duration to human readable string
func FormatDuration(d time.Duration) string {
	if d < time.Minute {
		return fmt.Sprintf("%.1fs", d.Seconds())
	}
	if d < time.Hour {
		return fmt.Sprintf("%.1fm", d.Minutes())
	}
	return fmt.Sprintf("%.1fh", d.Hours())
}

// ExpandPath expands ~ and environment variables in path
func ExpandPath(path string) string {
	if len(path) > 0 && path[0] == '~' {
		home, _ := os.UserHomeDir()
		path = filepath.Join(home, path[1:])
	}
	return os.ExpandEnv(path)
}

// WritePIDFile writes PID to file
func WritePIDFile(path string) error {
	pid := os.Getpid()
	return os.WriteFile(path, []byte(fmt.Sprintf("%d", pid)), 0644)
}

// ReadPIDFile reads PID from file
func ReadPIDFile(path string) (int, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0, err
	}

	var pid int
	_, err = fmt.Sscanf(string(data), "%d", &pid)
	return pid, err
}

// Timestamp returns current timestamp in ISO format
func Timestamp() string {
	return time.Now().Format(time.RFC3339)
}

// LogInfo logs info message using the logger package
func LogInfo(format string, args ...interface{}) {
	logger.Info(fmt.Sprintf(format, args...), nil)
}

// LogError logs error message using the logger package
func LogError(format string, args ...interface{}) {
	logger.Error(fmt.Sprintf(format, args...), nil)
}

// LogWarn logs warning message using the logger package
func LogWarn(format string, args ...interface{}) {
	logger.Warn(fmt.Sprintf(format, args...), nil)
}

// LogDebug logs debug message using the logger package
func LogDebug(format string, args ...interface{}) {
	logger.Debug(fmt.Sprintf(format, args...), nil)
}
