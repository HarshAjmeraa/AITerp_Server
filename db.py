import pyodbc

# Replace with your actual connection details
server = 'moli-dev-es-sqlserver.database.windows.net'
database = 'moli-dev-es-sqldb'
username = 'moli-dev-es-sql-admin'
password = 'HyIa0MInqwdpD3N'
driver = '{ODBC Driver 18 for SQL Server}'
connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'

def get_db_connection():
    return pyodbc.connect(connection_string, timeout=30)
