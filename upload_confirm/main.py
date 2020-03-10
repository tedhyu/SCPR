import re
import csv
import flask
import urllib
from google.cloud import bigquery
from google.cloud import storage
from datetime import datetime

def main(request): 
    """Responds to any HTTP request.  Checks to see if all arguments are present.  Makes decisions based on trigger argument.
    Trigger=unknown:  Checks to see if events exists.  If it doesn't, proceed with insert.  If not, prompt user if they wish to overwrite.
    Trigger=yes:  Overwrites old data related to the event before inserting.
    Trigger=no:  Does not insert.
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

    is_salesforce,attendees,message=check_data(eventname,venue,eventdate,bg_client)  #read csv info and save to list
    if(re.search('Header does not have',message)):  #check for header error message
        return message  #return error if headers are incorrect

    if (trigger=='unknown'):
        message=event_exist(eventname,venue,eventdate,bg_client)  #check if event exists
        if message=='no event':  #event does not exist.  proceed
            return insert(eventname,venue,eventdate,bg_client,is_salesforce,attendees)       
        else:  #event exists.  Prompt user if they want to overwrite.
            return message
    elif (trigger=='yes'):
        delete_old(eventname,venue,eventdate,bg_client)#delete previous data of event selected, so it can be overwritten.
        return insert(eventname,venue,eventdate,bg_client,is_salesforce,attendees)  
    else:
        message="No new data was entered as requested."
        return message  

def event_exist(eventname,venue,eventdate,bg_client):
    """Checks to see if the event already exists and prompts the user if they wish to overwrite old event
    Args:
        eventname:  string
        venue:  string
        eventdate: string
        bg_client: BigQuery client
    Returns:
        message:  string
    """ 
    pull_past_events = 'SELECT Datestamp from customertable.events where Eventname="'+eventname+'" and Venue="' + venue + '" and Eventdate="'+eventdate+'"' 
    query_job0 = bg_client.query(pull_past_events)
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
    else:
        return 'no event'

def delete_old(eventname,venue,eventdate,bg_client):  
    """Deletes old event data from events and attendees table
    Args:
        eventname:  string
        venue:  string
        eventdate: string
        bg_client: BigQuery client
    Returns:
        NONE
    """ 
    delete_past_events = 'DELETE FROM customertable.events where Eventname="'+eventname+'" and Venue="' + venue + '" and Eventdate="'+eventdate+'"' 
    delete_past_attendees = 'DELETE FROM customertable.attendees where Eventname="'+eventname+'" and Venue="' + venue + '" and Eventdate="'+eventdate+'"' 
    query_job0 = bg_client.query(delete_past_events) 
    query_jobA = bg_client.query(delete_past_attendees) 
    
def check_data(eventname,venue,eventdate,bg_client):    
    """Reads the CSV files and checks for header errors.  Crosschecks the emails in the CSV with the Salesforce Database. 
       Returns a list of emails, first name, last name.  Returns a list of emails that are in the Salesforce database.
       If headers are not right, returns error message.
    Args:
        eventname:  string
        venue:  string
        eventdate: string
        bg_client: BigQuery client
    Returns:
        in_salesforce:  list[string]
        list1:  list[string]
        err:  string
        
    """ 
    filename='output.csv'
    input_bucket='csv-output-bucket'
    client = storage.Client()
    bucket = client.get_bucket(input_bucket)
    blob = bucket.blob(filename)
    with open("/tmp/temp.csv", "wb") as file_obj:
        blob.download_to_file(file_obj) 
    list1=[]
    email=''
    check_in_salesforce= 'SELECT Email_Address FROM customertable.salesforce WHERE '
    err=''
        
    with open("/tmp/temp.csv") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:   #process column names
                if(re.search('Header does not have',row[1])):             #search error message
                    err="Error: " + row[1] #not right format
                    return 0,0,err
                line_count += 1
            else:
                if(email!=row[0]):   #take care of duplicates
                    if (line_count > 1): #add commas and ors if not second row
                        check_in_salesforce=check_in_salesforce+' OR '
                    check_in_salesforce=check_in_salesforce+'Email_Address= "'+ row[2] + '" ' 
                    email=row[0]
                    line_count+=1
                list1.append((row[0],row[1],row[2]))              

        query_job3 = bg_client.query(check_in_salesforce)  # search salesforce database to see if emails are there.
        in_salesforce=[]
        for row in query_job3:
            in_salesforce.append(row[0])
        return in_salesforce, list1, err

def insert(eventname,venue,eventdate,bg_client,in_salesforce,attendees):
    """Inserts data into attendees and events tables.  Calculates Attendance, Guests, Is_salesforce.
    Args:
        eventname:  string
        venue:  string
        eventdate: string
        bg_client: BigQuery client
        in_salesforce:  list[string]
        attendees:  list[string]
    Returns:
        String

    """ 
    dateTimeObj = str(datetime.now())
    insert_attendees='INSERT INTO customertable.attendees (Email, First_name, Last_name, Eventname, Venue, Eventdate, Datestamp, Is_salesforce, Guests) VALUES '
    insert_event= 'INSERT INTO customertable.events (Eventname, Venue, Eventdate, Datestamp, Attendance) VALUES '
    line_count = 0
    email=""
    for row2 in attendees:
        if(email!=row2[2]):   #take care of duplicates
            if (line_count > 0): #add commas and ors if not first row
                insert_attendees=insert_attendees+" , "
            guestcount=0
            guests=str(guestcount)
            sf = 'FALSE'  #boolean to show if email is in Salesforce database table
            if row2[2] in in_salesforce:
                sf='TRUE'
            insert_attendees = insert_attendees+'("'+row2[2]+'", "'+row2[0]+'", "'+row2[1]+'", "'+eventname+'", "'+venue+'", "'+eventdate+'", "'+dateTimeObj+'",'+sf+','+guests+')'
            email=row2[2]
            line_count += 1
        else:
            previous_count=str(guestcount)
            guestcount +=1    
            present_count=str(guestcount)
            insert_attendees= re.sub(previous_count+'\)$', present_count+')', insert_attendees) 
            line_count +=1     
    attendance=str(line_count)
    insert_event= 'INSERT INTO customertable.events (Eventname, Venue, Eventdate, Datestamp, Attendance) VALUES ("'+eventname+'","'+venue+'","'+eventdate+'","'+dateTimeObj+'",'+attendance+')'  #add records to events update statement.    
    query_job = bg_client.query(insert_attendees)  #insert into attendees table
    query_job2 = bg_client.query(insert_event)  #insert into events table
    return '<a href="https://storage.cloud.google.com/csv-output-bucket/output.csv">Download</a>'



