# Environment Variables Reference

This document lists all environment variables used in the HauntBro application.

## Required Variables

These variables **must** be set for the application to function properly:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://user:pass@localhost/dbname` |
| `JWT_SECRET_KEY` | Secret key for JWT token signing | `your-super-secure-secret-key-min-32-chars` |
| `REDDIT_CLIENT_ID` | Reddit API client ID | `your_reddit_client_id` |
| `REDDIT_CLIENT_SECRET` | Reddit API client secret | `your_reddit_client_secret` |

## Authentication & Security

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | *required* | JWT signing secret (min 32 chars) |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration time |
| `SESSION_SECRET_KEY` | *none* | Session encryption key |
| `BCRYPT_ROUNDS` | `12` | Password hashing rounds |
| `TEST_USER_PASSWORD` | `password123` | Default test user password |

## Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *required* | PostgreSQL connection string |
| `DATABASE_DEBUG` | `false` | Enable SQL query logging |
| `DATABASE_POOL_SIZE` | `5` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Max overflow connections |

## Reddit API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDDIT_CLIENT_ID` | *required* | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | *required* | Reddit app client secret |
| `REDDIT_USER_AGENT` | `HauntBro:1.0.0` | Reddit API user agent |
| `REDDIT_RATE_LIMIT_DELAY` | `0.1` | Delay between requests (seconds) |
| `REDDIT_BATCH_DELAY` | `2` | Delay between batches (seconds) |
| `REDDIT_MAX_RETRIES` | `3` | Max retry attempts |

## Content Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_CONTENT_LENGTH` | `200` | Minimum story length (chars) |
| `MAX_CONTENT_LENGTH` | `50000` | Maximum story length (chars) |
| `CHUNK_SIZE` | `1000` | Story chunk size for RAG |

## Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Application environment |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `API_DEBUG` | `true` | Enable debug mode |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8080` | Allowed CORS origins |
| `API_RATE_LIMIT` | `100` | API rate limit (requests/min) |

## Logging Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE_PATH` | `logs/hauntbro.log` | Log file location |
| `LOG_MAX_FILE_SIZE` | `10485760` | Max log file size (bytes) |
| `LOG_BACKUP_COUNT` | `5` | Number of backup log files |

## Cloud & Monitoring (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | *none* | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | *none* | AWS secret key |
| `AWS_REGION` | `us-east-1` | AWS region |
| `S3_BUCKET_NAME` | *none* | S3 bucket for storage |
| `REDIS_URL` | *none* | Redis connection URL |
| `SENTRY_DSN` | *none* | Sentry error tracking DSN |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | *none* | Azure App Insights key |

## Setup Instructions

1. **Copy template:**
   ```bash
   cp .env.example .env
   ```

2. **Set required variables:**
   - Get Reddit credentials from https://www.reddit.com/prefs/apps
   - Generate secure JWT secret (min 32 characters)
   - Configure database connection

3. **Customize optional variables:**
   - Adjust rate limits and timeouts
   - Configure logging preferences
   - Set up cloud credentials if needed

## Security Best Practices

- ✅ Never commit `.env` files to version control
- ✅ Use strong, unique secret keys (32+ characters)
- ✅ Rotate secrets regularly in production
- ✅ Use environment-specific configurations
- ✅ Encrypt secrets in cloud environments
- ✅ Limit database connection pool sizes appropriately
- ✅ Use secure random generators for secrets

## Environment-Specific Examples

### Development (.env)
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg2://dev:dev@localhost/hauntbro_dev
JWT_SECRET_KEY=dev-secret-key-32-chars-minimum-12345
API_DEBUG=true
LOG_LEVEL=DEBUG
```

### Production (Environment Variables)
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@prod-db:5432/hauntbro?sslmode=require
JWT_SECRET_KEY=prod-secure-random-key-min-32-chars
API_DEBUG=false
LOG_LEVEL=INFO
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
```

## Validation

Run this command to verify your environment setup:
```bash
python data-pipeline/scripts/test_reddit_setup.py
```