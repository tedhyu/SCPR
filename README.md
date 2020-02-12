# Audience Pulse

Powering Southern California Public Radio's audience data.

[Link](#) to your presentation.

<hr/>

## How to install and get it up and running
firebase:
index.html - Firebase code that includes user interface.  This allows the user to upload a file and select from the various events listed.  Links to google cloud function (upload_confirm)
index.js - Firebase credentials (omitted)

Google cloud function:
requirements.txt - Configuration for main.py
upload_confirm:  Google cloud function that serves as a target page for index.html.  This page does SQL statements into BigQuery Table.  The SQL statements include:
1)  Query to see if the event exists in the database
2)  Enter new event data into the attendance table.
3)  Enter the attendance data into the attendance table.

csv_convert:  Processes the CSV in the csv-input-bucket and changes it into a three column format and copies new csv "output.csv" into csv-output-bucket

<hr/>

## Introduction

## Architecture

## Dataset

## Engineering challenges

## Trade-offs