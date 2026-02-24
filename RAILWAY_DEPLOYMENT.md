# Railway Deployment Guide

## Overview
This guide walks through deploying the Pharma Regulatory Intelligence Platform to Railway.app.

## Prerequisites
- Railway account (https://railway.app)
- Git repository (GitHub, GitLab, or Bitbucket)
- OpenAI API key
- Basic knowledge of Railway's dashboard

## Architecture
```
Your Git Repository
        ↓
    Railway.app
        ├── Backend Service (Python/FastAPI)
        │   └── PostgreSQL Database
        └── Frontend Service (Next.js)
```

## Step 1: Prepare Your Repository

1. **Initialize Git** (if not already done):
```bash
cd /path/to/REG
git init
git add .
git commit -m "Initial commit: Hybrid Intelligence Platform"
```

2. **Create `.gitignore`** at project root:
```
# Python
__pycache__/
*.py[cod]
*.so
env/
venv/
.env

# Node
node_modules/
.next
*.log
npm-debug.log*

# OS
.DS_Store
.vscode
.idea

# SQLite (use PostgreSQL in production)
*.sqlite3
```

3. **Push to GitHub/GitLab**:
```bash
git remote add origin https://github.com/yourusername/pharma-reg-intelligence.git
git branch -M main
git push -u origin main
```

## Step 2: Set Up Railway Project

### 2.1 Create New Project
1. Go to Railway dashboard: https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Authorize Railway to access your repositories
5. Select your `pharma-reg-intelligence` repository

### 2.2 Create Backend Service
1. In Railway dashboard, click "Add Service"
2. Select "Database" → "PostgreSQL"
   - Railway auto-configures `DATABASE_URL` environment variable
   - PostgreSQL runs in the same private network as your backend

### 2.3 Add Backend Application
1. Click "Add Service" → "GitHub Repo"
2. Select your repository
3. Railway detects `backend/Dockerfile` and uses it
4. Configure Service:
   - **Name**: `backend`
   - **Root Directory**: `backend/`
   - **Watch Paths**: `backend/**` (optional, for auto-redeploy)

### 2.4 Environment Variables - Backend
Set these in Railway dashboard (Backend Service):

```
OPENAI_API_KEY          = sk-your-openai-api-key
SECRET_KEY              = generate-a-secure-random-string
SCRAPE_INTERVAL_MINUTES = 360
FRONTEND_URL            = https://frontend-random.railway.app
```

The `DATABASE_URL` is automatically provided by the PostgreSQL plugin.

### 2.5 Add Frontend Application
1. Click "Add Service" → "GitHub Repo"
2. Select your repository
3. Configure Service:
   - **Name**: `frontend`
   - **Root Directory**: `frontend/`
   - **Port**: `3000` (Next.js default)

### 2.6 Environment Variables - Frontend
Set these in Railway dashboard (Frontend Service):

```
NEXT_PUBLIC_API_URL = https://backend-random.railway.app/api
```

## Step 3: Verify Deployment

### 3.1 Check Backend Service
1. Go to Backend service page
2. Click "Deployments" tab
3. Wait until status is "✓ Success" (usually 5-10 minutes)
4. Note the generated domain (e.g., `backend-random.railway.app`)
5. Test the API:
```bash
curl -X POST https://backend-random.railway.app/api/v1/ai/query \
  -H "Content-Type: application/json" \
  -d '{"query":"FDA approval guidelines"}'
```

### 3.2 Check Frontend Service
1. Go to Frontend service page
2. Click "Deployments" tab
3. Wait until deployment is complete
4. Note the generated domain (e.g., `frontend-random.railway.app`)
5. Visit the URL in browser to test

### 3.3 Database Verification
1. Go to PostgreSQL service
2. Check "Network" tab to confirm it's accessible to backend
3. No external port needed - backend connects privately

## Step 4: Update Environment Variables

**IMPORTANT**: Update frontend environment variable with actual backend URL:

1. Go to Frontend service settings
2. Find `NEXT_PUBLIC_API_URL`
3. Update to the actual backend domain from Railway
4. Trigger a redeploy (Railway auto-detects or manual push)

## Step 5: Production Checklist

- [ ] Backend builds successfully in Railway
- [ ] PostgreSQL database is created and accessible
- [ ] Environment variables set correctly
- [ ] Frontend builds successfully  
- [ ] API endpoint responds to test query
- [ ] Frontend loads and can make API calls
- [ ] CORS properly configured (check backend)
- [ ] OpenAI API key is valid and working
- [ ] No sensitive data in git history
- [ ] Domain names configured in both services

## Troubleshooting

### Backend won't start
1. Check Logs tab for error messages
2. Verify environment variables are set
3. Ensure `requirements.txt` has all dependencies
4. Check `DATABASE_URL` format

### Frontend shows "API not found"
1. Verify `NEXT_PUBLIC_API_URL` is set correctly
2. Check backend service is running
3. Verify CORS in `backend/app/main.py`:
```python
allow_origins=[
    "https://your-frontend-domain.railway.app",
    "http://localhost:3000"
]
```

### Database connection fails
1. Verify `DATABASE_URL` is set in backend environment
2. Check PostgreSQL service is running
3. Ensure both services are in same Railway project

### Slow initial response
1. Railway containers may be cold-starting
2. Normal - subsequent requests are faster
3. Consider Railway's paid tier for always-on

## Monitoring & Maintenance

### View Logs
- Go to service → "Logs" tab
- Real-time log streaming for debugging

### Monitor Usage
- Railway dashboard shows:
  - CPU/Memory usage
  - Network traffic
  - Deployment history
  - Uptime metrics

### Update Code
Simply push to GitHub - Railway auto-redeploys:
```bash
git commit -am "Update AI logic"
git push origin main
```

## Scaling & Optimization

### Enable Auto-Scaling (Premium)
1. Service settings → "Scaling"
2. Set min/max replicas based on traffic

### Optimize Database
PostgreSQL on Railway includes automatic backups and monitoring

### Custom Domain
1. Railway console → Project settings
2. Add custom domain (requires DNS configuration)
3. SSL certificate auto-provisioned

## Cost Estimates (as of Feb 2026)

| Service | Estimate | Notes |
|---------|----------|-------|
| Backend (Python) | $5-15/month | 512MB RAM minimum |
| Frontend (Node.js) | $5-15/month | Basic traffic |
| PostgreSQL | $10-20/month | 1GB storage |
| **Total** | **$20-50/month** | Usage-based pricing |

Free tier available for small projects!

## Next Steps After Deployment

1. **Configure Monitoring**
   - Set up Railway alerts
   - Monitor error logs
   - Track API usage

2. **Optimize Performance**
   - Enable Railway's caching
   - Consider CDN for frontend assets
   - Optimize database queries

3. **Scheduled Tasks**
   - Guideline scrapers run on backend
   - Set `SCRAPE_INTERVAL_MINUTES` environment variable
   - Monitor scraper logs

4. **Backup Strategy**
   - PostgreSQL auto-backups daily
   - Export backups weekly
   - Test restore procedure

## Support & Resources

- Railway Docs: https://docs.railway.app
- Railway Community: https://railway.app/discord
- Issue Tracking: Check Railway dashboard for error details
- FastAPI Docs: http://backend-domain.railway.app/docs
- API Status: Test endpoint regularly

---

**Last Updated**: February 24, 2026
**Status**: Production Ready
**Deployment Time**: 10-15 minutes (first time)
