#This is a backup controller for ESXI, it takes one argument being the name of a VM
#It will then search through the defined Hosts and copy the contents of that VM from one datastore to another
#The first copy will take much longer than the next ones. This is because First the contents are
#copied using RSync to setup the necessary directories as well as to bring over the VMX file and anything else
#The name of this VM is then written into the syncedVMs.csv file so it doesn't get RSynced again. If you wish to force a sync,
#simply remove it from this file. To use RSync you must install it on one of your hosts. To do so extract the esxiRsync.tar.gz file on the host
#tar xvf esxiRsync.tar.gz and then copy it to /bin/ then mc /bin/rsync-static /bin/rsync
#This doesn't appear to be a persistent procedure so it may need to be done after every reboot of the host
#The next copies are done using vmfstools which runs much quicker and simply copies the .vmdk files
#
#For this to run properly you must be able to ssh from the controller machine to the esxi hosts without a password
#This can be done by copying the public certificate to the ESXI hosts.
#one the controller - scp /root/.ssh/id_rsa.pub root@esxihost:/etc/ssh/
#on the host - cat /etc/ssh/id_rsa.pub >> /etc/ssh/know_hosts/authorized_keys
#
#Upon starting and finishing the backup this script will send out emails
#This function requires installing the smtplib library as well as setting up the proper email in the emailNotification function
#
#This program will create many more custom .py files. These can be deleted after each run, or left as they will be overwritten
#many times. These files will be used with Fabric which is the ssh tool being used
#
#A two minute sleep is used after sending the power off command to a VM so that there is time for it to power off before starting the copy
#If you think this isn't enough, it is in the powerOffVM function. It could be improved using the getState command.
#
#Jeremiah Butler

import subprocess, os, smtplib, time, sys

vmList = []
vmNames = []

