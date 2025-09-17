# Complete Kafka-PostgreSQL-Spark Streaming Pipeline Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Components](#architecture--components)
3. [Installation & Setup](#installation--setup)
4. [Database Schema & CDC](#database-schema--cdc)
5. [Debezium Configuration](#debezium-configuration)
6. [Kafka Topics & Offsets](#kafka-topics--offsets)
7. [Spark Streaming Processing](#spark-streaming-processing)
8. [Data Flow & Event Processing](#data-flow--event-processing)
9. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
10. [Code Walkthrough](#code-walkthrough)

---

## 1. Project Overview

### What This Project Does
This is a **real-time data streaming pipeline** that demonstrates:
- **Change Data Capture (CDC)** from PostgreSQL database
- **Event streaming** through Apache Kafka
- **Real-time processing** with Apache Spark Streaming
- **Data enrichment** and **aggregation**
- **Multi-topic output** for different data consumers

### Business Use Case
**Employee Activity Tracking System**: Monitors employee website activities in real-time, processes the data, and creates insights for:
- Security monitoring
- Productivity analytics
- User behavior analysis
- Real-time dashboards

### Technology Stack
- **PostgreSQL 15**: Source database with logical replication
- **Apache Kafka**: Message streaming platform
- **Debezium**: Change Data Capture connector
- **Apache Spark**: Stream processing engine
- **Docker**: Containerization platform
- **pgAdmin**: Database management interface
- **Kafka UI**: Kafka cluster monitoring

---

## 2. Architecture & Components

### High-Level Architecture
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ PostgreSQL  │───▶│  Debezium   │───▶│    Kafka    │───▶│    Spark    │
│  Database   │    │ Connector   │    │   Topics    │    │  Streaming  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                                       │                   │
       ▼                                       ▼                   ▼
┌─────────────┐                    ┌─────────────┐    ┌─────────────┐
│   pgAdmin   │                    │  Kafka UI   │    │ Output      │
│ (Monitoring)│                    │(Monitoring) │    │ Topics      │
└─────────────┘                    └─────────────┘    └─────────────┘
```

### Component Details

#### PostgreSQL Database
- **Purpose**: Source of truth for employee data
- **Configuration**: Logical replication enabled (`wal_level=logical`)
- **Tables**: `employees`, `employee_activities`
- **Port**: 5432

#### Debezium Connector
- **Purpose**: Captures database changes in real-time
- **Type**: PostgreSQL CDC connector
- **Method**: Uses PostgreSQL's logical replication slots
- **Output**: JSON messages to Kafka topics

#### Apache Kafka
- **Purpose**: Message streaming and buffering
- **Broker**: Single broker setup for learning
- **Zookeeper**: Coordination service
- **Port**: 9092

#### Spark Streaming
- **Purpose**: Real-time data processing and transformation
- **Engine**: Structured Streaming API
- **Processing**: Micro-batch processing (10-15 second intervals)
- **Output**: Processed data to new Kafka topics

---

## 3. Installation & Setup

### Prerequisites Installed
1. **Docker Desktop**: Containerization platform
2. **Python 3.9+**: For Spark applications
3. **Java 11+**: Required by Spark (if running locally)

### Docker Services Started
```yaml
# docker-compose.yml services:
services:
  postgres:      # PostgreSQL database
  pgadmin:       # Database management UI
  zookeeper:     # Kafka coordination
  kafka:         # Message broker
  kafka-connect: # Debezium connector runtime
  kafka-ui:      # Kafka monitoring UI
```

### Service Ports
- **PostgreSQL**: localhost:5432
- **pgAdmin**: localhost:8080
- **Kafka**: localhost:9092
- **Kafka Connect**: localhost:8083
- **Kafka UI**: localhost:8081

### Installation Commands Used
```bash
# 1. Start Docker services
docker compose up -d

# 2. Initialize database
docker exec -i postgres-db psql -U postgres < init-scripts/01-init-db.sql
docker exec -i postgres-db psql -U postgres < init-scripts/02-employee-activity.sql

# 3. Create Debezium connectors
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @debezium-connector.json

curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @debezium-employee-connector.json

# 4. Install Python dependencies
pip3 install pyspark==3.5.0 kafka-python==2.0.2 psycopg2-binary==2.9.7
```

---

## 4. Database Schema & CDC

### Employee Tables Schema

#### employees table
```sql
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,              -- Auto-incrementing ID
    name VARCHAR(100) NOT NULL,         -- Employee name
    email VARCHAR(100) UNIQUE NOT NULL, -- Unique email
    department VARCHAR(50) NOT NULL,    -- Department (Engineering, Marketing, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### employee_activities table
```sql
CREATE TABLE employee_activities (
    id SERIAL PRIMARY KEY,              -- Activity ID
    employee_id INTEGER REFERENCES employees(id), -- Foreign key
    activity_type VARCHAR(50) NOT NULL, -- login, logout, page_view, click, download
    page_url VARCHAR(200),              -- URL visited
    duration_seconds INTEGER,           -- Time spent
    ip_address INET,                    -- User's IP address
    user_agent TEXT,                    -- Browser information
    activity_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Change Data Capture (CDC) Concepts

#### What is CDC?
**Change Data Capture** is a method to identify and capture changes made to data in a database, then deliver those changes in real-time to downstream systems.

#### How PostgreSQL CDC Works
1. **Write-Ahead Log (WAL)**: PostgreSQL logs all changes to WAL files
2. **Logical Replication**: Converts WAL entries to logical changes
3. **Replication Slot**: Named cursor that tracks consumed changes
4. **Publication**: Defines which tables to replicate

#### CDC Configuration
```sql
-- Enable logical replication (already configured in docker-compose.yml)
-- wal_level = logical
-- max_replication_slots = 4
-- max_wal_senders = 4

-- Set replica identity (enables full row tracking)
ALTER TABLE employees REPLICA IDENTITY DEFAULT;
ALTER TABLE employee_activities REPLICA IDENTITY DEFAULT;
```

---

## 5. Debezium Configuration

### Connector Configuration Explained

#### debezium-employee-connector.json
```json
{
  "name": "employee-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    
    // Database connection details
    "database.hostname": "postgres",     // Container name
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "streaming_db",
    
    // Server identification
    "database.server.name": "employee-server", // Logical server name
    
    // Table selection
    "table.include.list": "public.employees,public.employee_activities",
    
    // PostgreSQL specific settings
    "plugin.name": "pgoutput",           // Logical decoding plugin
    "slot.name": "employee_slot",        // Replication slot name
    "publication.name": "employee_publication", // Publication name
    
    // Kafka topic configuration
    "topic.prefix": "employee-server",   // Topic prefix
    
    // Schema registry (using Kafka for schema storage)
    "schema.history.internal.kafka.bootstrap.servers": "kafka:29092",
    "schema.history.internal.kafka.topic": "employee-schema-changes"
  }
}
```

### How Debezium Works

#### 1. Initial Snapshot
- Reads existing data from tables
- Creates baseline in Kafka topics
- Establishes replication slot

#### 2. Change Streaming
- Monitors PostgreSQL WAL
- Converts changes to JSON events
- Publishes to Kafka topics

#### 3. Event Structure
```json
{
  "payload": {
    "before": null,           // Previous row state (for updates/deletes)
    "after": {               // New row state
      "id": 1,
      "employee_id": 1,
      "activity_type": "login",
      "page_url": "/dashboard",
      "duration_seconds": 0,
      "ip_address": "192.168.1.100",
      "activity_timestamp": "2025-01-02T10:30:00Z"
    },
    "op": "c",               // Operation: c=create, u=update, d=delete
    "ts_ms": 1704193800000   // Timestamp in milliseconds
  }
}
```

---

## 6. Kafka Topics & Offsets

### Topics Created by Debezium

#### Source Topics (Created by Debezium)
1. **employee-server.public.employees**
   - Contains employee table changes
   - Partition: 1 (default)
   - Retention: 7 days (default)

2. **employee-server.public.employee_activities**
   - Contains activity table changes
   - Partition: 1 (default)
   - Key: Employee ID (for partitioning)

#### Processing Topics (Created by Spark)
3. **processed-employee-activities**
   - Enriched activity data
   - Added fields: activity_hour, session_category, business_hours

4. **employee-activity-summaries**
   - Aggregated data per employee per hour
   - Contains: activity_count, total_duration, avg_duration

### Kafka Offset Management

#### What are Offsets?
**Offsets** are unique identifiers for messages within a Kafka partition. They represent the position of a consumer in the message stream.

#### Offset Types
1. **Current Offset**: Last message read by consumer
2. **Committed Offset**: Last message successfully processed
3. **High Water Mark**: Latest message in partition

#### Offset Storage
- **Location**: `__consumer_offsets` topic
- **Format**: Binary format with consumer group metadata
- **Retention**: Configurable (default 7 days)

#### Consumer Groups
```bash
# Spark Streaming creates consumer groups automatically
# Group ID format: spark-kafka-source-[random-uuid]
```

### Monitoring Offsets
```bash
# View consumer groups
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Check consumer lag
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group [group-id] --describe
```

---

## 7. Spark Streaming Processing

### Spark Application Architecture

#### EmployeeActivityProcessor Class Structure
```python
class EmployeeActivityProcessor:
    def __init__(self):
        self.spark = None
        self.initialize_spark()
    
    # Core methods:
    # - initialize_spark()          # Setup Spark session
    # - define_schemas()            # Define data schemas
    # - process_employee_activities() # Main processing logic
    # - create_activity_summary()   # Aggregation logic
    # - write_to_kafka_topic()      # Output to Kafka
    # - start_processing()          # Main execution
```

### Processing Logic Explained

#### 1. Spark Session Configuration
```python
self.spark = SparkSession.builder \
    .appName("EmployeeActivityProcessor") \
    .config("spark.jars.packages", 
           "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()
```

**Explanation**:
- `spark-sql-kafka-0-10`: Kafka connector for Spark
- `adaptive.enabled`: Optimizes query execution
- `appName`: Identifies application in Spark UI

#### 2. Reading from Kafka
```python
kafka_df = self.spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "employee-server.public.employee_activities") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()
```

**Explanation**:
- `readStream`: Creates streaming DataFrame
- `subscribe`: Topic to read from
- `startingOffsets`: Start from latest messages (not historical)
- `failOnDataLoss`: Continue processing even if messages are lost

#### 3. Message Parsing
```python
parsed_df = df.select(
    from_json(col("value").cast("string"), debezium_schema).alias("parsed_value")
)
```

**Explanation**:
- Kafka messages are binary, cast to string
- `from_json`: Parses JSON using defined schema
- Extracts Debezium payload structure

#### 4. Data Enrichment
```python
enriched_df = activity_df.withColumn(
    "activity_hour", hour(col("activity_timestamp"))
).withColumn(
    "session_duration_category", 
    when(col("duration_seconds") < 30, "short")
    .when(col("duration_seconds") < 300, "medium")
    .otherwise("long")
).withColumn(
    "is_business_hours",
    when((hour(col("activity_timestamp")) >= 9) & 
         (hour(col("activity_timestamp")) <= 17), True)
    .otherwise(False)
)
```

**Explanation**:
- `withColumn`: Adds new columns to DataFrame
- `hour()`: Extracts hour from timestamp
- `when().otherwise()`: Conditional logic (like CASE WHEN in SQL)

#### 5. Windowed Aggregations
```python
summary_df = activity_df \
    .groupBy(
        window(col("activity_timestamp"), "1 hour"),
        col("employee_id"),
        col("activity_type")
    ) \
    .agg(
        count("*").alias("activity_count"),
        sum("duration_seconds").alias("total_duration"),
        avg("duration_seconds").alias("avg_duration")
    )
```

**Explanation**:
- `window()`: Creates 1-hour time windows
- `groupBy()`: Groups data by window, employee, and activity type
- `agg()`: Performs aggregations within each group

#### 6. Output to Kafka
```python
kafka_df = df.select(
    col("employee_id").cast("string").alias("key"),
    to_json(struct(*df.columns)).alias("value")
)

query = kafka_df.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("topic", "processed-employee-activities") \
    .option("checkpointLocation", "/tmp/checkpoint-processed") \
    .outputMode("append") \
    .trigger(processingTime='10 seconds') \
    .start()
```

**Explanation**:
- `to_json(struct())`: Converts DataFrame row to JSON
- `checkpointLocation`: Stores processing state for fault tolerance
- `outputMode`: How to handle updates (append/update/complete)
- `trigger`: Processing interval (micro-batch every 10 seconds)

---

## 8. Data Flow & Event Processing

### Complete Data Flow

#### Step 1: Database Change Occurs
```sql
-- User inserts new activity
INSERT INTO employee_activities (employee_id, activity_type, page_url, duration_seconds) 
VALUES (1, 'page_view', '/dashboard', 45);
```

#### Step 2: PostgreSQL WAL Entry
- PostgreSQL writes change to Write-Ahead Log
- WAL entry contains transaction details

#### Step 3: Debezium Captures Change
- Debezium reads WAL through replication slot
- Converts WAL entry to JSON event
- Publishes to Kafka topic: `employee-server.public.employee_activities`

#### Step 4: Kafka Stores Event
```json
{
  "key": "1",
  "value": {
    "payload": {
      "after": {
        "id": 15,
        "employee_id": 1,
        "activity_type": "page_view",
        "page_url": "/dashboard",
        "duration_seconds": 45,
        "activity_timestamp": "2025-01-02T10:30:00Z"
      },
      "op": "c",
      "ts_ms": 1704193800000
    }
  },
  "partition": 0,
  "offset": 42
}
```

#### Step 5: Spark Consumes Event
- Spark reads from Kafka topic
- Parses JSON payload
- Applies transformations

#### Step 6: Data Enrichment
```python
# Original data
{
  "employee_id": 1,
  "activity_type": "page_view",
  "duration_seconds": 45,
  "activity_timestamp": "2025-01-02T10:30:00Z"
}

# After enrichment
{
  "employee_id": 1,
  "activity_type": "page_view",
  "duration_seconds": 45,
  "activity_timestamp": "2025-01-02T10:30:00Z",
  "activity_hour": 10,
  "activity_date": "2025-01-02",
  "session_duration_category": "medium",
  "is_business_hours": true
}
```

#### Step 7: Output to New Topics
- **processed-employee-activities**: Individual enriched events
- **employee-activity-summaries**: Hourly aggregations

### Event Processing Guarantees

#### Exactly-Once Processing
- **Kafka**: At-least-once delivery guarantee
- **Spark**: Exactly-once processing with checkpointing
- **Debezium**: At-least-once capture guarantee

#### Fault Tolerance
- **Kafka**: Replication across brokers (single broker in our setup)
- **Spark**: Checkpointing for state recovery
- **PostgreSQL**: WAL-based durability

---

## 9. Monitoring & Troubleshooting

### Monitoring Interfaces

#### pgAdmin (Database Monitoring)
- **URL**: http://localhost:8080
- **Login**: admin@admin.com / admin
- **Purpose**: Monitor database changes, run queries
- **Key Queries**:
```sql
-- Check recent activities
SELECT * FROM employee_activities ORDER BY activity_timestamp DESC LIMIT 10;

-- Monitor activity counts
SELECT COUNT(*) FROM employee_activities;
```

#### Kafka UI (Stream Monitoring)
- **URL**: http://localhost:8081
- **Purpose**: Monitor topics, partitions, consumer lag
- **Key Metrics**:
  - Message count per topic
  - Consumer group lag
  - Partition distribution

#### Spark Console Output
- **Purpose**: Real-time processing logs
- **Information**: Batch processing times, record counts, errors

### Troubleshooting Common Issues

#### 1. Debezium Connector Not Running
```bash
# Check connector status
curl http://localhost:8083/connectors/employee-connector/status

# Restart connector
curl -X POST http://localhost:8083/connectors/employee-connector/restart
```

#### 2. Kafka Consumer Lag
```bash
# Check consumer groups
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Check lag
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group [group-id] --describe
```

#### 3. Spark Processing Errors
- Check Spark logs for Java/Python errors
- Verify Kafka connectivity
- Check schema compatibility

#### 4. Database Connection Issues
```bash
# Test PostgreSQL connection
docker exec postgres-db psql -U postgres -d streaming_db -c "SELECT 1;"

# Check replication slots
docker exec postgres-db psql -U postgres -d streaming_db \
  -c "SELECT * FROM pg_replication_slots;"
```

---

## 10. Code Walkthrough

### File Structure
```
kafka_cassendra/
├── docker-compose.yml                    # Container orchestration
├── init-scripts/
│   ├── 01-init-db.sql                   # Initial database setup
│   └── 02-employee-activity.sql         # Employee tables
├── spark-streaming/
│   ├── requirements.txt                 # Python dependencies
│   ├── kafka_spark_consumer.py          # Original consumer
│   └── employee_activity_processor.py   # Employee-specific processor
├── scripts/
│   ├── setup.sh                        # Docker setup script
│   ├── setup-local.sh                  # Local setup script
│   ├── test-data-generator.py          # General data generator
│   └── employee-activity-generator.py  # Employee activity generator
├── debezium-connector.json             # Original connector config
├── debezium-employee-connector.json    # Employee connector config
└── [documentation files]
```

### Key Configuration Files

#### docker-compose.yml
- **Purpose**: Defines all services and their configurations
- **Services**: PostgreSQL, Kafka, Zookeeper, Debezium, pgAdmin, Kafka UI
- **Networks**: Creates isolated Docker network
- **Volumes**: Persists PostgreSQL data

#### Debezium Connector Configuration
- **Purpose**: Configures CDC from PostgreSQL to Kafka
- **Key Settings**: Database connection, table selection, topic naming
- **Replication**: Uses PostgreSQL logical replication

#### Spark Application
- **Purpose**: Processes streaming data from Kafka
- **Architecture**: Structured Streaming with micro-batches
- **Output**: Multiple Kafka topics with processed data

### Data Generation Scripts

#### employee-activity-generator.py
```python
# Simulates realistic employee activities:
# - Login sessions with multiple activities
# - Department-specific page visits
# - Realistic duration patterns
# - IP address simulation
```

### Processing Logic Flow
1. **Data Ingestion**: Kafka → Spark DataFrame
2. **Schema Application**: JSON parsing with predefined schemas
3. **Filtering**: Only process INSERT operations (`op = "c"`)
4. **Enrichment**: Add calculated fields
5. **Aggregation**: Time-windowed summaries
6. **Output**: Write to multiple Kafka topics

---

## Summary

This project demonstrates a complete **real-time data streaming pipeline** with:

### Technical Learning Outcomes
- **Change Data Capture (CDC)** implementation
- **Apache Kafka** message streaming
- **Apache Spark Structured Streaming** processing
- **Docker containerization** and orchestration
- **Real-time data enrichment** and aggregation

### Business Value
- **Real-time monitoring** of employee activities
- **Scalable architecture** for high-volume data
- **Flexible processing** with multiple output streams
- **Fault-tolerant design** with checkpointing and offsets

### Next Steps for Enhancement
1. **Add more complex aggregations** (daily/weekly summaries)
2. **Implement alerting** for unusual activity patterns
3. **Add data validation** and quality checks
4. **Scale to multiple Kafka partitions** for higher throughput
5. **Integrate with external systems** (Elasticsearch, S3, etc.)

This pipeline provides a solid foundation for understanding modern data streaming architectures and can be extended for various real-world use cases.
