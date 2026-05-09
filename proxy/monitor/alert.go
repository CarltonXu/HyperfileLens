package monitor

import (
	"fmt"
	"sync"
	"time"
)

// AlertType defines the type of alert
type AlertType string

const (
	AlertTypeCPUHigh         AlertType = "cpu_high"
	AlertTypeMemoryHigh      AlertType = "memory_high"
	AlertTypeDiskHigh        AlertType = "disk_high"
	AlertTypeNetworkError    AlertType = "network_error"
	AlertTypeTaskFailed      AlertType = "task_failed"
	AlertTypeTaskTimeout     AlertType = "task_timeout"
	AlertTypeErrorRate       AlertType = "error_rate"
)

// AlertSeverity defines alert severity
type AlertSeverity string

const (
	SeverityInfo     AlertSeverity = "info"
	SeverityWarning  AlertSeverity = "warning"
	SeverityCritical AlertSeverity = "critical"
)

// Alert represents an alert
type Alert struct {
	Type        AlertType     `json:"type"`
	Severity    AlertSeverity `json:"severity"`
	Message     string        `json:"message"`
	Value       float64       `json:"value"`
	Threshold   float64       `json:"threshold"`
	Timestamp   string        `json:"timestamp"`
	TaskID      string        `json:"task_id,omitempty"`
	Resolved    bool          `json:"resolved"`
	ResolvedAt  string        `json:"resolved_at,omitempty"`
}

// AlertThreshold defines alert thresholds
type AlertThreshold struct {
	CPUMin       float64 // CPU usage threshold (percentage)
	CPUCritical  float64 // CPU critical threshold
	MemoryMin    float64 // Memory usage threshold (percentage)
	MemoryCritical float64 // Memory critical threshold
	DiskMin      float64 // Disk usage threshold (percentage)
	DiskCritical float64 // Disk critical threshold
	ErrorRateMin int     // Error rate threshold (errors per minute)
}

// DefaultAlertThresholds returns default alert thresholds
func DefaultAlertThresholds() *AlertThreshold {
	return &AlertThreshold{
		CPUMin:       80.0,
		CPUCritical:  95.0,
		MemoryMin:    85.0,
		MemoryCritical: 95.0,
		DiskMin:      85.0,
		DiskCritical: 95.0,
		ErrorRateMin: 10,
	}
}

// AlertManager manages alerts
type AlertManager struct {
	thresholds  *AlertThreshold
	alerts     []*Alert
	alertsMu   sync.RWMutex
	activeAlerts map[AlertType]*Alert
	callbacks   []AlertCallback
	metrics    *MetricsHistory
}

// AlertCallback is a function called when an alert is triggered or resolved
type AlertCallback func(alert *Alert)

// MetricsHistory stores historical metrics for trend analysis
type MetricsHistory struct {
	cpuHistory      []float64
	memoryHistory   []float64
	diskHistory     []float64
	errorCountHistory []int
	historySize     int
	mu              sync.RWMutex
}

// NewAlertManager creates a new alert manager
func NewAlertManager(collector *Collector) *AlertManager {
	return &AlertManager{
		thresholds:   DefaultAlertThresholds(),
		alerts:      make([]*Alert, 0),
		activeAlerts: make(map[AlertType]*Alert),
		callbacks:    make([]AlertCallback, 0),
		metrics:      &MetricsHistory{
			historySize: 300, // Keep 5 minutes of history (at 1 second intervals)
		},
	}
}

// SetThresholds sets custom alert thresholds
func (am *AlertManager) SetThresholds(thresholds *AlertThreshold) {
	am.thresholds = thresholds
}

// AddCallback adds an alert callback
func (am *AlertManager) AddCallback(callback AlertCallback) {
	am.alertsMu.Lock()
	defer am.alertsMu.Unlock()
	am.callbacks = append(am.callbacks, callback)
}

// CheckMetrics checks metrics and triggers alerts if thresholds are exceeded
func (am *AlertManager) CheckMetrics(metrics *Metrics) {
	// Update metrics history
	am.updateHistory(metrics)

	// Check CPU
	if metrics.CPUUsage >= am.thresholds.CPUCritical {
		am.triggerAlert(AlertTypeCPUHigh, SeverityCritical, fmt.Sprintf("CPU usage critical: %.1f%%", metrics.CPUUsage), metrics.CPUUsage, am.thresholds.CPUCritical)
	} else if metrics.CPUUsage >= am.thresholds.CPUMin {
		am.triggerAlert(AlertTypeCPUHigh, SeverityWarning, fmt.Sprintf("CPU usage high: %.1f%%", metrics.CPUUsage), metrics.CPUUsage, am.thresholds.CPUMin)
	} else {
		am.resolveAlert(AlertTypeCPUHigh)
	}

	// Check Memory
	if metrics.MemoryUsage >= am.thresholds.MemoryCritical {
		am.triggerAlert(AlertTypeMemoryHigh, SeverityCritical, fmt.Sprintf("Memory usage critical: %.1f%%", metrics.MemoryUsage), metrics.MemoryUsage, am.thresholds.MemoryCritical)
	} else if metrics.MemoryUsage >= am.thresholds.MemoryMin {
		am.triggerAlert(AlertTypeMemoryHigh, SeverityWarning, fmt.Sprintf("Memory usage high: %.1f%%", metrics.MemoryUsage), metrics.MemoryUsage, am.thresholds.MemoryMin)
	} else {
		am.resolveAlert(AlertTypeMemoryHigh)
	}

	// Check Disk
	if metrics.DiskUsage >= am.thresholds.DiskCritical {
		am.triggerAlert(AlertTypeDiskHigh, SeverityCritical, fmt.Sprintf("Disk usage critical: %.1f%%", metrics.DiskUsage), metrics.DiskUsage, am.thresholds.DiskCritical)
	} else if metrics.DiskUsage >= am.thresholds.DiskMin {
		am.triggerAlert(AlertTypeDiskHigh, SeverityWarning, fmt.Sprintf("Disk usage high: %.1f%%", metrics.DiskUsage), metrics.DiskUsage, am.thresholds.DiskMin)
	} else {
		am.resolveAlert(AlertTypeDiskHigh)
	}
}

