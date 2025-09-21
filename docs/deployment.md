# Deployment Guide

## Prerequisites

- Docker 20.10.0+
- Docker Compose 1.29.0+
- Kubernetes cluster (for production)
- Cloud provider account (AWS/GCP/Azure)

## Environment Variables

Create a `.env` file based on `.env.example` with your production configuration:

```bash
# Application
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=your-secret-key-here

# Database
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=insurance
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password

# API
API_KEY=your-api-key
API_RATE_LIMIT=100/minute
```

## Docker Deployment

1. **Build the Docker image**
   ```bash
   docker-compose build
   ```

2. **Start the services**
   ```bash
   docker-compose up -d
   ```

3. **Verify the deployment**
   ```bash
   docker-compose ps
   curl http://localhost:8000/health
   ```

## Kubernetes Deployment

1. **Create a namespace**
   ```bash
   kubectl create namespace insurance
   ```

2. **Create a secret for environment variables**
   ```bash
   kubectl create secret generic insurance-secrets --from-env-file=.env -n insurance
   ```

3. **Deploy the application**
   ```bash
   kubectl apply -f k8s/deployment.yaml -n insurance
   kubectl apply -f k8s/service.yaml -n insurance
   kubectl apply -f k8s/ingress.yaml -n insurance
   ```

## Database Migrations

```bash
# Run migrations
python manage.py migrate

# Create a new migration
python manage.py makemigrations
```

## Monitoring and Logging

### Prometheus and Grafana

```bash
# Deploy monitoring stack
kubectl apply -f monitoring/prometheus.yaml
kubectl apply -f monitoring/grafana.yaml
```

### Logging with ELK Stack

```bash
# Deploy ELK stack
kubectl apply -f logging/elasticsearch.yaml
kubectl apply -f logging/kibana.yaml
kubectl apply -f logging/filebeat.yaml
```

## Backup and Recovery

### Database Backup

```bash
# Create a backup
pg_dump -h localhost -U postgres insurance > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -h localhost -U postgres insurance < backup_20230921.sql
```

### Volume Snapshots

```bash
# Create a snapshot
gcloud compute disks snapshot [DISK_NAME] --zone [ZONE] --snapshot-names [SNAPSHOT_NAME]

# Restore from snapshot
gcloud compute disks create [DISK_NAME] --source-snapshot [SNAPSHOT_NAME] --zone [ZONE]
```

## Scaling

### Horizontal Pod Autoscaling

```bash
# Enable HPA
kubectl autoscale deployment insurance-app --cpu-percent=80 --min=2 --max=10 -n insurance
```

### Database Read Replicas

Update the deployment configuration to include read replicas:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-read-replica
  labels:
    app: postgres
    role: replica
spec:
  replicas: 2
  selector:
    matchLabels:
      app: postgres
      role: replica
  template:
    metadata:
      labels:
        app: postgres
        role: replica
    spec:
      containers:
      - name: postgres
        image: postgres:13
        ports:
        - containerPort: 5432
        envFrom:
        - secretRef:
            name: postgres-secrets
```

## Maintenance

### Zero-Downtime Deployments

```bash
# Perform a rolling update
kubectl set image deployment/insurance-app insurance-app=your-image:new-version -n insurance

# Monitor the rollout
kubectl rollout status deployment/insurance-app -n insurance

# Rollback if needed
kubectl rollout undo deployment/insurance-app -n insurance
```

### Database Maintenance

```bash
# Run vacuum
psql -h localhost -U postgres -c "VACUUM ANALYZE;" insurance

# Reindex database
psql -h localhost -U postgres -c "REINDEX DATABASE insurance;"
```

## Security

- Enable TLS for all external communications
- Regularly rotate API keys and database credentials
- Keep all dependencies updated
- Run security scans using tools like Trivy or Snyk
- Implement network policies to restrict pod-to-pod communication
