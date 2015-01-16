#This is a web controller for the backup controller. It is a useful tool to see what python processes are running on the controller
#It requires the web.py library to be installed. pip install web.py is the recommended method
#For this to run correctly you must also have a templates folder in the same directory, which contains your base.html file
#
#If the controller process is called using this method, you will also be emailed an output from that process which is useful for unsupervised backups.
#The scheduler is being implemented now
#
#Jeremiah Butler

import web, json
from web import form
from datetime import datetime
import subprocess, os, smtplib, threading
from controller import getVmNames, runBackup

render = web.template.render('templates/')

urls = ('/', 'index',
        '/getRunning', 'getRunning',
        '/getVMs', 'getVMs',
        '/backup', 'backup',
        '/schedule', 'schedule')
app = web.application(urls, globals())

schedulerLoop = True
backupLoop = True
global trigger
trigger = False
global vmList
vmList = []

hosts = ["""IPS GO HERE"""]
vmList = getVmNames(hosts)

def scheduler():
    import time
    global trigger
    print "scheduler started"
    currentTime = datetime.now()
    currentDay = currentTime.weekday()
    print "Scheduler year = "+str(currentTime.year)
    print "Scheduler month = "+str(currentTime.month)
    print "Scheduler day = "+str(currentTime.day)
    while schedulerLoop:
        r = open('schedule.csv','r')
        schedule = json.load(r)
        r.close()
        currentTime = datetime.now()
        currentDay = currentTime.weekday()
        if(currentDay == 0):
            print "Today is Monday!"
        if(currentDay == 1):
            print "Today is Tuesday!"
        if(currentDay == 2):
            print "Today is Wednesday!"
        if(currentDay == 3):
            print "Today is Thursday!"
        if(currentDay == 4):
            print "Today is Friday!"
        if(currentDay == 5):
            print "Today is Saturday!"
        if(currentDay == 6):
            print "Today is Sunday!"
        #print scheduledTasks
        for i in schedule:
            print "Date = "+str(i[1])
            date = i[1]
            month = int(date[1])
            day = int(date[2])
            schTime = str(i[2])
            timeSplit = schTime.split(':')
            hour = int(timeSplit[0])
            min = int(timeSplit[1])
            if (date[0] == str(currentTime.year)):
                #print "Correct Year!"
                if(str(month) == str(currentTime.month)):
                    #print "Correct Month!"
                    if(str(day) == str(currentTime.day)):
                        #print "We're on the right day!"
                        if(currentTime.hour == hour):
                            #print "In the right hour!"
                            if(currentTime.minute == min):
                                print "Trigger Backup!"
                                w = open('currentBackup.txt','w')
                                w.write(i[0])
                                w.close()
                                trigger =True
        print "Scheduler time = "
        print currentTime
        time.sleep(60)

schedulerThread = threading.Thread(target=scheduler)

def backupWaiting():
    import time, os, subprocess
    global trigger
    while backupLoop:
        if trigger:
            r = open('currentBackup.txt', 'r')
            name = r.readline()
            r.close()
            
            defString = "runBackup:"+name
            print "Backup! "+ name
            backupVM = subprocess.Popen(['fab', '-f', 'controller.py', defString], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            backupOutput = backupVM.communicate()
            emailNotification(backupOutput)
            trigger = False
            os.remove('currentBackup.txt')
        else:
            time.sleep(10)

backupThread = threading.Thread(target=backupWaiting)

def emailNotification(output):
    gmail_user = #Email for notifications
    gmail_pwd = #Email Password
    FROM = #same as gmail_user
    TO = ["""who to send emails too, must be a list"""]
    SUBJECT = "Output from Backup"
    TEXT = output
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s""" % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print "Successfully sent mail!"
    except:
        print "Failed to send mail!"

class index:
    def GET(self):
        return render.base()

class getRunning:
    def POST(self):
        web.header('Content-Type', 'application/json')
        ps = subprocess.Popen(['ps', '-ef'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        pythonPS = subprocess.Popen(['grep', 'python'], stdin=ps.stdout, stdout=subprocess.PIPE)
        ps.stdout.close()
        running = pythonPS.communicate()
        runString = running[0].splitlines()
        return json.dumps({'running': runString})

class getVMs:
    def POST(self):
        global vmList
        web.header('Content-Type', 'application/json')
        print vmList
        return json.dumps({'mnames': vmList})

class backup:
    def POST(self):
        machineName = web.input().name
        backup = subprocess.Popen(['python', '/root/administrator/controller.py', machineName], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        backupText = backup.communicate()
        emailNotification(backupText)

class schedule:
    def POST(self):
        scheduleDate = web.input().schDate
        scheduleTime = web.input().schTime
        scheduleName = web.input().schName
        print scheduleDate
        splitDate = str(scheduleDate).split('-')
        print scheduleTime
        print "Year = "+splitDate[0]
        print "Month = "+splitDate[1]
        print "Day = "+splitDate[2]
        toSchedule = [str(scheduleName),splitDate,scheduleTime]

        schedule = []
        r = open('schedule.csv','r')
        schedule = json.load(r)
        r.close()
        print "existing scheduled backups = "
        print schedule
        if not any(str(toSchedule) in s for s in schedule):
            print "Adding "+str(toSchedule)+" to schedule"
            w = open('schedule.csv', 'w')
            schedule.append(toSchedule)
            json.dump(schedule,w)
            print str(toSchedule)+" added to schedule"
        print schedule
        
        return

if __name__=="__main__":
    web.internalerror = web.debugerror
    schedulerThread.start()
    backupThread.start()
    app.run()
    schedulerLoop = False
    backupLoop = False