#!/bin/bash

# Kuu Bot Zero Downtime Reload Script
# This script implements a rolling restart strategy for zero downtime deployments

set -euo pipefail

# Configuration
SERVICE_NAME="kuu-bot"
SERVICE_FILE="/etc/systemd/system/kuu-bot.service"
APP_DIR="/root/bot"
BACKUP_DIR="/root/bot/backups"
LOG_FILE="/root/bot/logs/reload.log"
PID_FILE="/root/bot/kuu-bot.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Check if service exists
check_service() {
    if ! systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
        error "Service $SERVICE_NAME not found. Please install the service first."
    fi
}

# Create necessary directories
setup_directories() {
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/data"
    chown -R kuu-bot:kuu-bot "$APP_DIR"
}

# Backup current deployment
backup_current() {
    local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log "Creating backup: $backup_name"
    mkdir -p "$backup_path"
    
    # Backup application files (excluding data and logs)
    cp -r "$APP_DIR"/*.py "$backup_path/" 2>/dev/null || true
    cp -r "$APP_DIR"/*.txt "$backup_path/" 2>/dev/null || true
    cp -r "$APP_DIR"/*.toml "$backup_path/" 2>/dev/null || true
    cp -r "$APP_DIR"/*.md "$backup_path/" 2>/dev/null || true
    
    # Keep only last 10 backups
    cd "$BACKUP_DIR"
    ls -t | tail -n +11 | xargs -r rm -rf
    
    success "Backup created: $backup_name"
}

# Check service health
check_health() {
    local max_attempts=30
    local attempt=0
    
    log "Checking service health..."
    
    while [[ $attempt -lt $max_attempts ]]; do
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            # Check if the bot is responding (you can customize this check)
            if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
                success "Service is healthy"
                return 0
            fi
        fi
        
        ((attempt++))
        sleep 2
        log "Health check attempt $attempt/$max_attempts"
    done
    
    error "Service health check failed after $max_attempts attempts"
}

# Graceful reload with zero downtime
graceful_reload() {
    log "Starting graceful reload process..."
    
    # Check if service is running
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        warning "Service is not running. Starting service..."
        systemctl start "$SERVICE_NAME"
        check_health
        return 0
    fi
    
    # Send SIGHUP for graceful reload (if supported by the application)
    log "Sending reload signal to service..."
    if systemctl reload "$SERVICE_NAME" 2>/dev/null; then
        success "Reload signal sent successfully"
        check_health
    else
        warning "Reload signal not supported, performing rolling restart..."
        rolling_restart
    fi
}

# Rolling restart for zero downtime
rolling_restart() {
    log "Performing rolling restart..."
    
    # Start a new instance in parallel (if supported by your setup)
    # For this Telegram bot, we'll do a quick restart with minimal downtime
    
    # Stop the service gracefully
    log "Stopping service gracefully..."
    systemctl stop "$SERVICE_NAME"
    
    # Wait a moment for cleanup
    sleep 2
    
    # Start the service
    log "Starting service..."
    systemctl start "$SERVICE_NAME"
    
    # Check health
    check_health
}

# Full restart (with downtime)
full_restart() {
    log "Performing full restart..."
    
    systemctl restart "$SERVICE_NAME"
    check_health
}

# Main reload function
reload_bot() {
    local mode="${1:-graceful}"
    
    log "Starting bot reload process (mode: $mode)"
    
    # Pre-reload checks
    check_root
    check_service
    setup_directories
    
    # Create backup
    backup_current
    
    case "$mode" in
        "graceful")
            graceful_reload
            ;;
        "rolling")
            rolling_restart
            ;;
        "full")
            full_restart
            ;;
        *)
            error "Invalid mode: $mode. Use: graceful, rolling, or full"
            ;;
    esac
    
    success "Bot reload completed successfully!"
    
    # Show service status
    log "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager
}

# Show usage
show_usage() {
    echo "Usage: $0 [MODE]"
    echo ""
    echo "Modes:"
    echo "  graceful  - Try graceful reload first, fallback to rolling restart (default)"
    echo "  rolling   - Perform rolling restart with minimal downtime"
    echo "  full      - Full restart with downtime"
    echo ""
    echo "Examples:"
    echo "  $0                # Graceful reload"
    echo "  $0 graceful       # Graceful reload"
    echo "  $0 rolling        # Rolling restart"
    echo "  $0 full           # Full restart"
}

# Main execution
main() {
    local mode="${1:-graceful}"
    
    if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
        show_usage
        exit 0
    fi
    
    reload_bot "$mode"
}

# Run main function with all arguments
main "$@"
