package logger

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sync"
	"time"
)

// LogLevel defines the log level
type LogLevel string

const (
	LevelDebug LogLevel = "debug"
	LevelInfo  LogLevel = "info"
	LevelWarn  LogLevel = "warn"
	LevelError LogLevel = "error"
	LevelFatal LogLevel = "fatal"
)

// Logger interface for logging
type Logger interface {
	Debug(msg string, fields map[string]interface{})
	Info(msg string, fields map[string]interface{})
	Warn(msg string, fields map[string]interface{})
	Error(msg string, fields map[string]interface{})
	Fatal(msg string, fields map[string]interface{})
	SetLevel(level LogLevel)
}

// StructuredLogger implements structured logging
type StructuredLogger struct {
	level     LogLevel
	mu        sync.Mutex
	output    io.Writer
	jsonOutput bool
}

// LogEntry represents a log entry
type LogEntry struct {
	Level     LogLevel              `json:"level"`
	Timestamp string                 `json:"timestamp"`
	Message   string                 `json:"message"`
	Fields    map[string]interface{} `json:"fields,omitempty"`
	TaskID    string                 `json:"task_id,omitempty"`
	Service   string                 `json:"service"`
}

// NewLogger creates a new structured logger
func NewLogger(service string, level LogLevel, jsonOutput bool) *StructuredLogger {
	return &StructuredLogger{
		level:     level,
		output:    os.Stdout,
		jsonOutput: jsonOutput,
	}
}

// NewFileLogger creates a logger that writes to a file
func NewFileLogger(service, filepath string, level LogLevel, jsonOutput bool) (*StructuredLogger, error) {
	file, err := os.OpenFile(filepath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return nil, err
	}

	return &StructuredLogger{
		level:     level,
		output:    file,
		jsonOutput: jsonOutput,
	}, nil
}

// SetLevel sets the log level
func (l *StructuredLogger) SetLevel(level LogLevel) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.level = level
}

// SetJSONOutput sets whether to output JSON
func (l *StructuredLogger) SetJSONOutput(enabled bool) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.jsonOutput = enabled
}

// log writes a log entry
func (l *StructuredLogger) log(level LogLevel, msg string, fields map[string]interface{}, taskID string) {
	entry := LogEntry{
		Level:     level,
		Timestamp: time.Now().Format(time.RFC3339),
		Message:   msg,
		Fields:    fields,
		TaskID:    taskID,
		Service:   "hyperfilelens-proxy",
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	var output []byte
	var err error

	if l.jsonOutput {
		output, err = json.Marshal(entry)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Failed to marshal log entry: %v\n", err)
			return
		}
	} else {
		// Text format
		output = []byte(fmt.Sprintf("[%s] %s %s", entry.Level, entry.Timestamp, entry.Message))
		if taskID != "" {
			output = append(output, []byte(fmt.Sprintf(" [task=%s]", taskID))...)
		}
		for k, v := range fields {
			output = append(output, []byte(fmt.Sprintf(" %s=%v", k, v))...)
		}
		output = append(output, '\n')
	}

	_, err = l.output.Write(output)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to write log: %v\n", err)
	}
}

// Debug logs a debug message
func (l *StructuredLogger) Debug(msg string, fields map[string]interface{}) {
	if l.level == LevelDebug {
		l.log(LevelDebug, msg, fields, "")
	}
}

// Info logs an info message
func (l *StructuredLogger) Info(msg string, fields map[string]interface{}) {
	if l.level == LevelDebug || l.level == LevelInfo {
		l.log(LevelInfo, msg, fields, "")
	}
}

// Warn logs a warning message
func (l *StructuredLogger) Warn(msg string, fields map[string]interface{}) {
	if l.level == LevelDebug || l.level == LevelInfo || l.level == LevelWarn {
		l.log(LevelWarn, msg, fields, "")
	}
}

// Error logs an error message
func (l *StructuredLogger) Error(msg string, fields map[string]interface{}) {
	l.log(LevelError, msg, fields, "")
}

// Fatal logs a fatal message and exits
func (l *StructuredLogger) Fatal(msg string, fields map[string]interface{}) {
	l.log(LevelFatal, msg, fields, "")
	os.Exit(1)
}

// WithTask returns a logger with a task ID
func (l *StructuredLogger) WithTask(taskID string) *TaskLogger {
	return &TaskLogger{
		logger: l,
		taskID: taskID,
	}
}

// TaskLogger adds task ID to all log entries
type TaskLogger struct {
	logger *StructuredLogger
	taskID string
}

// Debug logs a debug message with task ID
func (tl *TaskLogger) Debug(msg string, fields map[string]interface{}) {
	tl.logger.log(LevelDebug, msg, fields, tl.taskID)
}

// Info logs an info message with task ID
func (tl *TaskLogger) Info(msg string, fields map[string]interface{}) {
	tl.logger.log(LevelInfo, msg, fields, tl.taskID)
}

// Warn logs a warning message with task ID
func (tl *TaskLogger) Warn(msg string, fields map[string]interface{}) {
	tl.logger.log(LevelWarn, msg, fields, tl.taskID)
}

// Error logs an error message with task ID
func (tl *TaskLogger) Error(msg string, fields map[string]interface{}) {
	tl.logger.log(LevelError, msg, fields, tl.taskID)
}

// Fatal logs a fatal message with task ID
func (tl *TaskLogger) Fatal(msg string, fields map[string]interface{}) {
	tl.logger.log(LevelFatal, msg, fields, tl.taskID)
	os.Exit(1)
}

// Global logger instance
var defaultLogger = NewLogger("proxy", LevelInfo, false)

// Package-level functions for convenience
func SetLevel(level LogLevel) {
	defaultLogger.SetLevel(level)
}

func SetJSONOutput(enabled bool) {
	defaultLogger.SetJSONOutput(enabled)
}

func SetOutput(w io.Writer) {
	defaultLogger.mu.Lock()
	defaultLogger.output = w
	defaultLogger.mu.Unlock()
}

func Debug(msg string, fields map[string]interface{}) {
	defaultLogger.Debug(msg, fields)
}

func Info(msg string, fields map[string]interface{}) {
	defaultLogger.Info(msg, fields)
}

func Warn(msg string, fields map[string]interface{}) {
	defaultLogger.Warn(msg, fields)
}

func Error(msg string, fields map[string]interface{}) {
	defaultLogger.Error(msg, fields)
}

func Fatal(msg string, fields map[string]interface{}) {
	defaultLogger.Fatal(msg, fields)
}

func WithTask(taskID string) *TaskLogger {
	return defaultLogger.WithTask(taskID)
}