def getVMsFromHost(hostIP):
    w = open('getVMs.py','w')
    w.write("from fabric.api import run, env\n")
    w.write("host = 'root@"+hostIP+"'\n")
    w.write("env.shell = '/bin/sh -c'\n")
    w.write("env.hosts = [host]\n")
    w.write("def getVmList():\n")
    w.write("\trun('vim-cmd vmsvc/getallvms')\n")
    w.close()
    getVmList = subprocess.Popen(['fab', '-f', 'getVMs.py', 'getVmList'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    vmListOutput = getVmList.communicate()
    lineByLine = vmListOutput[0].split('out: ')
    vmID = ''
    count = 0
    for i in lineByLine:
        if count > 1 and count < len(lineByLine)-1:
            splitAgain = i.split(' ')
            noNum = i.split(splitAgain[0])
            noSpaces = "".join(noNum[1].split())
            vmName = noSpaces.split('[')
            if len(vmName) < 2:
                continue
            vmDatastore = vmName[1].split(']')
            unregName = vmDatastore[1].split('/')
            vmList.append([vmName[0],splitAgain[0], vmDatastore[0], unregName[0], hostIP])
            vmNames.append(vmName[0])
        count += 1
    return

def getVmNames(hosts):
    for host in hosts:
        getVMsFromHost(host)
    return vmNames

def emailNotification(name, state):
    gmail_user = #Email for notifications
    gmail_pwd = #Email Password
    FROM = #same as gmail_user
    TO = ["""who to send emails too, must be a list"""]
    SUBJECT = ""
    TEXT = ""
    if (int(state) == 0):
        SUBJECT = "Backup Started"
        TEXT = "Your backup of "+name+" has started!"
    else:
        SUBJECT = "Backup Complete"
        TEXT = "Your backup of "+name+" is complete!"
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

def turnOnVM(name):
    vmId = ""
    host = ""
    for i in vmList:
        if (i[0] == name):
            print 'VMID = ' + str(i[1])
            vmId = i[1]
            host = i[4]
    w = open('powerOn.py','w')
    w.write("from fabric.api import run, env\n")
    w.write("esxiHost = 'root@"+host+"'\n")
    w.write("env.shell = '/bin/sh -c'\n")
    w.write("env.hosts = [esxiHost]\n")
    w.write("def powerOnVm():\n")
    w.write("\trun('vim-cmd vmsvc/power.on "+vmId+"')\n")
    w.close()
    powerOnVM = subprocess.Popen(['fab', '-f', 'powerOn.py', 'powerOnVm'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    powerOnOutput = powerOnVM.communicate()
    print powerOnOutput

def powerOffVM(name):
    vmId = ""
    host = ""
    for i in vmList:
        if (i[0] == name):
            print 'VMID = ' + str(i[1])
            vmId = i[1]
            host = i[4]
    w = open('shutdown.py','w')
    w.write("from fabric.api import run, env\n")
    w.write("esxiHost = 'root@"+host+"'\n")
    w.write("env.shell = '/bin/sh -c'\n")
    w.write("env.hosts = [esxiHost]\n")
    w.write("def shutdownVm():\n")
    w.write("\trun('vim-cmd vmsvc/power.shutdown "+vmId+"')\n")
    w.close()
    shutDownVM = subprocess.Popen(['fab', '-f', 'shutdown.py', 'shutdownVm'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    shutdownOutput = shutDownVM.communicate()
    print shutdownOutput
    print "VM Powering off, sleeping for 2 minutes before starting clone"
    time.sleep(120)

def getDisks(name):
    host = ""
    unregName = ""
    for i in vmList:
        if (i[0] == name):
            host = i[4]
            unregName = i[3]
    w = open('getDisks.py','w')
    w.write("from fabric.api import run, env\n")
    w.write("esxiHost = 'root@"+host+"'\n")
    w.write("env.shell = '/bin/sh -c'\n")
    w.write("env.hosts = [esxiHost]\n")
    w.write("def getDisks():\n")
    w.write("""\trun("ls /vmfs/volumes/ssdISCSI/"""+unregName+"""/"""+unregName+"""*.vmdk")\n""")
    w.close()
    disks = subprocess.Popen(['fab', '-f', 'getDisks.py', 'getDisks'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    disksOutput = disks.communicate()
    splitString = unregName+'/'+unregName
    crapDiskList = disksOutput[0].split(splitString)
    count = 0
    diskList = []
    for i in crapDiskList:
        if count > 1 and count < len(crapDiskList):
            disk = i.split('[')
            noSpaceDiskName = "".join(disk[0].split()).strip('\x1b')
            if not ("-ctk" in noSpaceDiskName or "-flat" in noSpaceDiskName or "-delta" in noSpaceDiskName):
                diskList.append(str(noSpaceDiskName))
        count += 1
    return diskList

def cloneVM(name):
    vmId = ""
    host = ""
    unregName = ""
    for i in vmList:
        if (i[0] == name):
            vmId = i[1]
            host = i[4]
            unregName = i[3]
    print "Getting names of all disks for VM "+name
    disks = getDisks(name)
    print disks
    print "Starting clone of "+name
    for i in disks:
        print "Clone "+i+" starting"
        w = open('clone.py','w')
        w.write("from fabric.api import run, env\n")
        w.write("esxiHost = 'root@"+host+"'\n")
        w.write("env.shell = '/bin/sh -c'\n")
        w.write("env.hosts = [esxiHost]\n")
        w.write("def clone():\n")
        w.write("""\trun("vmkfstools -U '/vmfs/volumes/backupISCSI/"""+unregName+"""/"""+unregName+i+"""'")\n""")
        w.write("""\trun("vmkfstools -i '/vmfs/volumes/ssdISCSI/"""+unregName+"""/"""+unregName+i+"""' '/vmfs/volumes/backupISCSI/"""+unregName+"""/"""+unregName+i+"""' -d thin -a buslogic")\n""")
        w.close()
        cloneVM = subprocess.Popen(['fab', '-f', 'clone.py', 'clone'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        cloneOutput = cloneVM.communicate()
        print cloneOutput
        print "Clone "+i+" complete"
    print "CLONE "+name+" COMPLETE!"

def backupVM(name):
    vmId = ""
    host = ""
    unregName = ""
    for i in vmList:
        if (i[0] == name):
            vmId = i[1]
            host = i[4]
            unregName = i[3]
    vms = []
    r = open('syncedVMs.csv','r+')
    vmString = r.readline()
    vms = vmString.split(', ')
    print "existing synced VMs "
    print vms
    if not any(name in s for s in vms):
        print "Syncing "+name+" to vms"
        w = open('backup.py','w')
        w.write("from fabric.api import run, env\n")
        w.write("esxiHost = 'root@"""IP OF HOST WITH RSync"""'\n")
        w.write("env.shell = '/bin/sh -c'\n")
        w.write("env.hosts = [esxiHost]\n")
        w.write("def backup():\n")
        w.write("\trun('rsync -rhI /vmfs/volumes/ssdISCSI/"+unregName+" /vmfs/volumes/backupISCSI/')\n")
        w.close()
        backupVM = subprocess.Popen(['fab', '-f', 'backup.py', 'backup'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        backupOutput = backupVM.communicate()
        print backupOutput
        vms.append(name)
        r.write(str(vms).strip("[]").replace("'",''))
        print name+" added to synced vms"
        print vms
    r.close()
    print "RSync COMPLETE!"

def runBackup(vmToBackup):
    hosts = ["""IPS GO HERE"""]
    for i in hosts:
        getVMsFromHost(i)
    emailNotification(vmToBackup, 0)
    powerOffVM(vmToBackup)
    backupVM(vmToBackup)
    cloneVM(vmToBackup)
    turnOnVM(vmToBackup)
    emailNotification(vmToBackup, 1)
    return