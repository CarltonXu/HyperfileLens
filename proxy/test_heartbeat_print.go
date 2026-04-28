//go:build ignore

package main

import (
	"encoding/json"
	"fmt"
	"github.com/hyperfilelens/proxy/monitor"
)

type HeartbeatPayload struct {
	NodeID            string                         `json:"node_id"`
	APIToken          string                         `json:"api_token,omitempty"`
	Version           string                         `json:"version"`
	Hostname          string                         `json:"hostname"`
	CPUUsage          float64                        `json:"cpu_usage"`
	MemoryUsage       float64                        `json:"memory_usage"`
	DiskUsage         float64                        `json:"disk_usage"`
	NetworkInterfaces []monitor.NetworkInterfaceInfo `json:"network_interfaces"`
	DiskIOStats       []monitor.DiskIOStats          `json:"disk_io_stats"`
}

func main() {
	payload := HeartbeatPayload{
		NodeID:            "test-id",
		Version:           "1.0.10",
		Hostname:          "test-host",
		CPUUsage:          50.0,
		MemoryUsage:       60.0,
		DiskUsage:         70.0,
		NetworkInterfaces: monitor.GetNetworkInterfaces(),
		DiskIOStats:       monitor.GetDiskIOStats(),
	}

	data, _ := json.MarshalIndent(payload, "", "  ")
	fmt.Printf("%s\n", string(data))
}
