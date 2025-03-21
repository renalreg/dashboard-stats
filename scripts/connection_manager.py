from rr_connection_manager import PostgresConnection
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker


# this code does work
jtrace_conn = PostgresConnection(
app="ukrdc_staging",
tunnel=True,
via_app=True,
)
jtrace_conn._connection_details["db_name"] = "removed_xml_archive"
jtrace_sessionmaker = jtrace_conn.session_maker()

with jtrace_sessionmaker() as jtrace_session:
    for item in jtrace_session.execute(text("SELECT * FROM patient_demog limit 10")): 
        print(item)

print(jtrace_conn._connection_details)
# this code doesn't work
jtrace_conn = PostgresConnection(
app="ukrdc_staging",
tunnel=True,
via_app=True,
)
#jtrace_conn._connection_details["db_name"] = "removed_xml_archive"
jtrace_session = jtrace_conn.session()

url = jtrace_session.bind.url
print(url)

archive_db_url = str(url).replace(url.database, "removed_xml_archive")
print(archive_db_url)
    
engine = create_engine(archive_db_url)
session = sessionmaker(bind=engine)()

for item in jtrace_session.execute(text("SELECT * FROM patientrecord limit 10")):
    print(item) 
    
for item in session.execute(text("SELECT * FROM patient_demog limit 10")): 
    print(item)
    
