import os
import pyodbc
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import pandas as pd

class DBClient:
    def __init__(self):
        self.server_name = os.environ.get("SQL_SERVER_NAME")
        self.database_name = os.environ.get("SQL_DB_NAME")
        self.admin_user = os.environ.get("SQL_ADMIN")
        self.keyvault_name = os.environ.get("KEYVAULT_NAME")
        self.password_secret_name = f"{self.server_name}-password"

        if not all([self.server_name, self.database_name, self.admin_user, self.keyvault_name]):
            raise ValueError("Required environment variables (SQL_SERVER_NAME, SQL_DB_NAME, SQL_ADMIN, KEYVAULT_NAME) are not set. Please source env.sh first.")

        self.keyvault_uri = f"https://{self.keyvault_name}.vault.azure.net"
        self.driver = "{ODBC Driver 18 for SQL Server}"
        self.sql_password = self._fetch_password()
        self.conn_str = (
            f"DRIVER={self.driver};"
            f"SERVER=tcp:{self.server_name}.database.windows.net,1433;"
            f"DATABASE={self.database_name};"
            f"UID={self.admin_user};"
            f"PWD={self.sql_password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        self.connection = None

    def _fetch_password(self):
        print(f"Fetching password secret '{self.password_secret_name}' from Key Vault '{self.keyvault_name}'...")
        try:
            credential = DefaultAzureCredential()
            secret_client = SecretClient(vault_url=self.keyvault_uri, credential=credential)
            sql_password = secret_client.get_secret(self.password_secret_name).value
            print("Successfully fetched SQL password from Key Vault.")
            return sql_password
        except Exception as e:
            raise RuntimeError(f"Error fetching secret from Key Vault: {e}. Ensure you are logged into Azure (az login) and have permissions.")

    def connect(self):
        if self.connection is None:
            print(f"Connecting to database '{self.database_name}' on server '{self.server_name}.database.windows.net'...")
            try:
                self.connection = pyodbc.connect(self.conn_str, autocommit=True)
                print("Connection successful.")
            except pyodbc.Error as ex:
                sqlstate = ex.args[0]
                raise RuntimeError(f"Error connecting to database: {sqlstate}. {ex}")
            except Exception as e:
                raise RuntimeError(f"An unexpected error occurred while connecting: {e}")
        return self.connection

    def execute_sql(self, sql_script):
        if not self.connection:
            self.connect()
        try:
            with self.connection.cursor() as cursor:
                print("Executing SQL script...")
                cursor.execute(sql_script)
                # Check if the query returns results
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    results = cursor.fetchall()
                    # Ensure results are in a list of lists format for DataFrame
                    formatted_results = [list(row) for row in results]
                    df = pd.DataFrame(formatted_results, columns=columns)
                    print("SQL script executed with results.")
                    return df
                else:
                    print("SQL script executed.")
                    return None
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            raise RuntimeError(f"Error executing SQL script: {sqlstate}. {ex}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while executing SQL: {e}")

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
            print("Database connection closed.")
