#!/bin/bash
# =====================================================
# HyperFileLens Entrypoint Script
# Handles database migrations and service startup
# =====================================================

set -e

echo "=========================================="
echo "HyperFileLens Starting..."
echo "=========================================="

# Wait for database to be ready
wait_for_db() {
    echo "Waiting for database..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python manage.py check --database default 2>/dev/null; then
            echo "Database is ready!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Database not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "ERROR: Database not ready after $max_attempts attempts"
    return 1
}

# Run database migrations
run_migrations() {
    echo "Running database migrations..."
    python manage.py migrate --noinput
    echo "Migrations completed!"
}

# Create superuser if not exists
create_superuser() {
    echo "Checking for superuser..."
    python manage.py check --deploy 2>/dev/null || true
}

# Collect static files
collect_static() {
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear 2>/dev/null || true
}

# Register periodic tasks
register_periodic_tasks() {
    echo "Registering periodic tasks..."
    python manage.py register_periodic_tasks 2>/dev/null || true
}

# Initialize agentcore
init_agentcore() {
    echo "Initializing agentcore..."
    python manage.py agentcore_sync 2>/dev/null || true
}

# Start the application
start_application() {
    echo "=========================================="
    echo "Starting application: $@"
    echo "=========================================="
    exec "$@"
}

# Main execution flow
main() {
    # Change to app directory
    cd /app
    
    # Wait for database
    wait_for_db
    
    # Run migrations
    run_migrations
    
    # Collect static files
    collect_static
    
    # Register periodic tasks
    register_periodic_tasks
    
    # Initialize agentcore
    init_agentcore
    
    # Start the application
    if [ $# -eq 0 ]; then
        # Default: run ASGI so WebSocket Proxy/Gateway agents work.
        start_application daphne -b 0.0.0.0 -p 8000 core.asgi:application
    else
        start_application "$@"
    fi
}

# Run main function with all arguments
main "$@"
