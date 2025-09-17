# Kafka-PostgreSQL-Spark Streaming Pipeline

A complete data streaming pipeline that captures database changes using Debezium CDC, processes them with Kafka, and consumes them with Spark Streaming.

## Architecture

```
PostgreSQL → Debezium → Kafka → Spark Streaming
     ↓
  pgAdmin (UI)
```

## Components

- **PostgreSQL**: Source database with sample data (users, orders, products)
- **Debezium**: Change Data Capture (CDC) connector for PostgreSQL
- **Kafka**: Message streaming platform
- **Spark Streaming**: Real-time data processing
- **pgAdmin**: Database management interface
- **Kafka UI**: Kafka cluster monitoring

## Quick Start

### 1. Start the Infrastructure

```bash
# Make setup script executable
chmod +x scripts/setup.sh

# Run the setup script
./scripts/setup.sh
```

### 2. Access Web Interfaces

- **pgAdmin**: http://localhost:8080
  - Email: `admin@admin.com`
  - Password: `admin`
  - Server: `postgres` (host), port `5432`, user `postgres`, password `postgres`

- **Kafka UI**: http://localhost:8081
- **Kafka Connect**: http://localhost:8083

### 3. Start Spark Streaming Consumer

```bash
cd spark-streaming
pip install -r requirements.txt
python kafka_spark_consumer.py
```

### 4. Generate Test Data

```bash
cd scripts
python test-data-generator.py
```

## Database Schema

### Users Table
- `id` (Primary Key)
- `name`
- `email`
- `age`
- `created_at`
- `updated_at`

### Orders Table
- `id` (Primary Key)
- `user_id` (Foreign Key)
- `product_name`
- `quantity`
- `price`
- `order_date`
- `status`

### Products Table
- `id` (Primary Key)
- `name`
- `category`
- `price`
- `stock_quantity`
- `created_at`

## Kafka Topics

The Debezium connector creates the following topics:
- `postgres-server.public.users`
- `postgres-server.public.orders`
- `postgres-server.public.products`

## Spark Streaming Features

- Real-time processing of CDC events
- Data transformation and filtering
- Aggregations (user order statistics)
- Console output for monitoring
- Error handling and logging

## Manual Operations

### Check Connector Status
```bash
curl http://localhost:8083/connectors/postgres-connector/status
```

### List Kafka Topics
```bash
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### View Kafka Messages
```bash
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic postgres-server.public.users \
  --from-beginning
```

### Connect to PostgreSQL
```bash
docker exec -it postgres-db psql -U postgres -d streaming_db
```

## Troubleshooting

### Services Not Starting
- Check Docker daemon is running
- Ensure ports 5432, 8080, 8081, 8083, 9092 are available
- Check logs: `docker-compose logs [service-name]`

### Debezium Connector Issues
- Verify PostgreSQL has logical replication enabled
- Check connector configuration in `debezium-connector.json`
- View connector logs: `docker-compose logs kafka-connect`

### Spark Streaming Issues
- Ensure Kafka is accessible on localhost:9092
- Check Java version compatibility
- Verify all required packages are installed

## Stopping the Pipeline

```bash
# Stop all services
docker-compose down

# Remove volumes (data will be lost)
docker-compose down -v
```

## Next Steps

1. Implement custom Spark transformations
2. Add data validation and quality checks
3. Integrate with external systems (Elasticsearch, S3, etc.)
4. Add monitoring and alerting
5. Implement schema evolution handling
