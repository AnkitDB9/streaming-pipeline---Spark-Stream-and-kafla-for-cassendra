#!/usr/bin/env python3
"""
Enhanced Multi-Source Streaming Processor
- Reads from PostgreSQL (employees) and Cassandra (activities) via Kafka
- Applies multiple transformations
- Writes to different Kafka topics
- Stores data in HDFS using Apache Hudi
- Solves small files problem
"""

import json
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiSourceStreamingProcessor:
    def __init__(self):
        self.spark = None
        self.initialize_spark()
        
    def initialize_spark(self):
        """Initialize Spark session with Kafka, HDFS, and Hudi support"""
        self.spark = SparkSession.builder \
            .appName("MultiSourceStreamingProcessor") \
            .config("spark.jars.packages", 
                   "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                   "org.apache.hudi:hudi-spark3.5-bundle_2.12:0.14.0,"
                   "org.apache.hadoop:hadoop-client:3.3.4") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.minPartitionNum", "1") \
            .config("spark.sql.adaptive.advisoryPartitionSizeInBytes", "128MB") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.hudi.catalog.HoodieCatalog") \
            .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension") \
            .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        logger.info("Spark session initialized with Kafka, HDFS, and Hudi support")

    def define_schemas(self):
        """Define schemas for employee and activity data"""
        employee_schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("email", StringType(), True),
            StructField("department", StringType(), True),
            StructField("created_at", TimestampType(), True)
        ])
        
        activity_schema = StructType([
            StructField("id", StringType(), True),  # UUID from Cassandra
            StructField("employee_id", IntegerType(), True),
            StructField("activity_type", StringType(), True),
            StructField("page_url", StringType(), True),
            StructField("duration_seconds", IntegerType(), True),
            StructField("ip_address", StringType(), True),
            StructField("user_agent", StringType(), True),
            StructField("activity_timestamp", TimestampType(), True),
            StructField("session_id", StringType(), True),
            StructField("device_type", StringType(), True),
            StructField("browser", StringType(), True),
            StructField("created_at", TimestampType(), True)
        ])
        
        return employee_schema, activity_schema

    def read_employee_stream(self):
        """Read employee data from PostgreSQL via Kafka"""
        return self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", "employee-server.public.employees") \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()

    def read_activity_stream(self):
        """Read activity data from PostgreSQL via Kafka (employee_activities table)"""
        return self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", "employee-server.public.employee_activities") \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()

    def process_employee_data(self, df):
        """Process employee data from PostgreSQL"""
        employee_schema, _ = self.define_schemas()
        
        # Parse Debezium CDC message
        parsed_df = df.select(
            col("topic"),
            col("key").cast("string").alias("key"),
            from_json(col("value").cast("string"), 
                     StructType([
                         StructField("payload", StructType([
                             StructField("after", StringType(), True),
                             StructField("op", StringType(), True),
                             StructField("ts_ms", LongType(), True)
                         ]), True)
                     ])).alias("parsed_value"),
            col("timestamp")
        )
        
        # Extract employee data (INSERT and UPDATE operations)
        employee_df = parsed_df \
            .filter(col("parsed_value.payload.op").isin(["c", "u"])) \
            .select(
                from_json(col("parsed_value.payload.after"), employee_schema).alias("employee"),
                col("parsed_value.payload.ts_ms").alias("event_timestamp"),
                col("timestamp").alias("processing_timestamp")
            ).select("employee.*", "event_timestamp", "processing_timestamp")
        
        # Add enrichment columns
        enriched_df = employee_df.withColumn(
            "department_category",
            when(col("department").isin(["Engineering", "IT"]), "Technical")
            .when(col("department").isin(["Sales", "Marketing"]), "Business")
            .otherwise("Support")
        ).withColumn(
            "employee_level",
            when(col("email").contains("senior"), "Senior")
            .when(col("email").contains("lead"), "Lead")
            .otherwise("Regular")
        ).withColumn(
            "data_source", lit("postgresql")
        ).withColumn(
            "processing_date", current_date()
        )
        
        return enriched_df

    def process_activity_data(self, df):
        """Process activity data from PostgreSQL (same CDC format as employees)"""
        _, activity_schema = self.define_schemas()
        
        # Parse Debezium CDC message (same format as employees)
        parsed_df = df.select(
            col("topic"),
            col("key").cast("string").alias("key"),
            from_json(col("value").cast("string"), 
                     StructType([
                         StructField("payload", StructType([
                             StructField("after", StringType(), True),
                             StructField("op", StringType(), True),
                             StructField("ts_ms", LongType(), True)
                         ]), True)
                     ])).alias("parsed_value"),
            col("timestamp")
        )
        
        # Extract activity data (INSERT and UPDATE operations)
        activity_df = parsed_df \
            .filter(col("parsed_value.payload.op").isin(["c", "u"])) \
            .select(
                from_json(col("parsed_value.payload.after"), activity_schema).alias("activity"),
                col("parsed_value.payload.ts_ms").alias("event_timestamp"),
                col("timestamp").alias("processing_timestamp")
            ).select("activity.*", "event_timestamp", "processing_timestamp")
        
        # Add enrichment columns
        enriched_df = activity_df.withColumn(
            "activity_hour", hour(col("activity_timestamp"))
        ).withColumn(
            "activity_date", to_date(col("activity_timestamp"))
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
        ).withColumn(
            "device_category",
            when(col("device_type") == "mobile", "Mobile")
            .when(col("device_type") == "tablet", "Tablet")
            .otherwise("Desktop")
        ).withColumn(
            "data_source", lit("postgresql")
        ).withColumn(
            "processing_date", current_date()
        )
        
        return enriched_df

    def create_activity_aggregations(self, activity_df):
        """Create multiple types of aggregations"""
        
        # Hourly aggregations by employee
        hourly_agg = activity_df \
            .groupBy(
                window(col("activity_timestamp"), "1 hour"),
                col("employee_id"),
                col("activity_type")
            ) \
            .agg(
                count("*").alias("activity_count"),
                sum("duration_seconds").alias("total_duration"),
                avg("duration_seconds").alias("avg_duration"),
                collect_set("page_url").alias("unique_pages"),
                first("device_category").alias("primary_device")
            ) \
            .withColumn("aggregation_type", lit("hourly")) \
            .withColumn("window_start", col("window.start")) \
            .withColumn("window_end", col("window.end")) \
            .drop("window")
        
        # Daily aggregations by department
        daily_dept_agg = activity_df \
            .groupBy(
                window(col("activity_timestamp"), "1 day"),
                col("activity_type"),
                col("device_category")
            ) \
            .agg(
                count("*").alias("activity_count"),
                countDistinct("employee_id").alias("unique_employees"),
                avg("duration_seconds").alias("avg_duration")
            ) \
            .withColumn("aggregation_type", lit("daily_device")) \
            .withColumn("window_start", col("window.start")) \
            .withColumn("window_end", col("window.end")) \
            .drop("window")
        
        return hourly_agg, daily_dept_agg

    def write_to_kafka_topic(self, df, topic_name, output_mode="append"):
        """Write processed data to Kafka topic"""
        kafka_df = df.select(
            coalesce(col("employee_id"), col("id")).cast("string").alias("key"),
            to_json(struct(*df.columns)).alias("value")
        )
        
        query = kafka_df.writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("topic", topic_name) \
            .option("checkpointLocation", f"/tmp/checkpoint-{topic_name}") \
            .outputMode(output_mode) \
            .trigger(processingTime='30 seconds') \
            .start()
        
        return query

    def write_to_hudi(self, df, table_name, path, record_key, precombine_field):
        """Write data to HDFS using Apache Hudi (solves small files problem)"""
        
        hudi_options = {
            'hoodie.table.name': table_name,
            'hoodie.datasource.write.recordkey.field': record_key,
            'hoodie.datasource.write.precombine.field': precombine_field,
            'hoodie.datasource.write.partitionpath.field': 'processing_date',
            'hoodie.datasource.hive_sync.enable': 'true',
            'hoodie.datasource.hive_sync.database': 'streaming_db',
            'hoodie.datasource.hive_sync.table': table_name,
            'hoodie.datasource.hive_sync.partition_fields': 'processing_date',
            'hoodie.datasource.hive_sync.partition_extractor_class': 'org.apache.hudi.hive.MultiPartKeysValueExtractor',
            'hoodie.datasource.hive_sync.metastore.uris': 'thrift://hive-metastore:9083',
            'hoodie.datasource.write.table.type': 'COPY_ON_WRITE',
            'hoodie.clean.automatic': 'true',
            'hoodie.clean.async': 'true',
            'hoodie.cleaner.policy': 'KEEP_LATEST_FILE_VERSIONS',
            'hoodie.cleaner.fileversions.retained': '3',
            'hoodie.compact.inline': 'true',
            'hoodie.compact.inline.max.delta.commits': '5'
        }
        
        query = df.writeStream \
            .format("hudi") \
            .options(**hudi_options) \
            .option("path", path) \
            .option("checkpointLocation", f"/tmp/checkpoint-hudi-{table_name}") \
            .outputMode("append") \
            .trigger(processingTime='2 minutes') \
            .start()
        
        return query

    def write_to_console(self, df, query_name):
        """Write data to console for monitoring"""
        query = df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .option("numRows", 10) \
            .queryName(query_name) \
            .trigger(processingTime='30 seconds') \
            .start()
        
        return query

    def start_processing(self):
        """Start the complete multi-source streaming pipeline"""
        try:
            logger.info("Starting multi-source streaming pipeline...")
            
            # Read from both sources
            employee_stream = self.read_employee_stream()
            activity_stream = self.read_activity_stream()
            
            # Process data from both sources
            processed_employees = self.process_employee_data(employee_stream)
            processed_activities = self.process_activity_data(activity_stream)
            
            # Create aggregations
            hourly_agg, daily_agg = self.create_activity_aggregations(processed_activities)
            
            # Write to different Kafka topics
            queries = []
            
            # Employee data to Kafka
            queries.append(self.write_to_kafka_topic(
                processed_employees, "processed-employees"
            ))
            
            # Activity data to Kafka
            queries.append(self.write_to_kafka_topic(
                processed_activities, "processed-activities"
            ))
            
            # Hourly aggregations to Kafka
            queries.append(self.write_to_kafka_topic(
                hourly_agg, "hourly-activity-aggregations", "update"
            ))
            
            # Daily aggregations to Kafka
            queries.append(self.write_to_kafka_topic(
                daily_agg, "daily-device-aggregations", "update"
            ))
            
            # Write to HDFS using Hudi (solves small files problem)
            queries.append(self.write_to_hudi(
                processed_employees,
                "employees_hudi",
                "hdfs://namenode:9000/streaming/employees",
                "id",
                "processing_timestamp"
            ))
            
            queries.append(self.write_to_hudi(
                processed_activities,
                "activities_hudi", 
                "hdfs://namenode:9000/streaming/activities",
                "id",
                "processing_timestamp"
            ))
            
            # Console outputs for monitoring
            queries.append(self.write_to_console(processed_employees, "employees"))
            queries.append(self.write_to_console(processed_activities, "activities"))
            queries.append(self.write_to_console(hourly_agg, "hourly_agg"))
            
            logger.info("All streaming queries started successfully")
            logger.info("Output Kafka topics: processed-employees, processed-activities, hourly-activity-aggregations, daily-device-aggregations")
            logger.info("HDFS paths: /streaming/employees, /streaming/activities")
            
            # Wait for all streams to terminate
            for query in queries:
                query.awaitTermination()
                
        except Exception as e:
            logger.error(f"Error in processing: {str(e)}")
            raise
        finally:
            if self.spark:
                self.spark.stop()

def main():
    """Main function to run the multi-source streaming processor"""
    processor = MultiSourceStreamingProcessor()
    
    try:
        logger.info("Starting Multi-Source Streaming Processor...")
        processor.start_processing()
    except KeyboardInterrupt:
        logger.info("Processing stopped by user")
    except Exception as e:
        logger.error(f"Error running processor: {str(e)}")
    finally:
        logger.info("Processor shutdown complete")

if __name__ == "__main__":
    main()
