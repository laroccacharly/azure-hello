from azure_hello.client import DBClient

sql_file = 'sql/show.sql'

sql_query = open(sql_file, 'r').read()

client = DBClient()
results = client.execute_sql(sql_query)
print(results)

sql_file = 'sql/create_user.sql'
sql_query = open(sql_file, 'r').read()
results = client.execute_sql(sql_query)
print(results)

sql_file = 'sql/query_users.sql'
sql_query = open(sql_file, 'r').read()
results = client.execute_sql(sql_query)
print(results)

client.close()
