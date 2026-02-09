# Hetzner Cloud Deployment Guide

## What You Get: €3.79/mo (~$4.20)
- **4GB RAM** (massive compared to other options)
- **2 vCPU**
- **40GB SSD**
- **20TB bandwidth/month**
- Germany or Finland data center (100-150ms to US East Coast)

---

## Step 1: Create Hetzner Account

1. Go to https://www.hetzner.com/cloud
2. Click **"Sign up"** (top right)
3. Fill in details:
   - Email
   - Name
   - Password
4. **Verify email** (check inbox)
5. **Add payment method** (credit card or PayPal)
   - Don't worry, you can delete the server anytime
   - Billed hourly (~€0.0052/hour, capped at €3.79/mo)

---

## Step 2: Create a Project

1. Log in to https://console.hetzner.cloud
2. Click **"New Project"**
3. Name: `lawn-intel-dashboard`
4. Click **"Add Project"**

---

## Step 3: Create a Server

1. Inside your project, click **"Add Server"**

2. **Location:**
   - **Nuremberg, Germany** (nbg1) - recommended
   - Or **Falkenstein, Germany** (fsn1)
   - Or **Helsinki, Finland** (hel1)

3. **Image:**
   - **Ubuntu 22.04**

4. **Type:**
   - **Shared vCPU** → **CPX11**
   - €3.79/mo - 2 vCPU, 4GB RAM, 40GB SSD
   - (This is the one you want!)

5. **Networking:**
   - ✅ **Public IPv4** (included)
   - ✅ **Public IPv6** (free, included)

6. **SSH keys (Recommended):**
   - Click **"Add SSH key"**

   **On your local machine (CachyOS):**
   ```bash
   # Generate SSH key if you don't have one
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Press Enter for defaults (~/.ssh/id_ed25519)

   # Copy public key
   cat ~/.ssh/id_ed25519.pub
   # Copy the output
   ```

   - Paste into Hetzner
   - Name: "CachyOS Main"
   - Click **"Add SSH key"**

   **Or use Password:**
   - You'll get root password via email

7. **Volumes:** Skip (not needed)

