from rr_connection_manager import PostgresConnection

# this code does work
ukrdc_conn = PostgresConnection(
    app="ukrdc_staging",
    via_app=True,
    tunnel = True
)
#conn._connection_details["db_host"] = conn.connection_conf.db_host

ukrdc_conn.connection_check()
print(":)")