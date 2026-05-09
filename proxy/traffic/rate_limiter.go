package traffic

import (
	"sync"
	"time"
)

// RateLimiter implements a token bucket rate limiter
type RateLimiter struct {
	rate       float64    // tokens per second
	bucketSize int64      // maximum bucket size
	tokens     float64    // current tokens
	lastUpdate time.Time  // last update time
	mu         sync.Mutex
}

// NewRateLimiter creates a new rate limiter
// kbps is the rate in kilobytes per second
func NewRateLimiter(kbps int64) *RateLimiter {
	return &RateLimiter{
		rate:       float64(kbps * 1024), // convert KB/s to bytes/s
		bucketSize: kbps * 1024 * 10,    // 10 seconds worth of tokens
		tokens:     float64(kbps * 1024),
		lastUpdate: time.Now(),
	}
}

// Allow checks if a transfer of size bytes is allowed
func (r *RateLimiter) Allow(size int) bool {
	r.mu.Lock()
	defer r.mu.Unlock()

	now := time.Now()
	elapsed := now.Sub(r.lastUpdate).Seconds()

	// Add tokens based on elapsed time
	r.tokens += elapsed * r.rate
	if r.tokens > float64(r.bucketSize) {
		r.tokens = float64(r.bucketSize)
	}

	// Check if we have enough tokens
	if r.tokens >= float64(size) {
		r.tokens -= float64(size)
		r.lastUpdate = now
		return true
	}

	return false
}

// Wait blocks until a transfer of size bytes is allowed
func (r *RateLimiter) Wait(size int) {
	for !r.Allow(size) {
		// Calculate how long to wait
		r.mu.Lock()
		needed := float64(size) - r.tokens
		waitTime := time.Duration(needed/r.rate * float64(time.Second))
		r.mu.Unlock()

		if waitTime > 0 {
			time.Sleep(waitTime)
		}
	}
}

// SetRate updates the rate limit
func (r *RateLimiter) SetRate(kbps int64) {
	r.mu.Lock()
	defer r.mu.Unlock()

	r.rate = float64(kbps * 1024)
	r.bucketSize = kbps * 1024 * 10
}