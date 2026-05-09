package task

import (
	"fmt"
	"sync"
	"time"
)

// ErrorType defines the type of error
type ErrorType string

const (
	ErrorTypeNetwork    ErrorType = "network"
	ErrorTypeStorage    ErrorType = "storage"
	ErrorTypeFilesystem ErrorType = "filesystem"
	ErrorTypeConfig     ErrorType = "config"
	ErrorTypeValidation ErrorType = "validation"
	ErrorTypeAuth       ErrorType = "authentication"
	ErrorTypeResource   ErrorType = "resource"
	ErrorTypeTimeout    ErrorType = "timeout"
	ErrorTypeCancel     ErrorType = "cancel"
	ErrorTypeUnknown    ErrorType = "unknown"
)

// ErrorSeverity defines the severity level of an error
type ErrorSeverity string

const (
	SeverityLow      ErrorSeverity = "low"
	SeverityMedium   ErrorSeverity = "medium"
	SeverityHigh     ErrorSeverity = "high"
	SeverityCritical ErrorSeverity = "critical"
)

// ErrorCategory defines the category of error
type ErrorCategory string

const (
	CategoryTransient     ErrorCategory = "transient"     // Temporary errors, can retry
	CategoryPermanent     ErrorCategory = "permanent"     // Permanent errors, cannot retry
	CategoryConfiguration ErrorCategory = "configuration" // Configuration errors
	CategoryPermission    ErrorCategory = "permission"    // Permission errors
)

// AppError represents an application error
type AppError struct {
	errorType ErrorType     `json:"type"`
	Category  ErrorCategory `json:"category"`
	Severity  ErrorSeverity `json:"severity"`
	Message   string        `json:"message"`
	Code      string        `json:"code,omitempty"`
	TaskID    string        `json:"task_id,omitempty"`
	Timestamp string        `json:"timestamp"`
	Retryable bool          `json:"retryable"`
	Original  error         `json:"-"` // Original error (not serialized)
}

// Error defines the interface for application errors
type Error interface {
	Error() string
	GetType() ErrorType
	GetCategory() ErrorCategory
	GetSeverity() ErrorSeverity
	IsRetryable() bool
	GetCode() string
}

// NewError creates a new application error
func NewError(errorType ErrorType, message string) *AppError {
	return &AppError{
		errorType: errorType,
		Message:   message,
		Severity:  SeverityMedium,
		Category:  CategoryTransient,
		Retryable: true,
		Timestamp: time.Now().Format(time.RFC3339),
	}
}

// WrapError wraps an existing error with additional context
func WrapError(errorType ErrorType, message string, err error) *AppError {
	return &AppError{
		errorType: errorType,
		Message:   message,
		Severity:  SeverityMedium,
		Category:  getCategoryForType(errorType),
		Retryable: isRetryableForType(errorType),
		Timestamp: time.Now().Format(time.RFC3339),
		Original:  err,
	}
}

// NewErrorWithCode creates a new error with a specific code
func NewErrorWithCode(errorType ErrorType, code, message string) *AppError {
	return &AppError{
		errorType: errorType,
		Code:      code,
		Message:   message,
		Severity:  SeverityMedium,
		Category:  CategoryTransient,
		Retryable: true,
		Timestamp: time.Now().Format(time.RFC3339),
	}
}

// Error implements the error interface
func (e *AppError) Error() string {
	if e.Code != "" {
		return fmt.Sprintf("[%s:%s] %s", e.errorType, e.Code, e.Message)
	}
	return fmt.Sprintf("[%s] %s", e.errorType, e.Message)
}

// GetType returns the error type
func (e *AppError) GetType() ErrorType {
	return e.errorType
}

// GetCategory returns the error category
func (e *AppError) GetCategory() ErrorCategory {
	return e.Category
}

// GetSeverity returns the error severity
func (e *AppError) GetSeverity() ErrorSeverity {
	return e.Severity
}

// IsRetryable returns whether the error is retryable
func (e *AppError) IsRetryable() bool {
	return e.Retryable
}

// GetCode returns the error code
func (e *AppError) GetCode() string {
	return e.Code
}

// WithTaskID sets the task ID
func (e *AppError) WithTaskID(taskID string) *AppError {
	e.TaskID = taskID
	return e
}

