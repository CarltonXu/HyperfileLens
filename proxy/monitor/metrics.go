package monitor

import (
	"runtime"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
)

// Metrics holds system metrics
type Metrics struct {
	CPUUsage    float64 `json:"cpu_usage"`
	MemoryUsage float64 `json:"memory_usage"`
	DiskUsage   float64 `json:"disk_usage"`
	Uptime      int64   `json:"uptime"`
	Goroutines  int     `json:"goroutines"`
}

// Collector collects system metrics
type Collector struct {
	startTime time.Time
}

// NewCollector creates a new metrics collector
func NewCollector() *Collector {
	return &Collector{
		startTime: time.Now(),
	}
}

// GetCurrent returns current metrics
func (c *Collector) GetCurrent() *Metrics {
	m := &Metrics{
		Uptime:     int64(time.Since(c.startTime).Seconds()),
		Goroutines: runtime.NumGoroutine(),
	}
	
	// CPU usage
	if cpuPercent, err := cpu.Percent(time.Second, false); err == nil && len(cpuPercent) > 0 {
		m.CPUUsage = cpuPercent[0]
	}
	
	// Memory usage
	if memInfo, err := mem.VirtualMemory(); err == nil {
		m.MemoryUsage = memInfo.UsedPercent
	}
	
	// Disk usage (root partition)
	if diskInfo, err := disk.Usage("/"); err == nil {
		m.DiskUsage = diskInfo.UsedPercent
	}
	
	return m
}

// GetHostInfo returns host information
func GetHostInfo() map[string]interface{} {
	info := make(map[string]interface{})
	
	if hostInfo, err := host.Info(); err == nil {
		info["hostname"] = hostInfo.Hostname
		info["os"] = hostInfo.OS
		info["platform"] = hostInfo.Platform
		info["platform_version"] = hostInfo.PlatformVersion
		info["kernel_version"] = hostInfo.KernelVersion
		info["arch"] = hostInfo.KernelArch
		info["uptime"] = hostInfo.Uptime
	}
	
	return info
}

// GetDiskPartitions returns disk partition info
func GetDiskPartitions() []map[string]interface{} {
	partitions, err := disk.Partitions(false)
	if err != nil {
		return nil
	}
	
	result := make([]map[string]interface{}, 0, len(partitions))
	for _, p := range partitions {
		info := map[string]interface{}{
			"device":     p.Device,
			"mountpoint": p.Mountpoint,
			"fstype":     p.Fstype,
		}
		
		if usage, err := disk.Usage(p.Mountpoint); err == nil {
			info["total"] = usage.Total
			info["used"] = usage.Used
			info["free"] = usage.Free
			info["used_percent"] = usage.UsedPercent
		}
		
		result = append(result, info)
	}
	
	return result
}
