#!/bin/bash

# PostgreSQL Configuration File
PG_CONF="/etc/postgresql/16/main/postgresql.conf"
PG_HBA="/etc/postgresql/16/main/pg_hba.conf"

# Backup existing configuration files
cp $PG_CONF "$PG_CONF.bak_$(date +%F_%T)"
cp $PG_HBA "$PG_HBA.bak_$(date +%F_%T)"

echo "Detecting your system specs..."

# Get server specs
total_ram=$(free -m | awk '/Mem:/ {print $2}')  # Total RAM in MB
total_cpus=$(nproc)  # Total number of CPUs

echo "Detected system specs: $total_ram MB RAM, $total_cpus CPUs"

echo -e "\nSelect server configuration option:"
echo "1) 64GB RAM, 14 CPUs (High Performance)"
echo "2) 16GB RAM, 6 CPUs (Medium Performance)"
echo "3) 32GB RAM, 8 CPUs (Balanced Performance)"
echo -n "Enter your choice [1 or 2 or 3]: "
read choice

# Set PostgreSQL parameters based on the user's choice
case $choice in
    1)
        shared_buffers="16GB"
        effective_cache_size="48GB"
        work_mem="128MB"
        maintenance_work_mem="2GB"
        max_connections="300"
        max_wal_senders="10"
        max_parallel_workers_per_gather="8"
        max_parallel_workers="14"
        ;;
    2)
        shared_buffers="2GB"
        effective_cache_size="6GB"
        work_mem="64MB"
        maintenance_work_mem="1GB"
        max_connections="100"
        max_wal_senders="3"
        max_parallel_workers_per_gather="2"
        max_parallel_workers="4"
        ;;
    3)
        shared_buffers="4GB"
        effective_cache_size="12GB"
        work_mem="64MB"
        maintenance_work_mem="1GB"
        max_connections="200"
        max_wal_senders="5"
        max_parallel_workers_per_gather="3"
        max_parallel_workers="6"
        ;;
    *)
        echo "Invalid choice! Exiting."
        exit 1
        ;;
esac

# Show selected configuration settings to the user
echo -e "\nUpdating PostgreSQL configuration for optimal performance..."
echo "Updating the following PostgreSQL parameters based on your selection:"
echo "Shared Buffers: $shared_buffers"
echo "Effective Cache Size: $effective_cache_size"
echo "Work Memory: $work_mem"
echo "Maintenance Work Memory: $maintenance_work_mem"
echo "Max Connections: $max_connections"
echo "Max WAL Senders: $max_wal_senders"
echo "Max Parallel Workers per Gather: $max_parallel_workers_per_gather"
echo "Max Parallel Workers: $max_parallel_workers"

# Apply the changes to the PostgreSQL config file
sed -i "/^#\?shared_buffers/c\shared_buffers = $shared_buffers" $PG_CONF
sed -i "/^#\?effective_cache_size/c\effective_cache_size = $effective_cache_size" $PG_CONF
sed -i "/^#\?work_mem/c\work_mem = $work_mem" $PG_CONF
sed -i "/^#\?maintenance_work_mem/c\maintenance_work_mem = $maintenance_work_mem" $PG_CONF
sed -i "/^#\?max_connections/c\max_connections = $max_connections" $PG_CONF
sed -i "/^#\?max_wal_senders/c\max_wal_senders = $max_wal_senders" $PG_CONF
sed -i "/^#\?max_parallel_workers_per_gather/c\max_parallel_workers_per_gather = $max_parallel_workers_per_gather" $PG_CONF
sed -i "/^#\?max_parallel_workers/c\max_parallel_workers = $max_parallel_workers" $PG_CONF

# Update pg_hba.conf for secure connections (peer authentication)
echo "Updating pg_hba.conf for secure connections..."
echo "local   all             all                                     peer" > $PG_HBA
echo "host    all             all             127.0.0.1/32            md5" >> $PG_HBA
echo "host    all             all             ::1/128                 md5" >> $PG_HBA

# Restart PostgreSQL service to apply changes
echo "Restarting PostgreSQL to apply changes..."
sudo systemctl restart postgresql@16-main

echo "✅ PostgreSQL tuning for FilesDNA is complete!"
