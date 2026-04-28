package monitor

import (
	"runtime"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/net"
)

// Metrics holds system metrics
type Metrics struct {
	// CPU
	CPUUsage    float64 `json:"cpu_usage"`
	CPUCores    int     `json:"cpu_cores"`     // Logical cores
	CPUPhysical int     `json:"cpu_physical"`  // Physical cores

	// Memory
	MemoryUsage float64 `json:"memory_usage"`
	MemoryTotal uint64  `json:"memory_total"`
	MemoryUsed  uint64  `json:"memory_used"`
	MemoryFree  uint64  `json:"memory_free"`

	// Disk (root partition)
	DiskUsage float64 `json:"disk_usage"`
	DiskTotal uint64  `json:"disk_total"`
	DiskUsed  uint64  `json:"disk_used"`
	DiskFree  uint64  `json:"disk_free"`

	// Network
	NetworkBytesSent   uint64 `json:"network_bytes_sent"`
	NetworkBytesRecv   uint64 `json:"network_bytes_recv"`
	NetworkPacketsSent uint64 `json:"network_packets_sent"`
	NetworkPacketsRecv uint64 `json:"network_packets_recv"`

	// System
	Uptime     int64 `json:"uptime"`
	Goroutines int   `json:"goroutines"`
}

// DiskPartition represents a disk partition
type DiskPartition struct {
	Device     string  `json:"device"`
	Mountpoint string  `json:"mountpoint"`
	Fstype     string  `json:"fstype"`
	Total      uint64  `json:"total"`
	Used       uint64  `json:"used"`
	Free       uint64  `json:"free"`
	UsedPercent float64 `json:"used_percent"`
}

// NetworkIO represents network I/O statistics
type NetworkIO struct {
	BytesSent   uint64 `json:"bytes_sent"`
	BytesRecv   uint64 `json:"bytes_recv"`
	PacketsSent uint64 `json:"packets_sent"`
	PacketsRecv uint64 `json:"packets_recv"`
}

// Collector collects system metrics
type Collector struct {
	startTime       time.Time
	lastNetworkIO   *NetworkIO
	lastNetworkTime time.Time
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
		CPUCores:   runtime.NumCPU(),
	}

	// CPU usage and physical cores
	if cpuPercent, err := cpu.Percent(time.Second, false); err == nil && len(cpuPercent) > 0 {
		m.CPUUsage = cpuPercent[0]
	}
	if physicalCores, err := cpu.Counts(false); err == nil {
		m.CPUPhysical = physicalCores
	}

	// Memory usage
	if memInfo, err := mem.VirtualMemory(); err == nil {
		m.MemoryUsage = memInfo.UsedPercent
		m.MemoryTotal = memInfo.Total
		m.MemoryUsed = memInfo.Used
		m.MemoryFree = memInfo.Free
	}

	// Disk usage (root partition)
	if diskInfo, err := disk.Usage("/"); err == nil {
		m.DiskUsage = diskInfo.UsedPercent
		m.DiskTotal = diskInfo.Total
		m.DiskUsed = diskInfo.Used
		m.DiskFree = diskInfo.Free
	}

	// Network I/O
	if netIO, err := net.IOCounters(false); err == nil && len(netIO) > 0 {
		m.NetworkBytesSent = netIO[0].BytesSent
		m.NetworkBytesRecv = netIO[0].BytesRecv
		m.NetworkPacketsSent = netIO[0].PacketsSent
		m.NetworkPacketsRecv = netIO[0].PacketsRecv
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

	// Add CPU info
	info["cpu_cores_logical"] = runtime.NumCPU()
	if physicalCores, err := cpu.Counts(false); err == nil {
		info["cpu_cores_physical"] = physicalCores
	}

	return info
}

// GetDiskPartitions returns disk partition info
func GetDiskPartitions() []DiskPartition {
	partitions, err := disk.Partitions(false)
	if err != nil {
		return nil
	}

	result := make([]DiskPartition, 0, len(partitions))
	for _, p := range partitions {
		partition := DiskPartition{
			Device:     p.Device,
			Mountpoint: p.Mountpoint,
			Fstype:     p.Fstype,
		}

		if usage, err := disk.Usage(p.Mountpoint); err == nil {
			partition.Total = usage.Total
			partition.Used = usage.Used
			partition.Free = usage.Free
			partition.UsedPercent = usage.UsedPercent
		}

		result = append(result, partition)
	}

	return result
}

// GetNetworkIO returns network I/O statistics
func GetNetworkIO() (*NetworkIO, error) {
	counters, err := net.IOCounters(false)
	if err != nil {
		return nil, err
	}

	if len(counters) == 0 {
		return nil, nil
	}

	return &NetworkIO{
		BytesSent:   counters[0].BytesSent,
		BytesRecv:   counters[0].BytesRecv,
		PacketsSent: counters[0].PacketsSent,
		PacketsRecv: counters[0].PacketsRecv,
	}, nil
}


// NetworkInterfaceInfo represents network interface information
type NetworkInterfaceInfo struct {
	Name        string   `json:"name"`
	IPAddresses []string `json:"ip_addresses,omitempty"`
	MAC         string   `json:"mac,omitempty"`
	BytesIn     int64    `json:"bytes_in,omitempty"`
	BytesOut    int64    `json:"bytes_out,omitempty"`
}

// GetNetworkInterfaces returns network interface information
func GetNetworkInterfaces() []NetworkInterfaceInfo {
	interfaces, err := net.Interfaces()
	if err != nil {
		return nil
	}

	result := make([]NetworkInterfaceInfo, 0, len(interfaces))
	for _, iface := range interfaces {
		info := NetworkInterfaceInfo{
			Name: iface.Name,
			MAC:  iface.HardwareAddr,
		}

		// Add IP addresses
		var addrs []string
		for _, addr := range iface.Addrs {
			addrs = append(addrs, addr.Addr)
		}
		info.IPAddresses = addrs

		// Get IO counters for this interface
		counters, err := net.IOCounters(true)
		if err == nil {
			for _, c := range counters {
				if c.Name == iface.Name {
					info.BytesIn = int64(c.BytesRecv)
					info.BytesOut = int64(c.BytesSent)
					break
				}
			}
		}

		result = append(result, info)
	}

	return result
}
