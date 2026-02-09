# Oracle Cloud Free Tier Deployment Guide

## What You Get (FREE Forever)
- 2x ARM-based VMs (4 CPU cores, 24GB RAM total)
- 200GB storage
- 10TB bandwidth/month
- No credit card required for free tier

---

## Step 1: Oracle Cloud Account Setup

### A. Sign Up
1. Go to https://www.oracle.com/cloud/free/
2. Click **"Start for free"**
3. Fill out registration form:
   - Email address
   - Country/Territory
   - Choose a cloud account name (this becomes part of your URL)
4. Verify email and set password
5. **Skip** the credit card step if you're only using free tier (it's optional)

### B. Create a Compute Instance (VM)

1. **Log in** to Oracle Cloud Console: https://cloud.oracle.com
2. Click **"Create a VM instance"** on the dashboard
3. **Instance Configuration:**
   - Name: `lawn-intel-dashboard`
   - Placement: Keep default
   - Image: **Ubuntu 22.04 (Minimal)**
     - Click "Change Image"
     - Select "Canonical Ubuntu"
     - Choose "22.04 Minimal" (ARM or AMD64, both work)
   - Shape: **VM.Standard.A1.Flex** (ARM - free tier)
     - Click "Change Shape"
     - Select "Ampere" family
     - Choose **2 OCPUs, 12GB RAM** (free tier eligible)
     - This gives you room to run the app + nginx

4. **Networking:**
   - Create new VCN (Virtual Cloud Network) - keep defaults
   - Assign a public IPv4 address: **YES** ✓
   - **IMPORTANT:** Download your SSH key pair
     - Save the private key as `lawn-oracle-key.pem`
     - You'll need this to connect

5. Click **"Create"** (takes ~2 minutes to provision)

---

## Step 2: Configure Firewall Rules

### A. Oracle Cloud Security List (Cloud Firewall)

1. After instance is created, click on the instance name
2. Under **"Instance Details"** → **"Primary VNIC"** → Click your subnet name
3. Click **"Default Security List"**
4. Click **"Add Ingress Rules"**

Add these two rules:

**Rule 1: HTTP (Port 80)**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: `TCP`
- Destination Port Range: `80`
- Description: `HTTP for dashboard`

**Rule 2: HTTPS (Port 443)** - optional for now, we'll add SSL later
- Source CIDR: `0.0.0.0/0`
- IP Protocol: `TCP`
- Destination Port Range: `443`
- Description: `HTTPS for dashboard`

**Rule 3: SSH (Port 22)** - should already exist
- If not, add it with port `22`

---

### B. Ubuntu Firewall (iptables/ufw)

Oracle Cloud instances also have Ubuntu's firewall enabled. We'll disable it via SSH in the next step.

---

## Step 3: Connect to Your VM

### On Your Local Machine (CachyOS)

1. **Move your SSH key to .ssh folder:**
   ```bash
   mkdir -p ~/.ssh
   mv ~/Downloads/lawn-oracle-key.pem ~/.ssh/
   chmod 600 ~/.ssh/lawn-oracle-key.pem
   ```

2. **Get your instance's public IP:**
   - Oracle Cloud Console → Compute → Instances
   - Copy the **Public IP address** (looks like `xxx.xxx.xxx.xxx`)

3. **Connect via SSH:**
   ```bash
   ssh -i ~/.ssh/lawn-oracle-key.pem ubuntu@YOUR_PUBLIC_IP
   ```

4. **First time connecting:**
   - Type `yes` when prompted about fingerprint
   - You should now be logged in as `ubuntu@lawn-intel-dashboard`

---

## Step 4: Disable Ubuntu Firewall

Oracle Cloud's firewall is already protecting your VM. Ubuntu's firewall causes conflicts.

```bash
sudo iptables -F
sudo iptables -X
sudo netfilter-persistent save
```

Or if using ufw:
```bash
sudo ufw disable
```

---

## Step 5: Deploy the Application

### A. Upload Your Code to the VM

**From your local machine** (in a new terminal, NOT the SSH session):

```bash
cd ~/projects/lawn-eve-intel-dashboard

# Create a tarball (excludes git, venv, etc.)
tar czf lawn-intel.tar.gz \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.vscode' \
  .

# Upload to VM
scp -i ~/.ssh/lawn-oracle-key.pem \
  lawn-intel.tar.gz \
  ubuntu@YOUR_PUBLIC_IP:~/

# Clean up local tarball
rm lawn-intel.tar.gz
```

### B. Extract and Deploy on VM

**Back in your SSH session** (on the VM):

```bash
# Extract uploaded files
mkdir -p ~/lawn-eve-intel-dashboard
tar xzf lawn-intel.tar.gz -C ~/lawn-eve-intel-dashboard
cd ~/lawn-eve-intel-dashboard

# Run deployment script
./deploy-oracle.sh
```

