import re
import csv
import flask
import os
import urllib
from google.cloud import bigquery
from google.cloud import storage
from datetime import datetime

def main(request):
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
    else:
        return "Missing Event Name Parameter"        
    if request_args and "venue" in request_args:
        venue = request_args["venue"]
    else:
        return "Missing Venue Parameter"        
    if request_args and "eventdate" in request_args:
        eventdate = request_args["eventdate"]
    else:
        return "Missing Event Date Parameter"        
    if request_args and "overwrite" in request_args:
        trigger = request_args["overwrite"]
    else:
        return "Missing Trigger Parameter"

    bg_client = bigquery.Client()      

    if (trigger=='unknown'):
        SQL0 = 'SELECT Datestamp from customertable.events where Eventname="'+eventname+'" and Venue="' + venue + '" and Eventdate="'+eventdate+'"' 
        query_job0 = bg_client.query(SQL0)
        datestamp=0
        for row in query_job0:
            datestamp=row.Datestamp
            break
        if (datestamp!=0):
             #  No previous record with the same venue, eventdate, and event.  Proceed.
            datetime_new = re.sub('\.\d(.*)$', '', str(datestamp))
            message="There is previous record of " + eventname + " on " + eventdate + " at " + venue + " recorded at " + datetime_new + ".  Overwrite?"            
            eventname=urllib.parse.quote_plus(eventname)  # account for special symbols in URL
            venue=urllib.parse.quote_plus(venue)
            eventdate=urllib.parse.quote_plus(eventdate)
            message=message+'&nbsp<a href="https://us-central1-scprbigquery.cloudfunctions.net/upload_confirm?overwrite=yes&event=' + eventname + '&venue=' + venue + '&eventdate=' + eventdate + '">Yes</a>'
            message=message+'&nbsp<a href="https://us-central1-scprbigquery.cloudfunctions.net/upload_confirm?overwrite=no&event=' + eventname + '&venue=' + venue + '&eventdate=' + eventdate + '">No</a>'
            return message
        is_salesforce,attendees=check_data(eventname,venue,eventdate,bg_client)
        return insert(eventname,venue,eventdate,bg_client,is_salesforce,attendees)       

    elif (trigger=='yes'):
        delete_old(eventname,venue,eventdate,bg_client)
        is_salesforce,attendees=check_data(eventname,venue,eventdate,bg_client)
        return insert(eventname,venue,eventdate,bg_client,is_salesforce,attendees)  #delete previous data of event selected, so it can be overwritten.
        
    else:
        message="No new data was entered as requested."
        return message  

def delete_old(eventname,venue,eventdate,bg_client):  
    SQL0 = 'DELETE FROM customertable.events where Eventname="'+eventname+'" and Venue="' + venue + '" and Eventdate="'+eventdate+'"' 
    SQLA = 'DELETE FROM customertable.attendees where Eventname="'+eventname+'" and Venue="' + venue + '" and Eventdate="'+eventdate+'"' 
    query_job0 = bg_client.query(SQL0) 
    query_jobA = bg_client.query(SQLA) 
    

def check_data(eventname,venue,eventdate,bg_client):    
    if os.path.isfile("/tmp/temp.csv"):
        os.remove("/tmp/temp.csv")
    file='output.csv'
    input_bucket='csv-output-bucket'
    client = storage.Client()
    bucket = client.get_bucket(input_bucket)
    blob = bucket.blob(file)
    with open("/tmp/temp.csv", "wb") as file_obj:
        blob.download_to_file(file_obj) 
    list1=[]
    email=''
    SQL3= 'SELECT Email_Address FROM customertable.salesforce WHERE '
        
    with open("/tmp/temp.csv") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:   #process column names
                if(re.search('Header does not have',row[1])):             #search error message
                    err="Error: " + row[1] #not right format
                    return err
                line_count = 1
            else:
                if(email!=row[0]):   #take care of duplicates
                    if (line_count > 1): #add commas and ors if not first row
                        SQL3=SQL3+' OR '
                    SQL3=SQL3+'Email_Address= "'+ row[2] + '" ' 
                    email=row[0]
                list1.append((row[0],row[1],row[2]))              

        query_job3 = bg_client.query(SQL3)  # search salesforce database to see if emails are there.
        in_salesforce=[]
        for row in query_job3:
            in_salesforce.append(row[0])
        return in_salesforce, list1

def insert(eventname,venue,eventdate,bg_client,in_salesforce,attendees):
    dateTimeObj = str(datetime.now())
    SQL='INSERT INTO customertable.attendees (Email, First_name, Last_name, Eventname, Venue, Eventdate, Datestamp, Is_salesforce, Guests) VALUES '
    SQL2= 'INSERT INTO customertable.events (Eventname, Venue, Eventdate, Datestamp, Attendance) VALUES '
    line_count = 0
    email=""
    for row2 in attendees:
        if(email!=row2[2]):   #take care of duplicates
            if (line_count > 0): #add commas and ors if not first row
                SQL=SQL+" , "
            guestcount=0
            guests=str(guestcount)
            sf = 'FALSE'  #boolean to show if email is in Salesforce database table
            if row2[2] in in_salesforce:
                sf='TRUE'
            SQL = SQL+'("'+row2[2]+'", "'+row2[0]+'", "'+row2[1]+'", "'+eventname+'", "'+venue+'", "'+eventdate+'", "'+dateTimeObj+'",'+sf+','+guests+')'
            email=row2[2]
            line_count += 1
        else:
            previous_count=str(guestcount)
            guestcount +=1    
            present_count=str(guestcount)
            SQL= re.sub(previous_count+'\)$', present_count+')', SQL) 
            line_count +=1     
    attendance=str(line_count)
    SQL2=SQL2+'("'+eventname+'","'+venue+'","'+eventdate+'","'+dateTimeObj+'",'+attendance+')'  #add records to events update statement.    
    query_job = bg_client.query(SQL)  #insert into attendees table
    query_job2 = bg_client.query(SQL2)  #insert into events table
    return '<a href="https://storage.cloud.google.com/csv-output-bucket/output.csv">Download</a>'


