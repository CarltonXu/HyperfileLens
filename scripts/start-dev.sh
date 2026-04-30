#!/bin/bash

# =============================================================================
# HyperFileLens Development Environment Management Script
# =============================================================================
# Usage: ./start-dev.sh [COMMAND] [SERVICE...] [OPTIONS]
#
# Commands:
#   start     Start services (default if no command specified)
#   stop      Stop services
#   restart   Restart services
#   status    Show service status
#   logs      Show service logs
#   install   Install dependencies only
#
# Services:
#   all       All services (default)
#   frontend  Frontend service (Vue.js on port 5000)
#   backend   Backend service (Django on port 8000)
#   gateway   Gateway service (FastAPI on port 8001)
#   redis     Redis server (port 6379)
#   celery    Celery worker
#
# Options:
#   -h, --help     Show this help message
#   -v, --verbose  Enable verbose output
#   --no-deps      Skip dependency installation
#   --build        Force rebuild frontend
#
# Examples:
#   ./start-dev.sh                    # Start all services
#   ./start-dev.sh start backend      # Start only backend
#   ./start-dev.sh restart frontend   # Restart frontend
#   ./start-dev.sh stop all           # Stop all services
#   ./start-dev.sh logs backend       # Show backend logs
#   ./start-dev.sh status             # Show service status
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================

readonly SCRIPT_NAME=$(basename "$0")
readonly SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
readonly PROJECT_ROOT="/workspace/projects"
readonly LOG_DIR="/app/work/logs/bypass"
readonly PID_DIR="/var/run/hyperfilelens"

# Service ports
readonly FRONTEND_PORT=5000
readonly BACKEND_PORT=8000
readonly GATEWAY_PORT=8001
readonly REDIS_PORT=6379

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color
readonly BOLD='\033[1m'

# Flags
VERBOSE=false
NO_DEPS=false
FORCE_BUILD=false

# =============================================================================
# Utility Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

print_banner() {
    echo ""
    echo -e "${BOLD}${BLUE}==================================================${NC}"
    echo -e "${BOLD}${BLUE}   HyperFileLens Development Environment${NC}"
    echo -e "${BOLD}${BLUE}==================================================${NC}"
    echo ""
}

print_help() {
    cat << EOF
Usage: $SCRIPT_NAME [COMMAND] [SERVICE...] [OPTIONS]

Commands:
  start     Start services (default if no command specified)
  stop      Stop services
  restart   Restart services
  status    Show service status
  logs      Show service logs (follow mode)
  install   Install dependencies only

Services:
  all       All services (default)
  frontend  Frontend service (Vue.js on port $FRONTEND_PORT)
  backend   Backend service (Django on port $BACKEND_PORT)
  gateway   Gateway service (FastAPI on port $GATEWAY_PORT)
  redis     Redis server (port $REDIS_PORT)
  celery    Celery worker

Options:
  -h, --help     Show this help message
  -v, --verbose  Enable verbose output
  --no-deps      Skip dependency installation
  --build        Force rebuild frontend

Examples:
  $SCRIPT_NAME                      # Start all services
  $SCRIPT_NAME start backend        # Start only backend
  $SCRIPT_NAME restart frontend     # Restart frontend
  $SCRIPT_NAME stop all             # Stop all services
  $SCRIPT_NAME logs backend         # Show backend logs
  $SCRIPT_NAME status               # Show service status
EOF
}

# =============================================================================
# Process Management Functions
# =============================================================================

# Create required directories
setup_directories() {
    mkdir -p "$LOG_DIR" "$PID_DIR"
    log_debug "Created directories: $LOG_DIR, $PID_DIR"
}

# Get PID file path for a service
get_pid_file() {
    local service=$1
    echo "$PID_DIR/${service}.pid"
}

# Save PID to file
save_pid() {
    local service=$1
    local pid=$2
    echo "$pid" > "$(get_pid_file "$service")"
    log_debug "Saved PID $pid for $service"
}

# Get PID from file
get_pid() {
    local service=$1
    local pid_file=$(get_pid_file "$service")
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
    fi
}

# Remove PID file
remove_pid() {
    local service=$1
    local pid_file=$(get_pid_file "$service")
    rm -f "$pid_file"
    log_debug "Removed PID file for $service"
}

# Check if a process is running
is_process_running() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

# Check if a port is in use (LISTEN state)
is_port_listening() {
    local port=$1
    ss -lptn "sport = :$port" 2>/dev/null | grep -q LISTEN
}

# Get process listening on port
get_port_process() {
    local port=$1
    ss -lptn "sport = :$port" 2>/dev/null | grep LISTEN | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1
}

