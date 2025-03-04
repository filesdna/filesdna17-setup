from datetime import datetime

def convert_datetimes(data):
    # Recursively convert datetime objects to timestamps in milliseconds
    if isinstance(data, dict):
        return {k: convert_datetimes(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_datetimes(item) for item in data]
    elif isinstance(data, datetime):
        # Convert datetime to timestamp in milliseconds
        return int(data.timestamp() * 1000)
    else:
        return data

def serialize_record(record):
    """Helper function to convert datetime fields in a record to a JSON serializable format."""
    serialized_record = {}
    for key, value in record.items():
        if isinstance(value, datetime):
            # Convert datetime to a Unix timestamp
            serialized_record[key] = int(value.timestamp() * 1000)  # Converts to milliseconds
        else:
            serialized_record[key] = value
    return serialized_record