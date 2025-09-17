# Apache Kafka & Real-Time Streaming Pipeline
## Complete Learning Manual

---

**Table of Contents**

1. [Apache Kafka Fundamentals](#kafka-fundamentals)
2. [Project Architecture](#project-architecture)  
3. [Installation & Setup](#installation-setup)
4. [Implementation Details](#implementation-details)
5. [Code Walkthrough](#code-walkthrough)
6. [Monitoring & Troubleshooting](#monitoring-troubleshooting)

---

## 1. Apache Kafka Fundamentals

### What is Apache Kafka?

Apache Kafka is a **distributed event streaming platform** designed to handle high-throughput, real-time data feeds. Think of it as a **message highway** where applications can:
- **Publish** messages (producers)
- **Subscribe** to messages (consumers)
- **Store** messages reliably
- **Process** messages in real-time

### Core Concepts

#### 1.1 Topics
A **topic** is like a **folder** or **category** where messages are stored.
- Example: `employee-activities`, `user-clicks`, `order-events`
- Topics are **append-only logs**
- Messages are **immutable** once written

#### 1.2 Partitions
Each topic is divided into **partitions** for scalability.
```
Topic: employee-activities
├── Partition 0: [msg1, msg2, msg3, ...]
├── Partition 1: [msg4, msg5, msg6, ...]
└── Partition 2: [msg7, msg8, msg9, ...]
```

**Why Partitions?**
- **Parallelism**: Multiple consumers can read simultaneously
- **Scalability**: Distribute load across multiple servers
- **Ordering**: Messages within a partition are ordered

#### 1.3 Producers
**Producers** are applications that **send messages** to Kafka topics.
- In our project: **Debezium** is the producer
- Sends database changes to Kafka topics
- Can specify which partition to send to

#### 1.4 Consumers
**Consumers** are applications that **read messages** from Kafka topics.
- In our project: **Spark Streaming** is the consumer
- Can read from multiple partitions
- Track their position using **offsets**

#### 1.5 Offsets
**Offsets** are like **bookmarks** that track message position.
```
Partition 0: [msg1, msg2, msg3, msg4, msg5]
Offsets:      0     1     2     3     4
                              ↑
                    Consumer position (offset 3)
```

#### 1.6 Consumer Groups
**Consumer groups** enable **load balancing** and **fault tolerance**.
- Multiple consumers in same group share the workload
- Each partition is consumed by only one consumer in the group
- If a consumer fails, others take over its partitions

### Kafka Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Producer   │───▶│    Kafka    │◀───│  Consumer   │
│ (Debezium)  │    │   Cluster   │    │   (Spark)   │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                   ┌─────────────┐
                   │  Zookeeper  │
                   │(Coordination)│
                   └─────────────┘
```

#### Kafka Broker
- **Server** that stores and serves messages
- Our setup: Single broker (learning environment)
- Production: Multiple brokers for high availability

#### Zookeeper
- **Coordination service** for Kafka cluster
- Manages broker metadata
- Handles leader election for partitions

---

## 2. Project Architecture

### What We Built

A **real-time employee activity tracking system** with this flow:

```
PostgreSQL Database
        │ (Database changes)
        ▼
   Debezium CDC
        │ (Capture changes)
        ▼
    Kafka Topics
        │ (Stream messages)
        ▼
  Spark Streaming
        │ (Process & enrich)
        ▼
  Output Kafka Topics
```

### Components Explained

#### 2.1 PostgreSQL Database
- **Role**: Source of truth for employee data
- **Tables**: `employees`, `employee_activities`
- **Special Config**: Logical replication enabled for CDC

#### 2.2 Debezium CDC Connector
- **Role**: Captures database changes in real-time
- **Method**: Reads PostgreSQL Write-Ahead Log (WAL)
- **Output**: JSON messages to Kafka topics

#### 2.3 Kafka Cluster
- **Role**: Message streaming and buffering
- **Topics Created**:
  - `employee-server.public.employees`
  - `employee-server.public.employee_activities`
  - `processed-employee-activities` (output)
  - `employee-activity-summaries` (output)

#### 2.4 Spark Streaming
- **Role**: Real-time data processing
- **Processing**: Enrichment, aggregation, filtering
- **Output**: Processed data to new Kafka topics

---

## 3. Installation & Setup

### 3.1 Docker Environment

We used **Docker Compose** to orchestrate multiple services:

```yaml
services:
  postgres:      # Database
  pgadmin:       # Database UI
  zookeeper:     # Kafka coordination
  kafka:         # Message broker
  kafka-connect: # Debezium runtime
  kafka-ui:      # Kafka monitoring
```

### 3.2 Installation Steps Performed

#### Step 1: Start Docker Services
```bash
docker compose up -d
```
**What this does**:
- Downloads required Docker images
- Creates isolated network for services
- Starts all containers with proper dependencies

#### Step 2: Initialize Database
```bash
docker exec -i postgres-db psql -U postgres < init-scripts/01-init-db.sql
docker exec -i postgres-db psql -U postgres < init-scripts/02-employee-activity.sql
```
**What this does**:
- Creates `streaming_db` database
- Creates tables with sample data
- Enables logical replication

#### Step 3: Configure Debezium
```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @debezium-employee-connector.json
```
**What this does**:
- Registers PostgreSQL connector with Kafka Connect
- Creates replication slot in PostgreSQL
- Starts capturing database changes

#### Step 4: Install Python Dependencies
```bash
pip3 install pyspark==3.5.0 kafka-python==2.0.2 psycopg2-binary==2.9.7
```
**What this does**:
- Installs Spark for stream processing
- Installs Kafka client libraries
- Installs PostgreSQL adapter

---

## 4. Implementation Details

### 4.1 Database Schema

#### Employees Table
```sql
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,              -- Unique identifier
    name VARCHAR(100) NOT NULL,         -- Employee name
    email VARCHAR(100) UNIQUE NOT NULL, -- Contact email
    department VARCHAR(50) NOT NULL,    -- Department (Engineering, Marketing, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Employee Activities Table
```sql
CREATE TABLE employee_activities (
    id SERIAL PRIMARY KEY,              -- Activity identifier
    employee_id INTEGER REFERENCES employees(id), -- Links to employee
    activity_type VARCHAR(50) NOT NULL, -- Type: login, page_view, click, etc.
    page_url VARCHAR(200),              -- URL visited
    duration_seconds INTEGER,           -- Time spent on activity
    ip_address INET,                    -- User's IP address
    user_agent TEXT,                    -- Browser information
    activity_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Change Data Capture (CDC)

#### What is CDC?
**Change Data Capture** identifies and captures changes in a database, then delivers those changes to other systems in real-time.

#### How PostgreSQL CDC Works
1. **Write-Ahead Log (WAL)**: PostgreSQL logs all changes
2. **Logical Replication**: Converts WAL to readable format
3. **Replication Slot**: Tracks which changes have been consumed
4. **Publication**: Defines which tables to monitor

#### Debezium Configuration
```json
{
  "name": "employee-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "streaming_db",
    "database.server.name": "employee-server",
    "table.include.list": "public.employees,public.employee_activities",
    "plugin.name": "pgoutput",
    "slot.name": "employee_slot",
    "publication.name": "employee_publication",
    "topic.prefix": "employee-server"
  }
}
```

**Configuration Explained**:
- `connector.class`: Specifies PostgreSQL connector
- `database.*`: Connection details
- `table.include.list`: Which tables to monitor
- `topic.prefix`: Kafka topic naming convention
- `slot.name`: PostgreSQL replication slot name

### 4.3 Kafka Topics Structure

#### Source Topics (Created by Debezium)
1. **employee-server.public.employees**
   - Contains employee table changes
   - Key: Employee ID
   - Value: Complete employee record

2. **employee-server.public.employee_activities**
   - Contains activity table changes
   - Key: Activity ID
   - Value: Complete activity record

#### Message Format
```json
{
  "payload": {
    "before": null,           // Previous state (for updates/deletes)
    "after": {               // New state
      "id": 1,
      "employee_id": 1,
      "activity_type": "page_view",
      "page_url": "/dashboard",
      "duration_seconds": 45,
      "activity_timestamp": "2025-01-02T10:30:00Z"
    },
    "op": "c",               // Operation: c=create, u=update, d=delete
    "ts_ms": 1704193800000   // Timestamp
  }
}
```

---

## 5. Code Walkthrough

### 5.1 Spark Streaming Application

#### Application Structure
```python
class EmployeeActivityProcessor:
    def __init__(self):
        self.spark = None
        self.initialize_spark()
    
    def initialize_spark(self):        # Setup Spark session
    def define_schemas(self):          # Define data structures
    def process_employee_activities(self): # Main processing logic
    def create_activity_summary(self):  # Aggregation logic
    def write_to_kafka_topic(self):    # Output to Kafka
    def start_processing(self):        # Main execution
```

#### 5.2 Spark Session Configuration
```python
self.spark = SparkSession.builder \
    .appName("EmployeeActivityProcessor") \
    .config("spark.jars.packages", 
           "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()
```

**Configuration Explained**:
- `appName`: Identifies application in Spark UI
- `spark.jars.packages`: Downloads Kafka connector for Spark
- `adaptive.enabled`: Optimizes query execution automatically

#### 5.3 Reading from Kafka
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

**Options Explained**:
- `format("kafka")`: Use Kafka as data source
- `bootstrap.servers`: Kafka broker address
- `subscribe`: Topic to read from
- `startingOffsets`: Start from latest messages (not historical)
- `failOnDataLoss`: Continue processing even if messages are lost

#### 5.4 Data Processing Pipeline

##### Message Parsing
```python
parsed_df = df.select(
    from_json(col("value").cast("string"), debezium_schema).alias("parsed_value")
)
```
**Explanation**: Kafka messages are binary, convert to string and parse JSON

##### Data Enrichment
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

**Enrichment Logic**:
- Extract hour from timestamp
- Categorize session duration
- Identify business hours activities

##### Windowed Aggregations
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

**Aggregation Logic**:
- Group by 1-hour time windows
- Group by employee and activity type
- Calculate count, sum, and average duration

#### 5.5 Output to Kafka
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

**Output Configuration**:
- Convert DataFrame to key-value format
- Specify output Kafka topic
- Set checkpoint location for fault tolerance
- Use append mode for new records
- Process every 10 seconds

---

## 6. Monitoring & Troubleshooting

### 6.1 Monitoring Interfaces

#### pgAdmin (Database Monitoring)
- **URL**: http://localhost:8080
- **Purpose**: Monitor database changes, run queries
- **Login**: admin@admin.com / admin

**Key Monitoring Queries**:
```sql
-- Check recent activities
SELECT * FROM employee_activities 
ORDER BY activity_timestamp DESC LIMIT 10;

-- Activity count by employee
SELECT e.name, COUNT(ea.id) as activity_count
FROM employees e
LEFT JOIN employee_activities ea ON e.id = ea.employee_id
GROUP BY e.id, e.name
ORDER BY activity_count DESC;
```

#### Kafka UI (Stream Monitoring)
- **URL**: http://localhost:8081
- **Purpose**: Monitor topics, partitions, consumer lag

**Key Metrics to Watch**:
- Message count per topic
- Consumer group lag
- Partition distribution
- Throughput rates

### 6.2 Common Issues & Solutions

#### Issue 1: Debezium Connector Not Running
**Symptoms**: No messages in Kafka topics
**Check**:
```bash
curl http://localhost:8083/connectors/employee-connector/status
```
**Solution**:
```bash
curl -X POST http://localhost:8083/connectors/employee-connector/restart
```

#### Issue 2: Consumer Lag
**Symptoms**: Spark processing falling behind
**Check**:
```bash
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group [group-id] --describe
```
**Solutions**:
- Increase Spark parallelism
- Optimize processing logic
- Scale Kafka partitions

#### Issue 3: Database Connection Issues
**Check**:
```bash
docker exec postgres-db psql -U postgres -d streaming_db -c "SELECT 1;"
```
**Common Causes**:
- Container not running
- Network connectivity issues
- Authentication problems

---

## Summary

This project demonstrates a complete **real-time data streaming pipeline** that teaches:

### Technical Concepts Learned
- **Apache Kafka**: Message streaming, topics, partitions, offsets
- **Change Data Capture (CDC)**: Real-time database change tracking
- **Stream Processing**: Real-time data transformation with Spark
- **Containerization**: Docker orchestration and networking

### Practical Skills Gained
- Setting up distributed systems
- Configuring CDC connectors
- Writing stream processing applications
- Monitoring and troubleshooting streaming pipelines

### Business Applications
- Real-time analytics
- Event-driven architectures
- Data pipeline automation
- Scalable data processing

This foundation prepares you for building production-grade streaming systems and understanding modern data architectures.