// WithSeverity sets the severity
func (e *AppError) WithSeverity(severity ErrorSeverity) *AppError {
	e.Severity = severity
	return e
}

// WithCategory sets the category
func (e *AppError) WithCategory(category ErrorCategory) *AppError {
	e.Category = category
	return e
}

// NotRetryable marks the error as not retryable
func (e *AppError) NotRetryable() *AppError {
	e.Retryable = false
	return e
}

// getCategoryForType returns the default category for an error type
func getCategoryForType(errorType ErrorType) ErrorCategory {
	switch errorType {
	case ErrorTypeNetwork, ErrorTypeTimeout:
		return CategoryTransient
	case ErrorTypeStorage, ErrorTypeFilesystem:
		return CategoryPermanent
	case ErrorTypeAuth:
		return CategoryPermission
	case ErrorTypeConfig, ErrorTypeValidation:
		return CategoryConfiguration
	default:
		return CategoryTransient
	}
}

// isRetryableForType returns whether an error type is retryable
func isRetryableForType(errorType ErrorType) bool {
	switch errorType {
	case ErrorTypeNetwork, ErrorTypeTimeout:
		return true
	case ErrorTypeCancel:
		return false
	case ErrorTypeConfig, ErrorTypeValidation, ErrorTypeAuth:
		return false
	default:
		return true
	}
}

// ErrorRegistry manages error types and their handling strategies
type ErrorRegistry struct {
	retryPolicies map[ErrorType]RetryPolicy
}

// RetryPolicy defines retry policy for an error type
type RetryPolicy struct {
	MaxRetries    int              // Maximum number of retries
	RetryDelay    time.Duration    // Delay between retries
	BackoffFactor float64          // Exponential backoff factor
	ShouldRetry   func(error) bool // Custom retry logic
}

// NewErrorRegistry creates a new error registry
func NewErrorRegistry() *ErrorRegistry {
	registry := &ErrorRegistry{
		retryPolicies: make(map[ErrorType]RetryPolicy),
	}
	registry.setDefaultPolicies()
	return registry
}

// setDefaultPolicies sets default retry policies
func (r *ErrorRegistry) setDefaultPolicies() {
	// Network errors - retry with backoff
	r.retryPolicies[ErrorTypeNetwork] = RetryPolicy{
		MaxRetries:    5,
		RetryDelay:    2 * time.Second,
		BackoffFactor: 2.0,
	}

	// Timeout errors - retry with backoff
	r.retryPolicies[ErrorTypeTimeout] = RetryPolicy{
		MaxRetries:    3,
		RetryDelay:    5 * time.Second,
		BackoffFactor: 1.5,
	}

	// Storage errors - limited retries
	r.retryPolicies[ErrorTypeStorage] = RetryPolicy{
		MaxRetries:    2,
		RetryDelay:    10 * time.Second,
		BackoffFactor: 1.0,
	}

	// Permanent errors - no retry
	r.retryPolicies[ErrorTypeFilesystem] = RetryPolicy{
		MaxRetries: 0,
	}

	// Config errors - no retry
	r.retryPolicies[ErrorTypeConfig] = RetryPolicy{
		MaxRetries: 0,
	}

	// Auth errors - no retry
	r.retryPolicies[ErrorTypeAuth] = RetryPolicy{
		MaxRetries: 0,
	}
}

// GetRetryPolicy returns the retry policy for an error type
func (r *ErrorRegistry) GetRetryPolicy(errorType ErrorType) RetryPolicy {
	if policy, ok := r.retryPolicies[errorType]; ok {
		return policy
	}
	// Default policy
	return RetryPolicy{
		MaxRetries:    3,
		RetryDelay:    5 * time.Second,
		BackoffFactor: 1.5,
	}
}

// ShouldRetry determines if an error should be retried based on policy
func (r *ErrorRegistry) ShouldRetry(err Error, retryCount int) bool {
	if !err.IsRetryable() {
		return false
	}

	policy := r.GetRetryPolicy(err.GetType())
	if policy.MaxRetries <= 0 {
		return false
	}

	if retryCount >= policy.MaxRetries {
		return false
	}

	if policy.ShouldRetry != nil {
		return policy.ShouldRetry(err)
	}

	return err.IsRetryable()
}

