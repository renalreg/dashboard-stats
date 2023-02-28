from ukrdc.database import Connection

import pandas as pd
import glob

engine = Connection.get_engine_from_file(key="ukrdc_live")

paths = glob.glob("mappings/*.csv")
print(paths)


for path in paths:
    data = pd.read_csv(path)
    data.to_sql("code_map", engine, if_exists="append", index=False)
    # print(data)