// triggerAlert triggers an alert
func (am *AlertManager) triggerAlert(alertType AlertType, severity AlertSeverity, message string, value, threshold float64) {
	am.alertsMu.Lock()
	defer am.alertsMu.Unlock()

	// Check if alert already exists
	if existing, ok := am.activeAlerts[alertType]; ok && !existing.Resolved {
		return // Alert already active
	}

	alert := &Alert{
		Type:      alertType,
		Severity:  severity,
		Message:   message,
		Value:     value,
		Threshold: threshold,
		Timestamp: time.Now().Format(time.RFC3339),
		Resolved:  false,
	}

	am.activeAlerts[alertType] = alert
	am.alerts = append(am.alerts, alert)

	// Call callbacks
	for _, callback := range am.callbacks {
		go callback(alert)
	}
}

// resolveAlert resolves an active alert
func (am *AlertManager) resolveAlert(alertType AlertType) {
	am.alertsMu.Lock()
	defer am.alertsMu.Unlock()

	if alert, ok := am.activeAlerts[alertType]; ok {
		alert.Resolved = true
		alert.ResolvedAt = time.Now().Format(time.RFC3339)

		// Call callbacks
		for _, callback := range am.callbacks {
			go callback(alert)
		}

		// Remove from active alerts
		delete(am.activeAlerts, alertType)
	}
}

// triggerTaskAlert triggers a task-related alert
func (am *AlertManager) triggerTaskAlert(alertType AlertType, taskID, message string, severity AlertSeverity) {
	am.alertsMu.Lock()
	defer am.alertsMu.Unlock()

	alert := &Alert{
		Type:      alertType,
		Severity:  severity,
		Message:   message,
		TaskID:    taskID,
		Timestamp: time.Now().Format(time.RFC3339),
		Resolved:  false,
	}

	am.alerts = append(am.alerts, alert)

	// Call callbacks
	for _, callback := range am.callbacks {
		go callback(alert)
	}
}

// updateHistory updates metrics history
func (am *AlertManager) updateHistory(metrics *Metrics) {
	am.metrics.mu.Lock()
	defer am.metrics.mu.Unlock()

	am.metrics.cpuHistory = append(am.metrics.cpuHistory, metrics.CPUUsage)
	am.metrics.memoryHistory = append(am.metrics.memoryHistory, metrics.MemoryUsage)
	am.metrics.diskHistory = append(am.metrics.diskHistory, metrics.DiskUsage)

	if len(am.metrics.cpuHistory) > am.metrics.historySize {
		am.metrics.cpuHistory = am.metrics.cpuHistory[1:]
		am.metrics.memoryHistory = am.metrics.memoryHistory[1:]
		am.metrics.diskHistory = am.metrics.diskHistory[1:]
	}
}

// GetTrend calculates trend for a metric series
func (am *AlertManager) GetTrend(history []float64) string {
	if len(history) < 2 {
		return "stable"
	}

	recent := history[len(history)/4:]
	old := history[:len(history)-len(recent)]

	recentAvg := average(recent)
	oldAvg := average(old)

	change := (recentAvg - oldAvg) / oldAvg * 100

	if change > 10 {
		return "increasing"
	} else if change < -10 {
		return "decreasing"
	}
	return "stable"
}

// GetCPUTrend returns CPU usage trend
func (am *AlertManager) GetCPUTrend() string {
	am.metrics.mu.RLock()
	defer am.metrics.mu.RUnlock()
	return am.GetTrend(am.metrics.cpuHistory)
}

// GetMemoryTrend returns memory usage trend
func (am *AlertManager) GetMemoryTrend() string {
	am.metrics.mu.RLock()
	defer am.metrics.mu.RUnlock()
	return am.GetTrend(am.metrics.memoryHistory)
}

// GetDiskTrend returns disk usage trend
func (am *AlertManager) GetDiskTrend() string {
	am.metrics.mu.RLock()
	defer am.metrics.mu.RUnlock()
	return am.GetTrend(am.metrics.diskHistory)
}

// GetActiveAlerts returns all active alerts
func (am *AlertManager) GetActiveAlerts() []*Alert {
	am.alertsMu.RLock()
	defer am.alertsMu.RUnlock()

	active := make([]*Alert, 0)
	for _, alert := range am.activeAlerts {
		active = append(active, alert)
	}
	return active
}

// GetRecentAlerts returns recent alerts
func (am *AlertManager) GetRecentAlerts(count int) []*Alert {
	am.alertsMu.RLock()
	defer am.alertsMu.RUnlock()

	if count > len(am.alerts) {
		count = len(am.alerts)
	}

	return am.alerts[len(am.alerts)-count:]
}

func average(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}