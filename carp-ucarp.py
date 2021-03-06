#!/usr/bin/env python2.7
# Author: Jamal Shahverdiev
# Date: 17.02.2017

import sys
import os
from termcolor import colored, cprint
from fabric.api import *
from fabric.tasks import execute
import getpass
import jinja2

codepath = os.getcwd()
jinjadir = codepath+'/j2temps/'
outputdir = codepath+'/outdir/'

templateLoader = jinja2.FileSystemLoader( searchpath=jinjadir )
templateEnv = jinja2.Environment( loader=templateLoader )

CVIPCONFFILE = 'c6-c7-vip-001.conf.j2'
CVIPMASTERFILE = 'c6-c7-vip-common-master.j2'
CVIPSLAVEFILE = 'c6-c7-vip-common-slave.j2'
UMASTERFILE = 'ub-int-master.j2'
USLAVEFILE = 'ub-int-slave.j2'

tempcvipconf = templateEnv.get_template( CVIPCONFFILE )
tempcvipmaster = templateEnv.get_template( CVIPMASTERFILE )
tempcvipslave = templateEnv.get_template( CVIPSLAVEFILE )
tempumaster = templateEnv.get_template( UMASTERFILE )
tempuslave = templateEnv.get_template( USLAVEFILE )

ipadd = colored('IP address', 'green', attrs=['bold', 'underline'])
username = colored('username', 'green', attrs=['bold', 'underline'])
password = colored('password', 'magenta', attrs=['bold', 'underline'])
successfully = colored('successfully', 'green', attrs=['bold', 'underline'])
centosi = colored('CentOS', 'yellow', attrs=['bold', 'underline'])
freebsd = colored('FreeBSD', 'yellow', attrs=['bold', 'underline'])
ubuntu = colored('Ubuntu', 'yellow', attrs=['bold', 'underline'])
enter = colored('Enter', 'cyan', attrs=['bold', 'underline'])
server = colored('server', 'cyan', attrs=['bold', 'underline'])


def tempcreator(gncard, ipaddress, gateip, virtualip, carppass):
    tempVars = { "gncard" : gncard,
            "ipaddress" : ipaddress,
            "gateip" : gateip,
            "virtualip": virtualip,
            "carppass": carppass,
            }

    outcvipcTxt = tempcvipconf.render( tempVars )
    outcvipmTxt = tempcvipmaster.render( tempVars )
    outcvipsTxt = tempcvipslave.render( tempVars )
    outumasTxt = tempumaster.render( tempVars )
    outuslaTxt = tempuslave.render( tempVars )

    with open(outputdir+'vip-001.conf', 'wb') as outcvipvhid:
        outcvipvhid.write(outcvipcTxt)

    with open(outputdir+'vip-common-master.conf', 'wb') as outcvipm:
        outcvipm.write(outcvipmTxt)

    with open(outputdir+'vip-common-slave.conf', 'wb') as outcvips:
        outcvips.write(outcvipsTxt)

    with open(outputdir+'master-interfaces', 'wb') as outumas:
        outumas.write(outumasTxt)

    with open(outputdir+'slave-interfaces', 'wb') as outusla:
        outusla.write(outuslaTxt)


def variables():
    global dgsubnet
    dgsubnet = run('netstat -rn | grep UG | grep -v \'lo0\' | awk \'{ print $2 }\' | cut -f1,2,3 -d\'.\'')
    global gncard
    gncard = run('netstat -rn | grep UG | grep -v \'lo0\' | awk \'{ print $NF }\'')
    global gateip
    gateip = run('netstat -rn | awk \'{ print $2 }\' | grep '+dgsubnet+'')
    global ipaddress
    ipaddress = run('ifconfig | grep '+dgsubnet+' | awk \'{ print $2 }\' | cut -f2 -d\':\'')

env.roledefs = {
        'hosts': [str(raw_input('Please enter master '+ipadd+': ')), str(raw_input('Please enter slave '+ipadd+': '))]
        }

carpnodes = { "master" : env.roledefs['hosts'][0], "slave" : env.roledefs['hosts'][1] }


env.user = raw_input('Please '+enter+' '+username+' for UNIX/Linux '+server+': ')
env.password = getpass.getpass('Please '+enter+' '+password+' for UNIX/Linux '+server+': ')
virtualip = raw_input('Please '+enter+' virtual '+ipadd+' for CARP/UCARP: ')
carppass = raw_input('Please '+enter+' '+password+' to crypt CARP/UCARP traffic: ')


with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
    env.host_string = env.roledefs['hosts'][0]
    masterostype = run('uname -s')
    masterosname = run('cat /etc/issue | grep -v \'^$\' | head -n1 | awk \'{ print $1 }\'')
    mgncard = run('netstat -rn | grep UG | grep -v \'lo0\' | grep -o \'[^ ]*$\'')

with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
    env.host_string = env.roledefs['hosts'][1]
    slaveostype = run('uname -s')
    slaveosname = run('cat /etc/issue | grep -v \'^$\' | head -n1 | awk \'{ print $1 }\'')
    sgncard = run('netstat -rn | grep UG | grep -v \'lo0\' | grep -o \'[^ ]*$\'')

def different_oss():
    print('OS types are different between master and slave. Please choose identical operating systems!')
    sys.exit()


