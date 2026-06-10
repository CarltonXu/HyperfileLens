//go:build !windows

package main

import (
	"fmt"
)

// These functions are only used on Windows
// On Unix systems, services are handled differently (systemd, etc.)

func registerWindowsService(configPath string) error {
	return fmt.Errorf("registerWindowsService is only supported on Windows")
}

func unregisterWindowsService() error {
	return fmt.Errorf("unregisterWindowsService is only supported on Windows")
}

func startWindowsService() error {
	return fmt.Errorf("startWindowsService is only supported on Windows")
}

func stopWindowsService() error {
	return fmt.Errorf("stopWindowsService is only supported on Windows")
}

func runWindowsService() error {
	return fmt.Errorf("runWindowsService is only supported on Windows")
}
