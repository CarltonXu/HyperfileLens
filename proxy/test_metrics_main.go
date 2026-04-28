//go:build ignore

package main

import (
	"encoding/json"
	"fmt"
	"hyperfilelens/proxy/monitor"
)

func main() {
	// Test network interfaces
	interfaces := monitor.GetNetworkInterfaces()
	fmt.Printf("=== Network Interfaces (%d) ===\n", len(interfaces))
	if len(interfaces) > 0 {
		for i, iface := range interfaces {
			if i >= 3 {
				break
			}
			data, _ := json.MarshalIndent(iface, "", "  ")
			fmt.Printf("%s\n", string(data))
		}
	}

	// Test disk IO stats
	diskStats := monitor.GetDiskIOStats()
	fmt.Printf("\n=== Disk IO Stats (%d) ===\n", len(diskStats))
	if len(diskStats) > 0 {
		for i, stat := range diskStats {
			if i >= 3 {
				break
			}
			data, _ := json.MarshalIndent(stat, "", "  ")
			fmt.Printf("%s\n", string(data))
		}
	}
}
