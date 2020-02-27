Tool for maping connected device to switch ports with IP
Does "OK" maps MAC address to switch port finds vendor and finds its IP
duplicate results because of UPLINK ports. Still working on sollution

uses SNMP with RFC MIBS
Tested with Zyxel switches
any testing or help is apreciated 


HOW TO RUN?
1. Install requirements 

`pip3 install -r requirements.txt`

2. Install and setup postgres 
3. Create postgres database 


`CREATE TABLE maclist(switch text, port text, mac text, vendor text);`

`CREATE TABLE arplist(ip text, mac text UNIQUE);`

`CREATE TABLE devices(switch text, port text, mac text, vendor text, ip text, updated date);`

`CREATE UNIQUE INDEX unique_index ON devices (switch, port);`

`CREATE UNIQUE INDEX unique_index ON maclist (switch, port);`

4. Edit postgress connection variables at the beging of the script
5. Edit main.cfg


Web Gui for easy searching is planned

WORK IN PROGRESS
Inspired by https://github.com/edikmkoyan/portmatrix
Made by Michael Kaplan

