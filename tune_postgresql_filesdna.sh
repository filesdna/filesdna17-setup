#!/bin/bash

# PostgreSQL Configuration File
PG_CONF="/etc/postgresql/16/main/postgresql.conf"
PG_HBA="/etc/postgresql/16/main/pg_hba.conf"

# Backup existing configuration files
cp $PG_CONF "$PG_CONF.bak_$(date +%F_%T)"
cp $PG_HBA "$PG_HBA.bak_$(date +%F_%T)"

# Update postgresql.conf for Odoo optimization
sed -i "/^#?max_connections/c\max_connections = 200" $PG_CONF
sed -i "/^#?superuser_reserved_connections/c\superuser_reserved_connections = 3" $PG_CONF
sed -i "/^#?shared_buffers/c\shared_buffers = 4GB" $PG_CONF
sed -i "/^#?effective_cache_size/c\effective_cache_size = 10GB" $PG_CONF
sed -i "/^#?work_mem/c\work_mem = 64MB" $PG_CONF
sed -i "/^#?maintenance_work_mem/c\maintenance_work_mem = 512MB" $PG_CONF
sed -i "/^#?checkpoint_timeout/c\checkpoint_timeout = 15min" $PG_CONF
sed -i "/^#?checkpoint_completion_target/c\checkpoint_completion_target = 0.9" $PG_CONF
sed -i "/^#?wal_buffers/c\wal_buffers = 16MB" $PG_CONF
sed -i "/^#?wal_writer_delay/c\wal_writer_delay = 200ms" $PG_CONF
sed -i "/^#?autovacuum/c\autovacuum = on" $PG_CONF
sed -i "/^#?autovacuum_max_workers/c\autovacuum_max_workers = 3" $PG_CONF
sed -i "/^#?autovacuum_naptime/c\autovacuum_naptime = 15s" $PG_CONF
sed -i "/^#?autovacuum_vacuum_cost_limit/c\autovacuum_vacuum_cost_limit = 2000" $PG_CONF
sed -i "/^#?parallel_tuple_cost/c\parallel_tuple_cost = 0.1" $PG_CONF
sed -i "/^#?parallel_setup_cost/c\parallel_setup_cost = 100" $PG_CONF
sed -i "/^#?min_parallel_table_scan_size/c\min_parallel_table_scan_size = 8MB" $PG_CONF
sed -i "/^#?min_parallel_index_scan_size/c\min_parallel_index_scan_size = 512kB" $PG_CONF
sed -i "/^#?max_parallel_workers_per_gather/c\max_parallel_workers_per_gather = 2" $PG_CONF
sed -i "/^#?max_parallel_workers/c\max_parallel_workers = 6" $PG_CONF
sed -i "/^#?wal_level/c\wal_level = minimal" $PG_CONF
sed -i "/^#?synchronous_commit/c\synchronous_commit = off" $PG_CONF
sed -i "/^#?full_page_writes/c\full_page_writes = off" $PG_CONF
sed -i "/^#?random_page_cost/c\random_page_cost = 1.1" $PG_CONF
sed -i "/^#?effective_io_concurrency/c\effective_io_concurrency = 200" $PG_CONF
sed -i "/^#?default_statistics_target/c\default_statistics_target = 100" $PG_CONF
sed -i "/^#?max_worker_processes/c\max_worker_processes = 6" $PG_CONF

# Update pg_hba.conf for secure connections
echo "local   all             all                                     md5" > $PG_HBA
echo "host    all             all             127.0.0.1/32            md5" >> $PG_HBA
echo "host    all             all             ::1/128                 md5" >> $PG_HBA

# Restart PostgreSQL service
echo "Restarting PostgreSQL to apply changes..."
sudo systemctl restart postgresql@16-main

echo "✅ PostgreSQL tuning for FilesDNA is complete!"