# Kill process by PID with graceful shutdown
kill_process() {
    local pid=$1
    local service=$2
    local timeout=${3:-10}
    
    if [ -z "$pid" ]; then
        return 0
    fi
    
    log_debug "Attempting to stop $service (PID: $pid)"
    
    # Try graceful shutdown first
    kill -TERM "$pid" 2>/dev/null || true
    
    local count=0
    while is_process_running "$pid" && [ $count -lt $timeout ]; do
        sleep 1
        count=$((count + 1))
    done
    
    # Force kill if still running
    if is_process_running "$pid"; then
        log_warn "Force killing $service"
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi
    
    if is_process_running "$pid"; then
        log_error "Failed to stop $service"
        return 1
    fi
    
    log_debug "Stopped $service"
    return 0
}

# =============================================================================
# Service Functions
# =============================================================================

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    # Check if kopia repo is already added
    if [ ! -f /etc/apt/sources.list.d/kopia.list ]; then
        curl -s https://kopia.io/signing-key | gpg --dearmor -o /etc/apt/keyrings/kopia-keyring.gpg 2>/dev/null || true
        echo "deb [signed-by=/etc/apt/keyrings/kopia-keyring.gpg] http://packages.kopia.io/apt/ stable main" | tee /etc/apt/sources.list.d/kopia.list
    fi
    
    apt-get update -qq
    apt-get install -y -qq kopia redis-server sqlite3 daphne > /dev/null
    
    log_info "System dependencies installed"
}

# Install Python dependencies
install_backend_deps() {
    log_info "Installing backend dependencies..."
    cd "$PROJECT_ROOT/backend"
    pip install -q -r requirements.txt
    log_info "Backend dependencies installed"
}

# Install frontend dependencies
install_frontend_deps() {
    log_info "Installing frontend dependencies..."
    cd "$PROJECT_ROOT/frontend"
    pnpm install --silent 2>/dev/null || pnpm install
    log_info "Frontend dependencies installed"
}

# Install all dependencies
install_all_deps() {
    install_system_deps
    install_backend_deps
    install_frontend_deps
}

# Start Redis
start_redis() {
    log_info "Starting Redis..."
    
    if is_port_listening $REDIS_PORT; then
        log_warn "Redis is already running on port $REDIS_PORT"
        return 0
    fi
    
    redis-server --daemonize yes --logfile "$LOG_DIR/redis.log"
    sleep 1
    
    if is_port_listening $REDIS_PORT; then
        local pid=$(get_port_process $REDIS_PORT)
        save_pid "redis" "$pid"
        log_info "Redis started on port $REDIS_PORT"
        return 0
    else
        log_error "Failed to start Redis"
        return 1
    fi
}

# Stop Redis
stop_redis() {
    log_info "Stopping Redis..."
    
    if ! is_port_listening $REDIS_PORT; then
        log_warn "Redis is not running"
        remove_pid "redis"
        return 0
    fi
    
    redis-cli shutdown 2>/dev/null || true
    sleep 1
    
    if is_port_listening $REDIS_PORT; then
        local pid=$(get_port_process $REDIS_PORT)
        kill_process "$pid" "redis"
    fi
    
    remove_pid "redis"
    log_info "Redis stopped"
}

# Start Backend
start_backend() {
    log_info "Starting Backend..."
    
    if is_port_listening $BACKEND_PORT; then
        log_warn "Backend is already running on port $BACKEND_PORT"
        return 0
    fi
    
    cd "$PROJECT_ROOT/backend"
    
    # Run migrations if needed
    if [ -f "manage.py" ]; then
        USE_POSTGRES=false python manage.py migrate --noinput > /dev/null 2>&1 || log_warn "Migration may have issues"
    fi
    
    # Start Daphne server (ASGI for WebSocket support)
    USE_POSTGRES=false daphne -b 0.0.0.0 -p $BACKEND_PORT core.asgi:application > "$LOG_DIR/backend.log" 2>&1 &
    local pid=$!
    save_pid "backend" "$pid"
    
    sleep 3
    
    if is_port_listening $BACKEND_PORT; then
        log_info "Backend started on port $BACKEND_PORT"
        return 0
    else
        log_error "Failed to start Backend"
        log_error "Check logs: tail -f $LOG_DIR/backend.log"
        return 1
    fi
}

# Stop Backend
stop_backend() {
    log_info "Stopping Backend..."
    
    local pid=$(get_pid "backend")
    
    if [ -n "$pid" ]; then
        kill_process "$pid" "backend"
    elif is_port_listening $BACKEND_PORT; then
        pid=$(get_port_process $BACKEND_PORT)
        kill_process "$pid" "backend"
    else
        log_warn "Backend is not running"
    fi
    
    remove_pid "backend"
    log_info "Backend stopped"
}

