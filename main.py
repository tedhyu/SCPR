import re
import csv
import flask
import array as arr
from google.cloud import bigquery
from google.cloud import storage

def sql(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    
    request_args = request.args
    if request_args and "event" in request_args:
        eventname = request_args["event"]

    file='caltech.csv'
    input_bucket='csv-input-bucket'
    client = storage.Client()
    bucket = client.get_bucket(input_bucket)
    blob = bucket.blob(file)
    with open("/tmp/temp.csv", "wb") as file_obj:
        blob.download_to_file(file_obj)         
       
    list1=[]
    with open("/tmp/temp.csv") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            column=len(row)
            if line_count == 0:   #process column names
                email_columns=arr.array('i',[])
                for n in range(column):
                    lc=row[n].lower()
                    if(re.search('email',lc)):             #search for email in column name
                        email_columns.append(n)
                    if(re.search('last name',lc)):         #search for last name in column name
                        last_name=n
                    if(re.search('first name',lc)):        #search for first name in column name
                        first_name=n
                line_count += 1
            else:
                #iterate through the email columns for each row and add last, first name
                columns=len(email_columns)   #could vary from 1 to 3 or more buyer_email, email_address, etc
                for m in range(columns):
                    if(re.search('@', row[email_columns[m]])):
                    #print(row[email_columns[m]])
                        list1.append((row[email_columns[m]],row[first_name],row[last_name]))
                line_count += 1

    list1.sort()   
    email=''
    line_count2 = 0
    SQL="INSERT INTO customertable.customer (email, first_name, last_name, event) VALUES "
    for row2 in list1:
        if(email!=row2[0]):
            if (line_count2!=0):
            	SQL=SQL+" , "
            #SQL = SQL+"('"+row2[0]+"', '"+eventname+"')"
            SQL = SQL+"('"+row2[0]+"', '"+row2[1]+"', '"+row2[2]+"', '"+eventname+"')"
            email=row2[0]
            line_count2 +=1
    print(SQL)
    bq_client = bigquery.Client()
    query_job = bq_client.query(SQL)

    
#    QUERY =  "UPDATE customertable.customer SET attendance=" + str(line_count) + " WHERE customer_id=3" 
#    bq_client = bigquery.Client()
#    query_job = bq_client.query(QUERY)
    
    
    if request_args and "name" in request_args:
        name = request_args["name"]
    else:
        name = "World"
    return "Hello {}!".format(flask.escape(name))
    
    