def linux_ucarp_installer(installer):

    for server in env.roledefs['hosts']:
        env.host_string = server

        with settings(hide('warnings', 'running', 'stdout', 'stderr'),warn_only=True):
            run(''+installer+' update -y ; '+installer+' upgrade -y')
            run(''+installer+' install -y epel-release')
            run(''+installer+' install -y net-tools bind-utils')
            run(''+installer+' install -y ucarp')


def bsd_ucarp_installer():

    for server in env.roledefs['hosts']:
        env.host_string = server

        with settings(hide('warnings', 'running', 'stdout', 'stderr'),warn_only=True):
            run('echo \'carp_load="YES"\' >> /boot/loader.conf')
            run('kldload carp')


def bsd_ms_config(gncard, carppass, virtualip, indexid):

    with settings(hide('warnings', 'running', 'stdout', 'stderr'),warn_only=True):
        env.host_string = env.roledefs['hosts'][indexid]

        if indexid == 0:
            run('echo \'ifconfig_'+gncard+'_alias0="inet vhid 1 pass '+carppass+' alias '+virtualip+'/32"\' >> /etc/rc.conf')
        elif indexid == 1:
            run('echo \'ifconfig_'+gncard+'_alias0="inet vhid 1 advskew 100 pass '+carppass+' alias '+virtualip+'/32"\' >> /etc/rc.conf')
        else:
            print('You have only 2 servers ...')

        run('/etc/rc.d/netif restart && /etc/rc.d/routing restart')
        modname = run('kldstat | grep carp | grep -o \'[^ ]*$\'')
        vipname = run('ifconfig | grep \'inet \' | grep '+virtualip+' | awk \'{ print $2 }\'')
        checkstfile = run('cat /etc/rc.conf | grep '+virtualip+' | grep -o \'[^ ]*$\' | cut -f1 -d\'/\'')

        if indexid == 0 and modname == 'carp.ko' and vipname == virtualip:
            print('Master server '+successfully+' configured!!!')
        elif indexid == 1 and modname == 'carp.ko' and checkstfile == virtualip:
            print('Slave server '+successfully+' configured!!!')


def process_check(nodename):
    processid = run('ps waux| grep ucarp | grep -v grep | awk \'{ print $11 }\'')

    if processid == '/usr/sbin/ucarp':
        print(''+nodename+': Ucarp '+successfully+' configured!')


def ubuntu_config(nodeid, filename, nodename):

    with settings(hide('warnings', 'running', 'stdout', 'stderr'),warn_only=True):
        env.host_string = env.roledefs['hosts'][nodeid]
        variables()
        tempcreator(gncard, ipaddress, gateip, virtualip, carppass)
        put(outputdir+filename, '/etc/network/interfaces')
        run('ifdown -a && ifup -a')
        process_check(nodename)


def centos_config(nodeid, nodename):

    with settings(hide('warnings', 'running', 'stdout', 'stderr'),warn_only=True):
        env.host_string = env.roledefs['hosts'][nodeid]
        variables()
        tempcreator(gncard, ipaddress, gateip, virtualip, carppass)
        put(outputdir+'vip-001.conf', '/etc/ucarp/')
        put(outputdir+'vip-common-'+nodename+'.conf',  '/etc/ucarp/vip-common.conf')

        if masterosname == '\S':
            run('systemctl start NetworkManager ; systemctl enable NetworkManager')
            run('sed -i \'s/${NETWORKING}/"${NETWORKING}"/g\' /usr/libexec/ucarp/ucarp')
            run('systemctl start ucarp@vip-001 ; systemctl enable ucarp@vip-001.service')

        elif masterosname == 'CentOS':
            run('service ucarp start ; chkconfig --level 0123456 ucarp on')

        process_check(nodename)


if masterostype == 'Linux' and masterosname == 'Ubuntu' and slaveostype == 'Linux' and slaveosname == 'Ubuntu':
    print('Both servers are Linux Ubuntu ...')
    print('Installation and configuration of Ucarp is in progress ...')
    linux_ucarp_installer('apt-get')
    ubuntu_config(0, 'master-interfaces', 'master')
    ubuntu_config(1, 'slave-interfaces', 'slave')

elif masterostype == 'Linux' and masterosname == 'CentOS' and slaveostype == 'Linux' and slaveosname == 'CentOS':
    print('Both servers are Linux CentOS6 ...')
    print('Installation and configuration of Ucarp is in progress ...')
    linux_ucarp_installer('yum')
    centos_config(0, 'master')
    centos_config(1, 'slave')

elif masterostype == 'Linux' and masterosname == '\S' and slaveostype == 'Linux' and slaveosname == '\S':
    print('Both servers are Linux CentOS7 ...')
    print('Installation and configuration of Ucarp is in progress ...')
    linux_ucarp_installer('yum')
    centos_config(0, 'master')
    centos_config(1, 'slave')

elif masterostype == 'FreeBSD' and slaveostype == 'FreeBSD':
    print('Both servers are FreeBSD ... ')
    print('Installation and configuration of Ucarp is in progress ...')
    bsd_ucarp_installer()
    bsd_ms_config(mgncard, carppass, virtualip, 0)
    bsd_ms_config(sgncard, carppass, virtualip, 1)

else:
    different_oss()