# Start Frontend
start_frontend() {
    log_info "Starting Frontend..."
    
    if is_port_listening $FRONTEND_PORT; then
        log_warn "Frontend is already running on port $FRONTEND_PORT"
        return 0
    fi
    
    cd "$PROJECT_ROOT/frontend"
    
    # Build if needed or forced
    if [ "$FORCE_BUILD" = true ] || [ ! -d "dist" ]; then
        log_info "Building frontend..."
        pnpm run build > "$LOG_DIR/frontend-build.log" 2>&1
    fi
    
    # Start server
    node server.cjs > "$LOG_DIR/frontend.log" 2>&1 &
    local pid=$!
    save_pid "frontend" "$pid"
    
    sleep 2
    
    if is_port_listening $FRONTEND_PORT; then
        log_info "Frontend started on port $FRONTEND_PORT"
        return 0
    else
        log_error "Failed to start Frontend"
        log_error "Check logs: tail -f $LOG_DIR/frontend.log"
        return 1
    fi
}

# Stop Frontend
stop_frontend() {
    log_info "Stopping Frontend..."
    
    local pid=$(get_pid "frontend")
    
    if [ -n "$pid" ]; then
        kill_process "$pid" "frontend"
    elif is_port_listening $FRONTEND_PORT; then
        pid=$(get_port_process $FRONTEND_PORT)
        kill_process "$pid" "frontend"
    else
        log_warn "Frontend is not running"
    fi
    
    remove_pid "frontend"
    log_info "Frontend stopped"
}

# Start Gateway
start_gateway() {
    log_info "Starting Gateway..."
    
    if [ ! -d "$PROJECT_ROOT/gateway" ]; then
        log_warn "Gateway directory not found, skipping"
        return 0
    fi
    
    if is_port_listening $GATEWAY_PORT; then
        log_warn "Gateway is already running on port $GATEWAY_PORT"
        return 0
    fi
    
    cd "$PROJECT_ROOT/gateway"
    
    if ! command -v uvicorn &> /dev/null; then
        log_warn "uvicorn not installed, skipping gateway"
        return 0
    fi
    
    uvicorn app.main:app --host 0.0.0.0 --port $GATEWAY_PORT > "$LOG_DIR/gateway.log" 2>&1 &
    local pid=$!
    save_pid "gateway" "$pid"
    
    sleep 2
    
    if is_port_listening $GATEWAY_PORT; then
        log_info "Gateway started on port $GATEWAY_PORT"
        return 0
    else
        log_warn "Gateway failed to start (optional service)"
        return 0
    fi
}

# Stop Gateway
stop_gateway() {
    log_info "Stopping Gateway..."
    
    local pid=$(get_pid "gateway")
    
    if [ -n "$pid" ]; then
        kill_process "$pid" "gateway"
    elif is_port_listening $GATEWAY_PORT; then
        pid=$(get_port_process $GATEWAY_PORT)
        kill_process "$pid" "gateway"
    else
        log_warn "Gateway is not running"
    fi
    
    remove_pid "gateway"
    log_info "Gateway stopped"
}

# Start Celery
start_celery() {
    log_info "Starting Celery worker..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Check if celery is configured
    if [ ! -f "core/celery.py" ]; then
        log_warn "Celery not configured, skipping"
        return 0
    fi
    
    celery -A core worker --loglevel=info > "$LOG_DIR/celery.log" 2>&1 &
    local pid=$!
    save_pid "celery" "$pid"
    
    sleep 2
    log_info "Celery worker started"
    return 0
}

# Stop Celery
stop_celery() {
    log_info "Stopping Celery..."
    
    local pid=$(get_pid "celery")
    
    if [ -n "$pid" ]; then
        kill_process "$pid" "celery"
    else
        log_warn "Celery is not running"
    fi
    
    remove_pid "celery"
    log_info "Celery stopped"
}

# =============================================================================
# Service Management Functions
# =============================================================================

# Start services
start_services() {
    local services=("$@")
    
    if [ ${#services[@]} -eq 0 ] || [[ "${services[0]}" == "all" ]]; then
        services=("redis" "backend" "frontend" "gateway" "celery")
    fi
    
    for service in "${services[@]}"; do
        case $service in
            redis)    start_redis ;;
            backend)  start_backend ;;
            frontend) start_frontend ;;
            gateway)  start_gateway ;;
            celery)   start_celery ;;
            *)
                log_error "Unknown service: $service"
                print_help
                exit 1
                ;;
        esac
    done
}

