from .client import DBClient

def get_create_table_sql():
    with open('sql/users.sql', 'r') as file:
        return file.read()

def migrate_database():
    client = DBClient()
    client.execute_sql(get_create_table_sql())
    client.close()
