import re

# Define the old and new method content
old_method = """    def _get_errors_fallback_data(self):
        \"\"\"Fallback method to get error data from graylog_messages if system_errors doesn't exist.\"\"\"
        with get_db_cursor() as cursor:
            try:
                sql = \"\"\"
                    SELECT 
                        id as log_id,
                        timestamp, 
                        level, 
                        source,
                        host as host_name,
                        message, 
                        details
                    FROM graylog_messages
                    WHERE timestamp BETWEEN %s AND %s
                    AND level IN ('error', 'critical', 'fatal')
                \"\"\"
                
                params = [self.start_date, self.end_date]
                
                # Add limit if specified
                if self.record_limit:
                    sql += " LIMIT %s"
                    params.append(self.record_limit)
                
                cursor.execute(sql, params)
                results = cursor.fetchall()
                print(f"Retrieved {len(results)} error records from fallback")
                return results
            except Exception as e:
                print(f"Error in fallback query: {str(e)}")
                traceback.print_exc()
                return []"""

new_method = """    def _get_errors_fallback_data(self):
        \"\"\"Fallback method to get error data from graylog_messages if system_errors doesn't exist.\"\"\"
        with get_db_cursor() as cursor:
            try:
                sql = \"\"\"
                    SELECT 
                        id as log_id,
                        timestamp, 
                        level, 
                        category as source,
                        COALESCE(JSON_UNQUOTE(JSON_EXTRACT(details, '$.formsdbsessionid')), 'unknown') as host_name,
                        message, 
                        details
                    FROM graylog_messages
                    WHERE timestamp BETWEEN %s AND %s
                    AND level IN ('error', 'critical', 'fatal')
                \"\"\"
                
                params = [self.start_date, self.end_date]
                
                # Add limit if specified
                if self.record_limit:
                    sql += " LIMIT %s"
                    params.append(self.record_limit)
                
                cursor.execute(sql, params)
                results = cursor.fetchall()
                print(f"Retrieved {len(results)} error records from fallback")
                return results
            except Exception as e:
                print(f"Error in fallback query: {str(e)}")
                traceback.print_exc()
                return []"""

# Read the file content
file_path = 'modules/reports.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Use regex to find and replace the method
pattern = r'def _get_errors_fallback_data\(self\):.*?return \[\]'
escaped_old_pattern = re.escape(old_method.strip())
updated_content = re.sub(escaped_old_pattern, new_method.strip(), content, flags=re.DOTALL)

# Write the updated content back to the file
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(updated_content)

print('File updated successfully!')