# Stop services
stop_services() {
    local services=("$@")
    
    if [ ${#services[@]} -eq 0 ] || [[ "${services[0]}" == "all" ]]; then
        services=("celery" "gateway" "frontend" "backend" "redis")
    fi
    
    for service in "${services[@]}"; do
        case $service in
            redis)    stop_redis ;;
            backend)  stop_backend ;;
            frontend) stop_frontend ;;
            gateway)  stop_gateway ;;
            celery)   stop_celery ;;
            *)
                log_error "Unknown service: $service"
                print_help
                exit 1
                ;;
        esac
    done
}

# Restart services
restart_services() {
    local services=("$@")
    stop_services "${services[@]}"
    sleep 2
    start_services "${services[@]}"
}

# Show service status
show_status() {
    echo ""
    echo -e "${BOLD}Service Status:${NC}"
    echo ""
    printf "%-12s %-8s %-10s %s\n" "Service" "Port" "Status" "URL"
    printf "%-12s %-8s %-10s %s\n" "-------" "----" "------" "---"
    
    # Redis
    if is_port_listening $REDIS_PORT; then
        printf "%-12s %-8s ${GREEN}%-10s${NC} %s\n" "Redis" "$REDIS_PORT" "Running" "localhost:$REDIS_PORT"
    else
        printf "%-12s %-8s ${RED}%-10s${NC} %s\n" "Redis" "$REDIS_PORT" "Stopped" "-"
    fi
    
    # Backend
    if is_port_listening $BACKEND_PORT; then
        printf "%-12s %-8s ${GREEN}%-10s${NC} %s\n" "Backend" "$BACKEND_PORT" "Running" "http://localhost:$BACKEND_PORT"
    else
        printf "%-12s %-8s ${RED}%-10s${NC} %s\n" "Backend" "$BACKEND_PORT" "Stopped" "-"
    fi
    
    # Frontend
    if is_port_listening $FRONTEND_PORT; then
        printf "%-12s %-8s ${GREEN}%-10s${NC} %s\n" "Frontend" "$FRONTEND_PORT" "Running" "http://localhost:$FRONTEND_PORT"
    else
        printf "%-12s %-8s ${RED}%-10s${NC} %s\n" "Frontend" "$FRONTEND_PORT" "Stopped" "-"
    fi
    
    # Gateway
    if is_port_listening $GATEWAY_PORT; then
        printf "%-12s %-8s ${GREEN}%-10s${NC} %s\n" "Gateway" "$GATEWAY_PORT" "Running" "http://localhost:$GATEWAY_PORT"
    else
        printf "%-12s %-8s ${YELLOW}%-10s${NC} %s\n" "Gateway" "$GATEWAY_PORT" "Optional" "-"
    fi
    
    echo ""
    echo -e "${BOLD}Login Credentials:${NC}"
    echo "  Email:    admin@hyperfilelens.com"
    echo "  Password: admin123"
    echo ""
}

# Show service logs
show_logs() {
    local service=${1:-all}
    
    case $service in
        redis)    tail -f "$LOG_DIR/redis.log" ;;
        backend)  tail -f "$LOG_DIR/backend.log" ;;
        frontend) tail -f "$LOG_DIR/frontend.log" ;;
        gateway)  tail -f "$LOG_DIR/gateway.log" ;;
        celery)   tail -f "$LOG_DIR/celery.log" ;;
        all)
            echo "Showing all logs (Ctrl+C to exit)..."
            tail -f "$LOG_DIR"/*.log 2>/dev/null || {
                log_error "No log files found in $LOG_DIR"
                exit 1
            }
            ;;
        *)
            log_error "Unknown service: $service"
            print_help
            exit 1
            ;;
    esac
}

# =============================================================================
# Main Script
# =============================================================================

main() {
    # Parse arguments
    local command="start"
    local services=()
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --no-deps)
                NO_DEPS=true
                shift
                ;;
            --build)
                FORCE_BUILD=true
                shift
                ;;
            start|stop|restart|status|logs|install)
                command=$1
                shift
                ;;
            all|frontend|backend|gateway|redis|celery)
                services+=("$1")
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done
    
    # Setup
    setup_directories
    print_banner
    
    # Execute command
    case $command in
        start)
            if [ "$NO_DEPS" = false ]; then
                install_all_deps
            fi
            start_services "${services[@]}"
            show_status
            ;;
        stop)
            stop_services "${services[@]}"
            show_status
            ;;
        restart)
            if [ "$NO_DEPS" = false ]; then
                install_all_deps
            fi
            restart_services "${services[@]}"
            show_status
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${services[0]:-all}"
            ;;
        install)
            install_all_deps
            ;;
        *)
            log_error "Unknown command: $command"
            print_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
