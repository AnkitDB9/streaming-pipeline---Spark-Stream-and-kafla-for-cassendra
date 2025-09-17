# Enhanced Multi-Source Streaming Pipeline

## 🏗️ Clean Project Structure

```
kafka_cassendra/
├── docker-compose.yml                           # Complete infrastructure setup
├── debezium-employee-connector.json            # PostgreSQL CDC connector
├── cassandra-connector.json                    # Cassandra source connector
├── init-scripts/
│   ├── 01-init-db.sql                          # PostgreSQL setup
│   └── 02-employee-activity.sql                # Employee tables
├── cassandra-init/
│   └── 01-keyspace-tables.cql                  # Cassandra setup
├── hive-scripts/
│   └── create_tables.sql                       # Hive analytics tables
├── spark-streaming/
│   ├── multi_source_streaming_processor.py     # Main Spark application
│   └── requirements.txt                        # Python dependencies
├── scripts/
│   ├── setup-enhanced.sh                       # Complete setup script
│   ├── employee-activity-generator.py          # PostgreSQL data generator
│   └── cassandra-activity-generator.py         # Cassandra data generator
├── README.md                                   # Project overview
├── PROJECT_DOCUMENTATION.md                   # Detailed documentation
└── KAFKA_LEARNING_MANUAL.md                   # Kafka concepts
```

## 🎯 Architecture Components

### Data Sources
- **PostgreSQL**: Employee master data
- **Cassandra**: High-volume activity data

### Streaming Pipeline
- **Kafka**: Message broker with multiple topics
- **Debezium**: PostgreSQL CDC connector
- **Cassandra Connector**: Activity data streaming
- **Spark Streaming**: Multi-source processor with Hudi integration

### Storage & Analytics
- **HDFS**: Distributed file storage
- **Apache Hudi**: Solves small files problem
- **Hive**: SQL analytics layer

## 🚀 Quick Start

1. **Setup Infrastructure**:
   ```bash
   chmod +x scripts/setup-enhanced.sh
   ./scripts/setup-enhanced.sh
   ```

2. **Start Streaming**:
   ```bash
   python3 spark-streaming/multi_source_streaming_processor.py
   ```

3. **Generate Data**:
   ```bash
   # Terminal 1
   python3 scripts/employee-activity-generator.py
   
   # Terminal 2  
   python3 scripts/cassandra-activity-generator.py
   ```

## 📊 Output Topics

- `processed-employees` - Enriched employee data
- `processed-activities` - Enriched activity data  
- `hourly-activity-aggregations` - Real-time hourly metrics
- `daily-device-aggregations` - Device usage patterns

## 🔧 Key Features

- ✅ Multi-database streaming (PostgreSQL + Cassandra)
- ✅ Real-time transformations and aggregations
- ✅ Small files problem solved with Apache Hudi
- ✅ HDFS storage with Hive analytics
- ✅ Fault-tolerant processing with checkpointing
- ✅ Exactly-once processing semantics
