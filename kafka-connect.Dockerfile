# Start from the base Debezium Connect image
FROM debezium/connect:2.4

# Define environment variables for the user and plugin versions
ENV KAFKA_CONNECT_USER=kafka-connect
ENV DEBEZIUM_VERSION=2.4

# Switch to the root user to install plugins
USER root

# Use the built-in script to download and install the PostgreSQL connector
RUN /kafka/connect/bin/install-plugins.sh https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.4.2.Final/debezium-connector-postgres-2.4.2.Final-plugin.tar.gz

# Create a directory for our custom DataStax Cassandra connector
RUN mkdir -p /kafka/connect/cassandra-connector

# Copy our manually downloaded Cassandra connector JAR into the new directory
COPY kafka-connect-plugins/cassandra-connector/kafka-connect-source-cassandra-1.1.0.jar /kafka/connect/cassandra-connector/

# Switch back to the non-root user
USER ${KAFKA_CONNECT_USER}
