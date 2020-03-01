# Audience Pulse

Powering Public Radio's audience data.

https://docs.google.com/presentation/d/1ETRXEolbi1zsujgT4A_xpSHWsWtPfVPXFJIyV4LPVas/edit#slide=id.p

<hr/>

## How to install and get it up and running

Requirements:  Google Cloud Account

1)  Firebase:  Set up index.html on Firebase
2)  Google Cloud Function:  Set up csv_convert and upload_confirm
3)  Google Cloud Storage:  Set up buckets csv-output-bucket and csv-input-bucket
4)  BigQuery:  Set up Three BigQuery Tables:
		a)  customertable.salesforce - This is a BigQuery table imported from Salesforce.  It has one column needed which is Email_address.
		b)  customertable.attendees - Email(String), First_name(string), Last_name(string), Guests(integer), Is_salesforce(boolean), Datestamp(timestamp), Eventname(string), Venue(String), Eventdate(string)
                c)  customertable.events - Eventname(string), Venue(string), Eventdate(string), Datestamp(timestamp), Attendance(integer)
<hr/>

## Introduction
This app establishes a connection between venue and salesforce data, which were previously not linked.  It enters into two new tables:  attendees and events.
![Menu](https://imgur.com/jjHN3xY.png)

## Architecture
Data Pipeline:  
![Pipeline](https://imgur.com/PIiQevq.png)

## Dataset
CSV file that contains minimum three headers:  email, first name, and last name.  
Two salesforce table in BigQuery:
    Attendees:  Email, First_name, Last_name, Guests, Is_salesforce, Datestamp, Eventname, Venue, Eventdate
    Events:  Eventname, Venue, Eventdate, Datestamp, Attendance

## Engineering challenges
Multiple schemas of CSV files.  Organizing BigQuery tables in a format that is easily readable and logical.  Error handling algorithem.  
Error Handling Logic:
![Error](https://imgur.com/fWY7Drk.png)
