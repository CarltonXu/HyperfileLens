//go:build ignore

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
	"github.com/hyperfilelens/proxy/monitor"
)

type HeartbeatPayload struct {
	NodeID            string                         `json:"node_id"`
	APIToken          string                         `json:"api_token"`
	Version           string                         `json:"version"`
	Hostname          string                         `json:"hostname"`
	CPUUsage          float64                        `json:"cpu_usage"`
	MemoryUsage       float64                        `json:"memory_usage"`
	DiskUsage         float64                        `json:"disk_usage"`
	NetworkInterfaces []monitor.NetworkInterfaceInfo `json:"network_interfaces"`
	DiskIOStats       []monitor.DiskIOStats          `json:"disk_io_stats"`
}

func main() {
	// 采集数据
	interfaces := monitor.GetNetworkInterfaces()
	diskStats := monitor.GetDiskIOStats()
	
	fmt.Printf("=== Collected Data ===\n")
	fmt.Printf("Network Interfaces: %d\n", len(interfaces))
	for i, iface := range interfaces {
		if i < 2 {
			fmt.Printf("  - %s: in=%d, out=%d\n", iface.Name, iface.BytesIn, iface.BytesOut)
		}
	}
	fmt.Printf("Disk IO Stats: %d\n", len(diskStats))
	for i, disk := range diskStats {
		if i < 2 {
			fmt.Printf("  - %s: read=%d, write=%d\n", disk.Name, disk.ReadBytes, disk.WriteBytes)
		}
	}

	// 构造心跳数据
	payload := HeartbeatPayload{
		NodeID:            "f1daa5cb-ddff-4611-a9b1-abbc404843e0",
		APIToken:          "CMjM-6lerYVhgxmoum8ivQ-x-uAGLsWOvDnhQSg3KKI",
		Version:           "1.0.10",
		Hostname:          "test-host",
		CPUUsage:          50.0,
		MemoryUsage:       60.0,
		DiskUsage:         70.0,
		NetworkInterfaces: interfaces,
		DiskIOStats:       diskStats,
	}

	// 序列化
	body, _ := json.Marshal(payload)
	fmt.Printf("\n=== JSON Payload ===\n%s\n", string(body)[:min(1000, len(string(body)))])

	// 发送请求
	url := "http://localhost:8000/api/v1/proxies/f1daa5cb-ddff-4611-a9b1-abbc404843e0/heartbeat/"
	req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	fmt.Printf("\n=== Response ===\nStatus: %d\nBody: %s\n", resp.StatusCode, string(respBody))
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
