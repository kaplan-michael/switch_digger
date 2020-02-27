#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Made by Michael Kaplan
#Inspired by https://github.com/edikmkoyan/portmatrix
#Before running install requirements.txt


######### Import Libraries ######################################################
import configparser, os, datetime
from pysnmp.hlapi import bulkCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
from tendo import singleton
import requests
import time
import psycopg2
import sys
from mac_vendor_lookup import MacLookup


print ("import ok")
######### Define functions #######################################################

def getvendor(macaddr):
    try:
        maclook = MacLookup()
        maclook.load_vendors() 
        vendor = (maclook.lookup(macaddr))  
        return vendor
    except:
        pass 
    
#def getvendor(macaddr):
#    vendor = requests.get(url="http://api.macvendors.com/%s" % macaddr)
#    time.sleep(1.2)
#    return vendor.text

def cleardatamac():
    postgres_cursor = postgres_conn.cursor()
    postgres_cursor.execute("DELETE FROM maclist *") 
    postgres_conn.commit() 
    postgres_cursor.close()

def cleardataarp():
    postgres_cursor = postgres_conn.cursor()
    postgres_cursor.execute("DELETE FROM arplist *") 
    postgres_conn.commit() 
    postgres_cursor.close()

def dbmac(switch,port,mac,vendor):
    postgres_cursor = postgres_conn.cursor()
    postgres_cursor.execute("INSERT INTO maclist (switch, port, mac, vendor) VALUES (%s, %s, %s, %s) ON CONFLICT(switch, port)  DO UPDATE SET mac = %s , vendor = %s ",
     (switch, port, mac, vendor,mac, vendor))
    postgres_conn.commit() 
    postgres_cursor.close()

def dbarp(ip,mac):
    postgres_cursor = postgres_conn.cursor()
    postgres_cursor.execute("INSERT INTO arplist (ip, mac) VALUES (%s, %s) ON CONFLICT(mac)  DO UPDATE SET mac = %s ",
     (ip, mac, mac))
    postgres_conn.commit() 
    postgres_cursor.close()

def dbfinal(switch,port,mac,vendor,ip):
    
    postgres_cursor = postgres_conn.cursor()
    postgres_cursor.execute ("INSERT INTO devices (switch, port, mac, vendor, ip, updated) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT(switch, port)  DO UPDATE SET mac = %s , vendor = %s , ip = %s , updated = %s ",
     (switch, port, mac, vendor, ip,  datetime.datetime.utcnow(),mac, vendor, ip,  datetime.datetime.utcnow()))

    
    postgres_conn.commit() 
    postgres_cursor.close()


#####################################################################################
#
#                      Define Variables section
#
#####################################################################################

######### Accessing the configuration file #######################################
config = configparser.RawConfigParser()
config.read('./main.cfg')
sections = config.sections()



######## Edit PGSQL connection Values Before Use #####################################


dbhost = config.get('Database','dbhost')
database = config.get('Database','database') 
dbuser = config.get('Database','dbuser')
dbpassword = config.get('Database','dbpassword')


######## Edit Gateway Values Before Use ##############################################
GWIPAddress = config.get('Gateway','IPAddress')
GWcommunityString = config.get('Gateway','communityString')
GWsnmpPort = config.get('Gateway','snmpPort')



#####################################################################################
#
#                      Connect to DB 
#
#####################################################################################
postgres_conn = psycopg2.connect(host = dbhost,database = database, user= dbuser, password = dbpassword)

######### Enforce one running instance ###########################################
me = singleton.SingleInstance()




#####################################################################################
#
#                      Get MAC table  from switches Section 
#
#####################################################################################




#cleardatamac()


######### Get Mac from switches  ##################################################
for currentsection in sections[2:]:
    IPAddress = config.get(currentsection, 'IPAddress')
    communityString = config.get(currentsection, 'communityString')
    snmpPort = config.get(currentsection, 'snmpPort')
    UplinkPorts = config.get(currentsection, 'UplinkPorts')
    ApPorts = config.get(currentsection, 'ApPorts')
    for (errorIndication,
             errorStatus,
             errorIndex,
             varBinds) in bulkCmd(SnmpEngine(),
                              CommunityData(communityString),
                              UdpTransportTarget((IPAddress, snmpPort)),
                              ContextData(),
                              0, 25,
                              ObjectType(ObjectIdentity('BRIDGE-MIB', 'dot1dTpFdbPort')),
                              lexicographicMode=False,
                              lookupMib=True):
        if errorIndication:
                Exception(errorIndication)
        elif errorStatus:
                Exception(errorStatus)
