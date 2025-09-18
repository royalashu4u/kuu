# Kuu Bot Systemctl Installation Guide

This guide will help you set up the Kuu Telegram Bot as a systemd service with zero downtime reload capabilities.

## Prerequisites

- Ubuntu/Debian or CentOS/RHEL system
- Python 3.8 or higher
- Root or sudo access
- Telegram Bot Token

## Installation Steps

### 1. Create System User

```bash
# Create a dedicated user for the bot
sudo useradd -r -s /bin/false -d /root/bot kuu-bot
```

### 2. Set Up Application Directory

```bash
# Create application directory
sudo mkdir -p /root/bot
sudo chown kuu-bot:kuu-bot /root/bot

# Copy your application files
sudo cp -r . /root/bot/
sudo chown -R kuu-bot:kuu-bot /root/bot
```

### 3. Set Up Python Virtual Environment

```bash
# Navigate to application directory
cd /root/bot

# Use existing virtual environment
# The .venv directory already exists, so we'll use it directly

# Activate virtual environment and install dependencies
sudo -u kuu-bot bash -c "source .venv/bin/activate && pip install -r requirements.txt"
```

### 4. Configure Environment

```bash
# Copy environment template
sudo cp env.template /root/bot/.env

# Edit the environment file with your actual values
sudo nano /root/bot/.env
```

Required environment variables:
- `BOT_TOKEN`: Your Telegram bot token
- `ADMIN_USER_ID`: Your Telegram user ID

### 5. Create Required Directories

```bash
# Create data and logs directories
sudo mkdir -p /root/bot/data
sudo mkdir -p /root/bot/logs
sudo mkdir -p /root/bot/backups
sudo chown -R kuu-bot:kuu-bot /root/bot
```

### 6. Install Systemd Service

```bash
# Copy service file to systemd directory
sudo cp kuu-bot.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable kuu-bot
```

### 7. Install Reload Script

```bash
# Copy reload script
sudo cp reload-bot.sh /usr/local/bin/reload-kuu-bot

# Make it executable
sudo chmod +x /usr/local/bin/reload-kuu-bot
```

## Usage

### Starting the Service

```bash
# Start the service
sudo systemctl start kuu-bot

# Check status
sudo systemctl status kuu-bot

# View logs
sudo journalctl -u kuu-bot -f
```

### Zero Downtime Reload

The reload script provides three modes for updating the bot:

#### 1. Graceful Reload (Default)
```bash
# Try graceful reload first, fallback to rolling restart
sudo reload-kuu-bot
# or
sudo reload-kuu-bot graceful
```

#### 2. Rolling Restart
```bash
# Minimal downtime restart
sudo reload-kuu-bot rolling
```

#### 3. Full Restart
```bash
# Full restart with downtime
sudo reload-kuu-bot full
```

### Service Management

```bash
# Start service
sudo systemctl start kuu-bot

# Stop service
sudo systemctl stop kuu-bot

# Restart service
sudo systemctl restart kuu-bot

# Check status
sudo systemctl status kuu-bot

# View logs
sudo journalctl -u kuu-bot

# Follow logs in real-time
sudo journalctl -u kuu-bot -f
```

### Updating the Bot

1. **Update code files:**
   ```bash
   # Copy new files to /root/bot
   sudo cp -r /path/to/new/files/* /root/bot/
   sudo chown -R kuu-bot:kuu-bot /root/bot
   ```

2. **Update dependencies (if needed):**
   ```bash
   sudo -u kuu-bot bash -c "cd /root/bot && source .venv/bin/activate && pip install -r requirements.txt"
   ```

3. **Reload the service:**
   ```bash
   sudo reload-kuu-bot graceful
   ```

## Configuration

### Service Configuration

The service file (`kuu-bot.service`) includes:

- **Security settings**: NoNewPrivileges, PrivateTmp, ProtectSystem
- **Resource limits**: File descriptors and processes
- **Restart policy**: Always restart on failure
- **Logging**: Output to systemd journal

### Environment Configuration

Edit `/opt/kuu-bot/.env` to configure:

- Bot token and admin settings
- Logging levels and file paths
- Performance and security settings

## Monitoring

### Health Checks

The reload script includes health checks that verify:
- Service is running
- Process is responding
- No critical errors

### Logs

- **System logs**: `sudo journalctl -u kuu-bot`
- **Application logs**: `/root/bot/logs/`
- **Reload logs**: `/root/bot/logs/reload.log`

### Backup

The reload script automatically creates backups in `/root/bot/backups/` and keeps the last 10 backups.

## Troubleshooting

### Common Issues

1. **Permission denied errors:**
   ```bash
   sudo chown -R kuu-bot:kuu-bot /root/bot
   ```

2. **Service won't start:**
   ```bash
   # Check logs for errors
   sudo journalctl -u kuu-bot -n 50
   
   # Check environment file
   sudo cat /root/bot/.env
   ```

3. **Reload script fails:**
   ```bash
   # Check script permissions
   ls -la /usr/local/bin/reload-kuu-bot
   
   # Run with verbose output
   sudo bash -x /usr/local/bin/reload-kuu-bot
   ```

### Debug Mode

To run the bot in debug mode:

```bash
# Stop the service
sudo systemctl stop kuu-bot

# Run manually
sudo -u kuu-bot bash -c "cd /root/bot && source .venv/bin/activate && python app.py"
```

## Security Considerations

- The service runs as a non-privileged user (`kuu-bot`)
- File system access is restricted to necessary directories
- Process privileges are limited
- Logs are managed by systemd

## Performance Tuning

- Adjust `LimitNOFILE` and `LimitNPROC` in the service file if needed
- Monitor memory usage with `systemctl status kuu-bot`
- Consider adjusting `RestartSec` based on your needs

## Support

For issues or questions:
1. Check the logs: `sudo journalctl -u kuu-bot`
2. Verify configuration: `sudo cat /opt/kuu-bot/.env`
3. Test manually: Run the bot outside of systemd
4. Check system resources: `htop` or `top`
