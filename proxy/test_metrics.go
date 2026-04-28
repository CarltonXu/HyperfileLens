//go:build ignore

package main

import (
	"encoding/json"
	"fmt"
	"github.com/hyperfilelens/proxy/monitor"
)

func main() {
	interfaces := monitor.GetNetworkInterfaces()
	data, _ := json.MarshalIndent(interfaces, "", "  ")
	fmt.Printf("Network Interfaces:\n%s\n\n", string(data))
	
	diskStats := monitor.GetDiskIOStats()
	data2, _ := json.MarshalIndent(diskStats, "", "  ")
	fmt.Printf("Disk IO Stats:\n%s\n", string(data2))
}
