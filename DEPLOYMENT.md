# Deployment Guide

## Prerequisites

- Docker (optional, for containerized deployment)
- Node.js 16+ (for frontend)
- Python 3.9+ (for backend)
- PostgreSQL 12+ (for database)

## Deployment Options

### Option 1: Local Deployment (Development)

See `backend/SETUP.md` and `frontend/SETUP.md`

### Option 2: Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: shared_expenses
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/shared_expenses
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: production
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:5000

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up --build
```

### Option 3: Cloud Deployment

#### Backend (Render.com)

1. Push code to GitHub
2. Create new Web Service on Render
3. Select repository
4. Set Environment:
   ```
   DATABASE_URL=postgresql://...
   SECRET_KEY=your-secret
   ENVIRONMENT=production
   ```
5. Build command: `pip install -r requirements.txt`
6. Start command: `uvicorn src.index:app --host 0.0.0.0`

#### Frontend (Vercel)

1. Push code to GitHub
2. Create new project on Vercel
3. Select frontend folder
4. Set environment variable:
   ```
   VITE_API_URL=https://your-backend.onrender.com
   ```
5. Deploy

#### Database (ElephantSQL or Render Postgres)

1. Create managed PostgreSQL database
2. Get connection string
3. Use as DATABASE_URL in backend

### Option 4: Manual Server Deployment

#### Ubuntu/Linux VPS

```bash
# SSH into server
ssh user@server.ip

# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv postgresql postgresql-contrib nodejs npm

# Clone repository
git clone <your-repo> shared-expenses
cd shared-expenses

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://user:password@localhost/shared_expenses
SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
EOF

# Create systemd service
sudo cat > /etc/systemd/system/shared-expenses-api.service << EOF
[Unit]
Description=Shared Expenses API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/home/user/shared-expenses/backend
ExecStart=/home/user/shared-expenses/backend/venv/bin/uvicorn src.index:app --host 0.0.0.0 --port 5000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable shared-expenses-api
sudo systemctl start shared-expenses-api

# Frontend setup
cd ../frontend
npm install
npm run build

# Setup Nginx
sudo apt install nginx
sudo cat > /etc/nginx/sites-available/shared-expenses << EOF
server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /home/user/shared-expenses/frontend/dist;
        try_files $uri /index.html;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/shared-expenses /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Performance Optimization

### Backend
- Use connection pooling for database
- Enable gzip compression
- Cache frequently accessed data
- Use CDN for static files

### Frontend
- Enable gzip compression
- Minify CSS/JS
- Use lazy loading for images
- Service worker for offline support

## Monitoring

### Logs
```bash
# Backend logs
docker logs <container-id>

# System logs
journalctl -u shared-expenses-api -f
```

### Health Checks

Backend health check:
```
GET /health
```

Frontend availability check:
Monitor with service like Uptime Robot

## Backup Strategy

### Database
```bash
# Backup
pg_dump shared_expenses > backup.sql

# Restore
psql shared_expenses < backup.sql
```

### Files
Use S3 or similar for receipt uploads

## Troubleshooting

### Database Connection Error
- Check PostgreSQL is running
- Verify DATABASE_URL is correct
- Check network connectivity

### Import Report Not Working
- Check file size limits
- Verify CSV format
- Check disk space

### Balance Calculation Off
- Verify all expenses are imported
- Check for deleted expenses
- Review import anomalies

---

For detailed setup instructions, see:
- `backend/SETUP.md`
- `frontend/SETUP.md`
- `README.md`