8. **Firewalls:** Skip for now (we'll use UFW)

9. **Backups:**
   - Optional: +20% cost (€0.76/mo extra)
   - Can enable later

10. **Placement Groups:** Skip

11. **Labels:** Optional (e.g., `app:intel-dashboard`, `env:production`)

12. **Cloud config:** Leave empty

13. **Name:** `lawn-intel-01`

14. **Click "Create & Buy now"**

Server will be ready in **~30 seconds**!

---

## Step 4: Get Server IP Address

1. In Hetzner console, click on your server name
2. Copy the **IPv4 address** (looks like `xxx.xxx.xxx.xxx`)

---

## Step 5: Connect via SSH

**From your local machine:**

```bash
# If you used SSH key
ssh root@YOUR_SERVER_IP

# If you used password (check email)
ssh root@YOUR_SERVER_IP
# Enter password when prompted
```

**First time connecting:**
- Type `yes` to accept fingerprint
- You're now logged in as root

---

## Step 6: Initial Server Setup

### A. Update System
```bash
apt update && apt upgrade -y
```

### B. Create Non-Root User (Best Practice)
```bash
# Create user
adduser lawn
# Enter password when prompted

# Add to sudo group
usermod -aG sudo lawn

# Copy SSH keys to new user (if you used SSH)
rsync --archive --chown=lawn:lawn ~/.ssh /home/lawn
```

### C. Switch to New User
```bash
su - lawn
```

---

## Step 7: Upload and Deploy Your App

### A. Upload Code from Local Machine

**Open a new terminal on your local machine (CachyOS):**

```bash
cd ~/projects/lawn-eve-intel-dashboard

# Create tarball
tar czf lawn-intel.tar.gz \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  .

# Upload to server
scp lawn-intel.tar.gz root@YOUR_SERVER_IP:/home/lawn/

# If you're connected as lawn user with SSH key
scp lawn-intel.tar.gz lawn@YOUR_SERVER_IP:~/

# Clean up local tarball
rm lawn-intel.tar.gz
```

### B. Extract and Deploy on Server

**Back in your SSH session (as lawn user):**

```bash
# Make sure you're the lawn user
whoami  # should say "lawn"

# Extract files
mkdir -p ~/lawn-eve-intel-dashboard
tar xzf ~/lawn-intel.tar.gz -C ~/lawn-eve-intel-dashboard
cd ~/lawn-eve-intel-dashboard

# Make deploy script executable
chmod +x deploy-oracle.sh

# Run deployment script
./deploy-oracle.sh
```

**What the script does:**
- Installs Docker & Docker Compose
- Installs nginx
- Builds Docker image
- Starts your application
- Configures auto-restart on reboot

**If Docker requires logout:**
```bash
exit  # logout
ssh lawn@YOUR_SERVER_IP  # or root@YOUR_SERVER_IP
cd ~/lawn-eve-intel-dashboard
./deploy-oracle.sh  # run again
```

---

## Step 8: Configure Firewall

```bash
# Allow SSH (CRITICAL - do this first!)
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS (for SSL later)
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
# Type 'y' to confirm

# Check status
sudo ufw status
```

---

## Step 9: Verify It's Working

### Test Locally on Server
```bash
# Check Docker container
docker-compose ps

# Check app health
curl http://localhost:5000/api/status

# Check nginx
sudo systemctl status nginx
curl http://localhost
```

### Test from Browser

**Open in your browser:**
```
http://YOUR_SERVER_IP
```

You should see your **LAWN Intel Dashboard**!

---

## Step 10: Set Up Your Domain Name

### A. Configure DNS (At Your Domain Registrar)

1. **Log in to your domain registrar** (Namecheap, GoDaddy, Cloudflare, etc.)

2. **Add DNS records:**

   **A Record (IPv4):**
   - **Name/Host:** `lawn` (for lawn.yourdomain.com)
     - Or `@` for root domain (yourdomain.com)
   - **Type:** `A`
   - **Value:** `YOUR_HETZNER_SERVER_IP`
   - **TTL:** 300 (5 minutes) or Auto

   **AAAA Record (IPv6) - Optional but recommended:**
   - **Name/Host:** `lawn`
   - **Type:** `AAAA`
   - **Value:** `YOUR_HETZNER_IPV6_ADDRESS` (from Hetzner console)
   - **TTL:** 300

3. **Save changes**

4. **Wait for DNS propagation** (5-60 minutes)

### B. Test DNS Propagation

**On your local machine:**
```bash
# Test if DNS is working
dig lawn.yourdomain.com

# Should return your server IP
nslookup lawn.yourdomain.com
```

### C. Update nginx Configuration

**On your server:**
```bash
sudo nano /etc/nginx/sites-available/lawn-intel
```

**Find this line:**
```nginx
server_name _;
```

**Change it to:**
```nginx
server_name lawn.yourdomain.com;
```
(Replace with your actual domain)

**Save and exit:**
- Press `Ctrl+X`
- Press `Y` to confirm
- Press `Enter`

**Test and reload nginx:**
```bash
# Test config syntax
sudo nginx -t

# If OK, reload nginx
sudo systemctl reload nginx
```

### D. Add Free SSL Certificate (Let's Encrypt)

**Install Certbot:**
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

**Get SSL certificate:**
```bash
sudo certbot --nginx -d lawn.yourdomain.com
```

**Follow the prompts:**
- Enter your email address (for renewal notifications)
- Agree to Terms of Service (type 'Y')
- Share email? (optional, type 'N' if you prefer not to)
- Redirect HTTP to HTTPS? **Choose option 2: Redirect**

**Test auto-renewal:**
```bash
sudo certbot renew --dry-run
```

**Done! Your site is now live at:**
- ✅ `https://lawn.yourdomain.com` (with SSL)
- ✅ HTTP automatically redirects to HTTPS

---

## Useful Commands

### Application Management
```bash
cd ~/lawn-eve-intel-dashboard

# View logs (live tail)
docker-compose logs -f

# View last 50 lines
docker-compose logs --tail=50

# Restart application
docker-compose restart

# Stop application
docker-compose down

# Start application
docker-compose up -d

# Rebuild and restart (after code changes)
docker-compose up -d --build

# Check container status
docker-compose ps
docker ps
```

### Nginx Management
```bash
# Check status
sudo systemctl status nginx

# Restart nginx
sudo systemctl restart nginx

# Reload config (no downtime)
sudo systemctl reload nginx

# Test config
sudo nginx -t

# View access logs
sudo tail -f /var/log/nginx/access.log

# View error logs
sudo tail -f /var/log/nginx/error.log
```

### System Monitoring
```bash
# CPU and Memory usage (interactive)
htop
# If not installed: sudo apt install htop

# Quick memory check
free -h

# Disk usage
df -h

# Check open ports
sudo ss -tulpn | grep LISTEN

# Check system load
uptime

# Process list
ps aux | grep -E 'docker|nginx|python'
```

### Server Management
```bash
# Reboot server
sudo reboot

# Check system logs
sudo journalctl -xe

# Check last boot time
uptime
```

---

## Updating Your Application

### Method 1: Manual Upload

**On your local machine:**
```bash
cd ~/projects/lawn-eve-intel-dashboard
tar czf lawn-intel.tar.gz --exclude='.git' --exclude='.venv' --exclude='__pycache__' .
scp lawn-intel.tar.gz lawn@YOUR_SERVER_IP:~/
rm lawn-intel.tar.gz
```

**On your server:**
```bash
cd ~/lawn-eve-intel-dashboard
tar xzf ~/lawn-intel.tar.gz
docker-compose up -d --build
```

### Method 2: Git Deployment (Recommended)

**One-time setup on server:**
```bash
cd ~/lawn-eve-intel-dashboard

# If you haven't pushed to GitHub yet
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/lawn-eve-intel-dashboard.git
git push -u origin main

# If repo already exists on GitHub
git clone https://github.com/yourusername/lawn-eve-intel-dashboard.git ~/lawn-eve-intel-dashboard
cd ~/lawn-eve-intel-dashboard
```

**To update later:**
```bash
cd ~/lawn-eve-intel-dashboard
git pull origin main
docker-compose up -d --build
```

---

## Optional: Hetzner Cloud Firewall

Hetzner offers a free cloud firewall that sits before your server:

1. **Hetzner Console** → **Firewalls** (left menu)
2. **Create Firewall**
3. **Name:** `lawn-intel-firewall`
4. **Inbound Rules:**
   - **SSH:** TCP, Port 22, Sources: `0.0.0.0/0, ::/0`
     - Or restrict to your IP for better security
   - **HTTP:** TCP, Port 80, Sources: `0.0.0.0/0, ::/0`
   - **HTTPS:** TCP, Port 443, Sources: `0.0.0.0/0, ::/0`
5. **Outbound Rules:** Allow all (default)
6. **Apply to resources:** Select your server
7. **Create firewall**

This adds an extra security layer on top of UFW.

---

## Cost Breakdown

**Server:** €3.79/mo (~$4.20)
- Billed hourly: €0.0052/hour
- Capped at €3.79/mo maximum
- Only pay for what you use (can delete anytime)

**Optional extras:**
- Backups: +€0.76/mo (20% of server cost)
- Volumes: €0.04/GB/mo (if you add extra storage)
- Snapshots: €0.014/GB/mo (manual backups)

**Bandwidth:** 20TB included (plenty for this app)

**Total typical cost:** €3.79/mo = ~$4.20/mo

---

## Performance Notes

### Latency from US
- **US East Coast:** ~100-120ms
- **US West Coast:** ~150-170ms
- **For your dashboard:** This is fine!
  - ESI data cached for 5 minutes
  - Page loads once, then uses cached data
  - Users won't notice the difference

### Server Performance
- **4GB RAM:** Plenty of headroom
  - App uses ~300-500MB
  - nginx uses ~50MB
  - ~3GB free for cache and buffers
- **2 vCPU:** More than enough for Flask app
- **40GB SSD:** Fast disk I/O

---

## Backup Strategy

### Option 1: Hetzner Automated Backups (+€0.76/mo)
1. **Server page** → **Backups** tab
2. **Enable backups**
3. Creates daily backups, keeps last 7 days
4. Can restore with one click

### Option 2: Manual Snapshots (€0.014/GB/mo)
1. **Server page** → **Snapshots** tab
2. **Create Snapshot** (takes ~1-2 min)
3. Snapshots persist until deleted
4. Useful before major changes

### Option 3: Application-Level Backups (Free)
```bash
# On server - backup entire app directory
cd ~
tar czf lawn-backup-$(date +%Y%m%d).tar.gz lawn-eve-intel-dashboard

# Download to local machine
scp lawn@YOUR_SERVER_IP:~/lawn-backup-*.tar.gz ~/backups/
```

---

## Troubleshooting

### Can't connect via SSH?
```bash
# Check if server is running (Hetzner console)
# Try verbose mode
ssh -v lawn@YOUR_SERVER_IP

# Check key permissions
chmod 600 ~/.ssh/id_ed25519
```

### Docker permission denied?
```bash
sudo usermod -aG docker $USER
exit  # log out and back in
```

### nginx won't start?
```bash
# Check config
sudo nginx -t

# Check what's using port 80
sudo lsof -i :80

# View errors
sudo tail -f /var/log/nginx/error.log
```

### Application errors?
```bash
cd ~/lawn-eve-intel-dashboard
docker-compose logs --tail=100

# Check if container is running
docker-compose ps

# Restart
docker-compose restart
```

### Out of disk space?
```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a
# Warning: This removes unused images/containers

# Check large files
sudo du -sh /* | sort -h
```

### SSL certificate failed?
```bash
# Make sure DNS is working first
dig lawn.yourdomain.com

# Check nginx config
sudo nginx -t

# Try certbot again
sudo certbot --nginx -d lawn.yourdomain.com
```

---

## Scaling Up (If Needed Later)

Hetzner makes it easy to upgrade:

1. **Server page** → **Resize**
2. Choose new plan:
   - CPX21: €7.29/mo - 3 vCPU, 8GB RAM
   - CPX31: €13.79/mo - 4 vCPU, 16GB RAM
3. **Resize** (takes ~1 minute, brief downtime)

You can also downgrade later!

---

## Deleting the Server (If You Want to Stop Paying)

1. **Server page** → **⋮** (three dots) → **Delete**
2. Confirm deletion
3. You'll only be charged for the hours you used

---

## Next Steps After Deployment

- ✅ Set up monitoring (htop, or install something like Netdata)
- ✅ Enable automated backups
- ✅ Configure Discord webhooks for intel alerts (future feature)
- ✅ Set up git-based deployments
- ✅ Add database persistence for historical data

---

**Need help?** Check logs with `docker-compose logs -f` or ping your corp!

**Enjoy your dashboard at `https://lawn.yourdomain.com`!** 🚀
