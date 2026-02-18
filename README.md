# Transaction Analytics API

FastAPI-based transaction analytics service with PostgreSQL backend for comprehensive financial data analysis and reporting.

## Features

- **Transaction Analytics**: Comprehensive reports with filtering, metrics, and trends
- **Country-based Reports**: Geographic analysis with CSV data integration
- **Advanced Analytics**: Daily/monthly trends, top transactions, success rates
- **Optimized Queries**: Database indexes and efficient aggregations
- **Full Testing**: 80%+ test coverage with unit and integration tests
- **Docker Support**: Complete containerization with PostgreSQL

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Clone and Setup
```bash
git clone <repository-url>
cd transaction-analytics_test
```

### 2. Start Services
```bash
docker-compose up -d
```

### 3. Wait for Services
```bash
# Wait for database to be ready (30 seconds)
sleep 30

# Check service status
docker-compose ps
```

### 4. Run Database Migrations
```bash
docker-compose exec api alembic upgrade head
```

### 5. Seed Database with Sample Data
```bash
docker-compose exec api python seed_data.py
```

### 6. Verify Installation
```bash
# Health check
curl http://localhost:8000/health

# API Documentation
open http://localhost:8000/docs
```

## Environment Configuration

The project uses environment variables for configuration. The main configuration is stored in:
- `env` file (mounted to `/app/.env` in container)
- Environment variables in `docker-compose.yml`

### Key Environment Variables
```bash
DATABASE_URL=postgresql://user:password@postgres:5432/transaction_analytics
APP_NAME=Transaction Analytics API
DEBUG=false
```

### Local Development
For local development, create `.env` file:
```bash
cp env .env
# Edit .env with your local settings
```

## API Endpoints

### Base URL: `http://localhost:8000`

### Health Check
- `GET /health` - Service health status

### Transaction Reports
- `GET /report/` - Comprehensive transaction analytics
  - Query parameters: `start_date`, `end_date`, `status`, `type`, `include_avg`, `include_min`, `include_max`, `include_daily_shift`, `include_monthly_comparison`, `include_top_transactions`
- `GET /report/summary` - Quick summary for last N days

### Country Reports
- `GET /report/by-country` - Analytics grouped by country
  - Query parameters: `start_date`, `end_date`, `status`, `type`, `sort_by`, `top_n`

## Testing

### Run All Tests
```bash
docker-compose exec api python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

### Run Specific Test Categories
```bash
# Model tests
docker-compose exec api python -m pytest tests/test_models.py -v

# API tests
docker-compose exec api python -m pytest tests/test_reports.py -v

# Country API tests
docker-compose exec api python -m pytest tests/test_country_reports.py -v
```

### Test Coverage Report
```bash
# Generate HTML coverage report
docker-compose exec api python -m pytest tests/ --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Database Management

### Connect to Database
```bash
# Using psql
docker-compose exec postgres psql -U user -d transaction_analytics

# Using pgAdmin (if enabled)
open http://localhost:5050
```

### Database Migrations
```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Rollback migration
docker-compose exec api alembic downgrade -1
```

### Data Seeding
```bash
# Seed with sample data (120 users, 12,000 transactions)
docker-compose exec api python seed_data.py

# Custom seeding (modify seed_data.py parameters)
docker-compose exec api python -c "
from seed_data import seed_database
seed_database()
"
```

## Development

### Local Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Run migrations
alembic upgrade head

# Seed database
python seed_data.py

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/transaction_analytics

# Application
DEBUG=false
APP_NAME="Transaction Analytics API"
APP_VERSION="1.0.0"
```

## API Usage Examples

### Basic Transaction Report
```bash
curl "http://localhost:8000/report/?start_date=2024-01-01&end_date=2024-01-31&include_avg=true&include_daily_shift=true"
```

### Country-based Report
```bash
curl "http://localhost:8000/report/by-country?sort_by=total&top_n=5"
```

### Quick Summary
```bash
curl "http://localhost:8000/report/summary?days=30"
```

## Project Structure

```
transaction-analytics_test/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── routers/
│   │   ├── reports.py      # Transaction reports API
│   │   └── country_reports.py  # Country reports API
│   └── utils/
│       ├── analytics.py     # Advanced analytics utilities
│       └── data_loader.py  # CSV data loading
├── tests/                  # Test suite
├── migrations/              # Alembic migrations
├── data/                   # Data files (CSV, etc.)
├── docker-compose.yml        # Docker configuration
├── Dockerfile              # Docker image
├── requirements.txt         # Python dependencies
├── seed_data.py           # Database seeding script
└── alembic.ini           # Alembic configuration
```

## Performance

### Database Optimizations
- **Indexes**: Optimized indexes on user_id, status, type, transaction_date
- **Query Optimization**: Single-query aggregations where possible
- **Connection Pooling**: Efficient database connection management

### API Performance
- **Async Support**: FastAPI async endpoints
- **Response Caching**: Efficient data serialization
- **Pagination**: Large dataset handling

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database status
docker-compose logs postgres

# Restart services
docker-compose down && docker-compose up -d
```

#### Migration Issues
```bash
# Check current migration status
docker-compose exec api alembic current

# Force migration
docker-compose exec api alembic upgrade head
```

#### API Not Responding
```bash
# Check API logs
docker-compose logs api

# Check service status
docker-compose ps
```

### Health Checks
```bash
# Service health
curl http://localhost:8000/health

# Database connectivity
docker-compose exec api python -c "
from app.database import engine
try:
    with engine.connect() as conn:
        print('Database connection: OK')
except Exception as e:
    print(f'Database connection: FAILED - {e}')
"
```

## Production Deployment

### Environment Setup
1. Set production environment variables
2. Use production database credentials
3. Enable SSL/TLS
4. Configure backup strategy

### Security Considerations
- Change default passwords
- Use environment variables for secrets
- Enable database SSL
- Configure firewall rules
- Regular security updates

## Monitoring

### Application Monitoring
```bash
# Real-time logs
docker-compose logs -f api

# Resource usage
docker stats
```

### Database Monitoring
```bash
# Database connections
docker-compose exec postgres psql -U user -d transaction_analytics -c "
SELECT count(*) FROM pg_stat_activity;
"

# Database size
docker-compose exec postgres psql -U user -d transaction_analytics -c "
SELECT pg_size_pretty(pg_database_size('transaction_analytics'));
"
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Ensure test coverage ≥70%
5. Submit pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Check API documentation: http://localhost:8000/docs
- Review logs: `docker-compose logs`
- Run health checks: `curl http://localhost:8000/health`