// GetRetryDelay calculates the delay before next retry
func (r *ErrorRegistry) GetRetryDelay(err Error, retryCount int) time.Duration {
	policy := r.GetRetryPolicy(err.GetType())
	delay := policy.RetryDelay

	// Apply exponential backoff
	if policy.BackoffFactor > 1.0 {
		for i := 0; i < retryCount; i++ {
			delay = time.Duration(float64(delay) * policy.BackoffFactor)
		}
	}

	return delay
}

// ErrorCollector collects and manages errors
type ErrorCollector struct {
	errors      []*AppError
	errorsMu    sync.RWMutex
	maxErrors   int
	alertLevels map[ErrorSeverity]int
}

// NewErrorCollector creates a new error collector
func NewErrorCollector() *ErrorCollector {
	return &ErrorCollector{
		errors:    make([]*AppError, 0),
		maxErrors: 1000,
		alertLevels: map[ErrorSeverity]int{
			SeverityLow:      10,
			SeverityMedium:   5,
			SeverityHigh:     3,
			SeverityCritical: 1,
		},
	}
}

// AddError adds an error to the collector
func (ec *ErrorCollector) AddError(err *AppError) {
	ec.errorsMu.Lock()
	defer ec.errorsMu.Unlock()

	ec.errors = append(ec.errors, err)

	// Trim old errors if we exceed max
	if len(ec.errors) > ec.maxErrors {
		ec.errors = ec.errors[len(ec.errors)-ec.maxErrors:]
	}

	// Check if we should alert
	ec.checkAlert(err)
}

// GetErrors returns all errors
func (ec *ErrorCollector) GetErrors() []*AppError {
	ec.errorsMu.RLock()
	defer ec.errorsMu.RUnlock()
	return append([]*AppError{}, ec.errors...)
}

// GetErrorsByType returns errors of a specific type
func (ec *ErrorCollector) GetErrorsByType(errorType ErrorType) []*AppError {
	ec.errorsMu.RLock()
	defer ec.errorsMu.RUnlock()

	var result []*AppError
	for _, err := range ec.errors {
		if err.errorType == errorType {
			result = append(result, err)
		}
	}
	return result
}

// GetErrorStats returns error statistics
func (ec *ErrorCollector) GetErrorStats() map[ErrorType]int {
	ec.errorsMu.RLock()
	defer ec.errorsMu.RUnlock()

	stats := make(map[ErrorType]int)
	for _, err := range ec.errors {
		stats[err.errorType]++
	}
	return stats
}

// checkAlert checks if an error should trigger an alert
func (ec *ErrorCollector) checkAlert(err *AppError) {
	threshold, ok := ec.alertLevels[err.Severity]
	if !ok {
		return
	}

	// Count recent errors of same severity
	recentCount := 0
	now := time.Now()
	recentWindow := 5 * time.Minute

	for _, e := range ec.errors {
		if e.Severity == err.Severity {
			if eTimestamp, parseErr := time.Parse(time.RFC3339, e.Timestamp); parseErr == nil {
				if now.Sub(eTimestamp) < recentWindow {
					recentCount++
				}
			}
		}
	}

	if recentCount >= threshold {
		// Trigger alert (implementation depends on alerting system)
		// For now, just log it
		fmt.Printf("[ALERT] Too many %s errors in recent window: %d\n", err.Severity, recentCount)
	}
}

// Clear clears all errors
func (ec *ErrorCollector) Clear() {
	ec.errorsMu.Lock()
	defer ec.errorsMu.Unlock()
	ec.errors = make([]*AppError, 0)
}

// Predefined errors
var (
	ErrNetworkTimeout     = NewError(ErrorTypeTimeout, "Network timeout")
	ErrStorageUnavailable = NewError(ErrorTypeStorage, "Storage unavailable").NotRetryable()
	ErrFileNotFound       = NewError(ErrorTypeFilesystem, "File not found").NotRetryable()
	ErrPermissionDenied   = NewError(ErrorTypeAuth, "Permission denied").NotRetryable()
	ErrInvalidConfig      = NewError(ErrorTypeConfig, "Invalid configuration").NotRetryable()
	ErrTaskCancelled      = NewError(ErrorTypeCancel, "Task cancelled").NotRetryable()
)
