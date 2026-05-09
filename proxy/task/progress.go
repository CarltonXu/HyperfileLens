package task

import "time"

// Progress represents task progress information
type Progress struct {
	TaskID    string `json:"task_id"`
	TaskType  string `json:"task_type"`
	Status    string `json:"status"`   // running, completed, failed, cancelled
	Progress  int    `json:"progress"` // 0-100
	Message   string `json:"message"`
	Timestamp string `json:"timestamp"`

	// File-level progress (for backup/restore operations)
	CurrentFile     string `json:"current_file,omitempty"`
	TotalFiles      int    `json:"total_files,omitempty"`
	ProcessedFiles  int    `json:"processed_files,omitempty"`
	CurrentFileSize int64  `json:"current_file_size,omitempty"`
	ProcessedBytes  int64  `json:"processed_bytes,omitempty"`
	TotalBytes      int64  `json:"total_bytes,omitempty"`

	// Speed information
	SpeedMBps float64 `json:"speed_mbps,omitempty"`
	ETA       string  `json:"eta,omitempty"`

	// Error information
	LastError  string `json:"last_error,omitempty"`
	ErrorCount int    `json:"error_count,omitempty"`

	// Start and end times
	StartedAt  string `json:"started_at,omitempty"`
	FinishedAt string `json:"finished_at,omitempty"`
}

// ProgressUpdate represents a progress update message
type ProgressUpdate struct {
	Type      string   `json:"type"`
	ID        string   `json:"id"`
	Timestamp string   `json:"timestamp"`
	Payload   Progress `json:"payload"`
}

// NewProgress creates a new progress object
func NewProgress(taskID, taskType, message string) *Progress {
	return &Progress{
		TaskID:    taskID,
		TaskType:  taskType,
		Status:    StatusRunning,
		Progress:  0,
		Message:   message,
		Timestamp: time.Now().Format(time.RFC3339),
		StartedAt: time.Now().Format(time.RFC3339),
	}
}

// UpdateProgress updates the progress information
func (p *Progress) UpdateProgress(progress int, message string) {
	p.Progress = progress
	p.Message = message
	p.Timestamp = time.Now().Format(time.RFC3339)
}

// UpdateFileProgress updates file-level progress
func (p *Progress) UpdateFileProgress(currentFile string, processedBytes, totalBytes int64) {
	p.CurrentFile = currentFile
	p.ProcessedBytes = processedBytes
	p.TotalBytes = totalBytes

	if totalBytes > 0 {
		p.Progress = int(float64(processedBytes) / float64(totalBytes) * 100)
	}
	p.Timestamp = time.Now().Format(time.RFC3339)
}

// UpdateFileCount updates file count progress
func (p *Progress) UpdateFileCount(currentFile string, processedFiles, totalFiles int) {
	p.CurrentFile = currentFile
	p.ProcessedFiles = processedFiles
	p.TotalFiles = totalFiles

	if totalFiles > 0 {
		p.Progress = int(float64(processedFiles) / float64(totalFiles) * 100)
	}
	p.Timestamp = time.Now().Format(time.RFC3339)
}

// UpdateSpeed updates speed information
func (p *Progress) UpdateSpeed(speedMBps float64, eta string) {
	p.SpeedMBps = speedMBps
	p.ETA = eta
	p.Timestamp = time.Now().Format(time.RFC3339)
}

// UpdateError updates error information
func (p *Progress) UpdateError(lastError string) {
	p.LastError = lastError
	p.ErrorCount++
	p.Timestamp = time.Now().Format(time.RFC3339)
}

// MarkCompleted marks the task as completed
func (p *Progress) MarkCompleted(message string) {
	p.Status = StatusCompleted
	p.Progress = 100
	p.Message = message
	p.FinishedAt = time.Now().Format(time.RFC3339)
	p.Timestamp = time.Now().Format(time.RFC3339)
}

// MarkFailed marks the task as failed
func (p *Progress) MarkFailed(message string) {
	p.Status = StatusFailed
	p.Message = message
	p.FinishedAt = time.Now().Format(time.RFC3339)
	p.Timestamp = time.Now().Format(time.RFC3339)
}

// MarkCancelled marks the task as cancelled
func (p *Progress) MarkCancelled(message string) {
	p.Status = StatusCancelled
	p.Message = message
	p.FinishedAt = time.Now().Format(time.RFC3339)
	p.Timestamp = time.Now().Format(time.RFC3339)
}
