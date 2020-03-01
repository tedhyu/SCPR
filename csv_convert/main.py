from google.cloud import storage
from io import StringIO
import re 
import csv
import array as arr
import os
import requests

def main(event, context):
    """Triggered by a new file in csv-input-bucket.  Copies the bucket file to /tmp/temp.csv
    Args:  
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    file = event
    print(f"Processing file: {file['name']}.")
    print(f"Processing file: {file['bucket']}.")
    list1=[]    #list1 created from csv
    x=file['name']
    y=file['bucket']
    filename=y+'/'+x
    client = storage.Client()
    bucket = client.get_bucket('csv-input-bucket')
    blob = bucket.blob(x)
    with open("/tmp/temp.csv", "wb") as file_obj:
        blob.download_to_file(file_obj) 
    blob.delete()  #deleted the blob
    list1,Error_message=read()
    write(list1,Error_message)

def read():
    """Opens /tmp/temp.csv.  Checks for errors.  Prioritizes Buyer info but takes other info anyways if Buyer does not exist.
       Creates a list of Email, First Name, Last Name.  Creates a string of errors if file has inccorect headers.
    Args:
        None
    Returns:
        list1:  List[string]
        Error_message:  string
    """
    list1=[]    #list1 created from csv
    fn_found=0
    ln_found=0
    em_found=0
    email_num=""
    last_name=""
    first_name=""
    Error_message=""
    with open("/tmp/temp.csv") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            column=len(row)
            if line_count == 0:   #process column names
                for n in range(column):
                    lc=row[n].lower()
                    if(re.search('email',lc) and em_found==0):             #search for email in column name
                        email_num=n
                        if(re.search('buyer email',lc)):
                            em_found=1
                    if(re.search('last name',lc) and ln_found==0):         #search for last name in column name
                        last_name=n
                        if(re.search('buyer last name',lc)):
                            ln_found=1
                    if(re.search('first name',lc) and fn_found==0):        #search for first name in column name
                        first_name=n
                        if(re.search('buyer first name',lc)):
                            fn_found=1
                if (email_num==""):
                    Error_message = Error_message + "Header does not have email.  "
                if (first_name==""):
                    Error_message = Error_message + "Header does not have first name.  "
                if (last_name==""):
                    Error_message = Error_message + "Header does not have last name.  "
                if (Error_message != ""):
                    break
                line_count = 1
            else:
                if(re.search('@', row[email_num])):
                    em=re.sub(r"\s+$", "", row[email_num])  #remove extra lines at end
                    fn=re.sub(r"\s+$", "", row[first_name])
                    ln=re.sub(r"\s+$", "", row[last_name])
                    list1.append((em,fn,ln))    
    list1.sort()
    return list1,Error_message

def write(list1,Error_message):
    """Takes a list of Email, First Name, Last Name or a string of errors.  Writes the info into a storage bucket:  csv-output-bucket.
    Args:
        list1:  List[string]
        Error_message:  string
    Returns:
        None
    """
#write after accounting for all errors                
    with open('/tmp/temp2.csv', 'w', newline='') as csvfile:
        output = csv.writer(csvfile, delimiter=',')
        if (Error_message == ""):
            output.writerow(('First Name', 'Last Name', 'Email')) 
            for row2 in list1:
                output.writerow((row2[1],row2[2],row2[0]))
        else:
            output.writerow(('Error', Error_message))

    client = storage.Client()            
    bucket2 = client.get_bucket('csv-output-bucket')
    blob2 = bucket2.blob("output.csv")
    blob2.upload_from_filename("/tmp/temp2.csv")
    blob2.cache_control = "private, max-age=0"
    blob2.patch()
    


    
