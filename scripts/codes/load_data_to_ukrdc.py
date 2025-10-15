"""This script inserts all of the code mappings into the ukrdc.
    TODO: add something to remove all URTS codes before insertion
"""


from rr_connection_manager import PostgresConnection

import pandas as pd
import glob

SERVER = 'ukrdc_staging'

conn = PostgresConnection(app=SERVER, tunnel=True, via_app=True)


engine = conn.engine()

paths = glob.glob("scripts/codes/mappings/*.csv")
print(paths)


for path in paths:
    data = pd.read_csv(path)
    data.to_sql("code_map", engine, if_exists="append", index=False)
    # print(data)