**What the script does:**
- Installs Docker & Docker Compose
- Installs and configures nginx
- Builds your Docker image
- Starts the application
- Sets up auto-restart on reboot

**Note:** If Docker install requires logout, do this:
```bash
exit  # logout
ssh -i ~/.ssh/lawn-oracle-key.pem ubuntu@YOUR_PUBLIC_IP  # log back in
cd ~/lawn-eve-intel-dashboard
./deploy-oracle.sh  # run again
```

---

## Step 6: Verify It's Running

1. **Check app status:**
   ```bash
   docker-compose ps
   curl http://localhost:5000/api/status
   ```

2. **Check nginx:**
   ```bash
   sudo systemctl status nginx
   curl http://localhost
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Open in your browser:**
   - Go to: `http://YOUR_PUBLIC_IP`
   - You should see your LAWN Intel Dashboard!

---

## Step 7: (Optional) Set Up a Domain Name

### Using a Custom Domain (Free with Cloudflare)

1. **Buy a domain** (or use existing):
   - Namecheap, Porkbun, Cloudflare Registrar (~$10/year)

2. **Add to Cloudflare** (free plan):
   - Sign up at https://www.cloudflare.com
   - Add your domain
   - Update nameservers at your registrar

3. **Create DNS A record:**
   - Name: `lawn` (or `@` for root domain)
   - Type: `A`
   - Content: `YOUR_ORACLE_PUBLIC_IP`
   - Proxy status: DNS only (grey cloud) for now

4. **Update nginx config on VM:**
   ```bash
   sudo nano /etc/nginx/sites-available/lawn-intel
   ```

   Change:
   ```nginx
   server_name _;
   ```

   To:
   ```nginx
   server_name lawn.yourdomain.com;
   ```

5. **Add SSL with Let's Encrypt:**
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d lawn.yourdomain.com
   ```

---

## Useful Commands (Run on VM)

### Application Management
```bash
cd ~/lawn-eve-intel-dashboard

# View logs
docker-compose logs -f

# Restart app
docker-compose restart

# Stop app
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Check status
docker-compose ps
curl http://localhost:5000/api/status
```

### Nginx Management
```bash
# Check status
sudo systemctl status nginx

# Restart nginx
sudo systemctl restart nginx

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Test config
sudo nginx -t
```

### System Monitoring
```bash
# CPU/Memory usage
htop

# Disk usage
df -h

# Check open ports
sudo ss -tulpn | grep LISTEN
```

---

## Updating Your App

When you make changes locally:

```bash
# On local machine
cd ~/projects/lawn-eve-intel-dashboard
tar czf lawn-intel.tar.gz \
  --exclude='.git' --exclude='.venv' --exclude='__pycache__' .
scp -i ~/.ssh/lawn-oracle-key.pem lawn-intel.tar.gz ubuntu@YOUR_PUBLIC_IP:~/
rm lawn-intel.tar.gz

# On VM
cd ~/lawn-eve-intel-dashboard
tar xzf ~/lawn-intel.tar.gz -C .
docker-compose up -d --build
```

Or set up **git deployment**:
```bash
# On VM - first time only
cd ~/lawn-eve-intel-dashboard
git init
git remote add origin YOUR_GITHUB_REPO_URL

# To update
git pull origin main
docker-compose up -d --build
```

---

## Troubleshooting

### Can't connect to public IP?
- Check Oracle Cloud security list has port 80 ingress rule
- Check instance is running (green status in console)
- Verify public IP is correct
- Try: `curl -v http://YOUR_PUBLIC_IP`

### Docker permission denied?
```bash
sudo usermod -aG docker $USER
exit  # logout and log back in
```

### App won't start?
```bash
docker-compose logs
# Check for Python errors or missing dependencies
```

### nginx errors?
```bash
sudo nginx -t  # test config
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

### Out of disk space?
```bash
# Clean up Docker
docker system prune -a

# Check disk
df -h
```

---

## Cost Monitoring

Your free tier includes:
- ✅ 2 VMs with 4 OCPUs + 24GB RAM total (ARM)
- ✅ 200GB storage
- ✅ 10TB outbound bandwidth/month

**This dashboard uses minimal resources:**
- ~500MB RAM for Flask + nginx
- ~2GB disk space
- ~10-50GB bandwidth/month (depends on usage)

You should stay well within free tier limits. Check Oracle Cloud console → Billing to monitor usage.

---

## Next Steps

- Set up a domain name + SSL
- Configure monitoring/alerts
- Set up automated backups
- Add Discord webhook notifications (future feature)
- Consider setting up git-based deployments

---

**Need help?** Check logs with `docker-compose logs -f` or open an issue in the repo.