#check varbind contents and filter if multiple IPS on port => Uplink
        else:
                for varBind in varBinds: 
                    port = varBind[1] 
                    
                    if  len(str(port)) == 3:
                        portlist = list(str(port))
                        port = (portlist[0]  + "/" + portlist[1] + portlist[2])
                    
                    if  port == "0":
                        port = "CPU"
                    macAddress = varBind[0].prettyPrint()[-19:] 
                    macAddress = macAddress.replace('"', '') 
                    macAddress = macAddress.replace(':', '') 
                    vendor = getvendor(macAddress)
                    #vendor = "test vendor"


                    excluded = (UplinkPorts + ApPorts)
                    if str(port) in  excluded:
                        continue
                    
                    
                    
                    
                    
                    print ("    switch:    " + str(currentsection) + "    port:    " + str(port) +
                    "    mac:    " + str(macAddress) + "    vendor:    " + str(vendor))


######### Open PGSQL cursor and insert data in loop from gateway ######################
                    dbmac(str(currentsection),str(port), str(macAddress), str(vendor))
                    
                    
print ("Inserted MACLIST")


#####################################################################################
#
#                      Get ARP table from gateway Section 
#
#####################################################################################



#cleardataarp()



######### Get ARP table from gateway ##################################################
for (errorIndication,
     errorStatus,
     errorIndex,
     varBindTable) in bulkCmd(SnmpEngine(),
                              CommunityData(GWcommunityString),
                              UdpTransportTarget((GWIPAddress, GWsnmpPort)),
                              ContextData(),
                              0, 25,
                              ObjectType(ObjectIdentity('IP-MIB', 'ipNetToPhysicalPhysAddress')),
                              lexicographicMode=False,
                              lookupMib=True):

    if errorIndication:
        Exception(errorIndication)
    elif errorStatus:
        Exception(errorStatus)
    else:
        for varBind in varBindTable:
            #print(' = '.join([x.prettyPrint() for x in varBind]))
            ipAddress_orig = varBind[0].prettyPrint()
            ipAddress = ipAddress_orig.replace('"', '')
            ipAddress = ipAddress.replace('IP-MIB::ipNetToPhysicalPhysAddress.6.ipv4.', '')
            ipAddress = ipAddress.replace('IP-MIB::ipNetToPhysicalPhysAddress.8.ipv4.', '')
            ipAddress = ipAddress.replace('IP-MIB::ipNetToPhysicalPhysAddress.9.ipv4.', '')
            ipAddress = ipAddress.replace('IP-MIB::ipNetToPhysicalPhysAddress.25.ipv4.', '')
            ipAddress = ipAddress.replace('IP-MIB::ipNetToPhysicalPhysAddress.26.ipv4.', '')
            ipAddress = ipAddress.replace('IP-MIB::ipNetToPhysicalPhysAddress.7.ipv4.', '')

            
            macAddress_ARP = varBind[1].prettyPrint()[-19:] 
            macAddress_ARP = macAddress_ARP.replace('"', '')
            macAddress_ARP = macAddress_ARP.replace(':', '')
            
            print ("    IP:    " + str(ipAddress) +  "    mac:    " + str(macAddress_ARP))
            dbarp(str(ipAddress), str(macAddress_ARP))
print ("Inserted ARP")                   



#####################################################################################
#
#                      Combine Mac address with IPaddress and put into DB 
#
#####################################################################################


postgres_cursor = postgres_conn.cursor()
postgres_cursor.execute("SELECT * from maclist")
maclist = postgres_cursor.fetchall()


for row in maclist:
    switch = row[0]
    port = row[1]
    mac = row[2]
    vendor = row[3]
    sql = "SELECT ip FROM arplist WHERE mac = '%s'   " %mac
    postgres_cursor.execute(sql)
    ip = postgres_cursor.fetchone()    
    if ip is None:
        ip = ("NOT FOUND")
    dbfinal(switch, port, mac, vendor, ip)



    print  ("port:  ", port, "mac:   ", mac, "ip:    ", ip)                    
postgres_conn.close()
print (" Finished")                   
