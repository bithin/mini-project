#!/usr/bin/env python
import os
import re
import string
import subprocess
import sys
import types
import xml.dom.minidom
import shlex
import collections


try:
    from multiprocessing import Process
except ImportError:
    from threading import Thread as Process

class PortScanner(object):
    def __init__(self, nmap_search_path=('nmap','/usr/bin/nmap','/usr/local/bin/nmap','/sw/bin/nmap','/opt/local/bin/nmap') ):
        self._nmap_path = ''                
        self._scan_result = {}
        self._nmap_version_number = 0      
        self._nmap_subversion_number = 0    
        self._nmap_last_output = ''  
        is_nmap_found = False       

        self.__process = None

        regex = re.compile('Nmap version [0-9]*\.[0-9]*[^ ]* \( http://nmap\.org \)')
        for nmap_path in nmap_search_path:
            try:
                p = subprocess.Popen([nmap_path, '-V'], bufsize=10000, stdout=subprocess.PIPE)
            except OSError:
                pass
            else:
                self._nmap_path = nmap_path  
                break
        else:
            raise PortScannerError('nmap program was not found in path. PATH is : {0}'.format(os.getenv('PATH')))            


            
        self._nmap_last_output = bytes.decode(p.communicate()[0]) 
        for line in self._nmap_last_output.split('\n'):
            if regex.match(line) is not None:
                is_nmap_found = True
                regex_version = re.compile('[0-9]+')
                regex_subversion = re.compile('\.[0-9]+')

                rv = regex_version.search(line)
                rsv = regex_subversion.search(line)

                if rv is not None and rsv is not None:
                    self._nmap_version_number = int(line[rv.start():rv.end()])
                    self._nmap_subversion_number = int(line[rsv.start()+1:rsv.end()])
                break

        if is_nmap_found == False:
            raise PortScannerError('nmap program was not found in path')

        return


    def get_nmap_last_output(self):

        return self._nmap_last_output



    def nmap_version(self):

        return (self._nmap_version_number, self._nmap_subversion_number)

    
    def runningservice(self, hosts='127.0.0.1'):
        # assert type(hosts) is str, 'Wrong type for [hosts], should be a string [was {0}]'.format(type(hosts))
        scanresult1 = self.scan(hosts, arguments='-A -O')
        return scanresult1




    def listscan(self, hosts='127.0.0.1'):

        assert type(hosts) is str, 'Wrong type for [hosts], should be a string [was {0}]'.format(type(hosts))
        self.scan(hosts, arguments='-sL')
        return self.all_hosts()



    def scan(self, hosts='127.0.0.1', ports=None, arguments='-sV'):
        
        #Executing Nmap

        assert type(hosts) is str, 'Wrong type for [hosts], should be a string [was {0}]'.format(type(hosts))
        assert type(ports) in (str, type(None)), 'Wrong type for [ports], should be a string [was {0}]'.format(type(ports))
        assert type(arguments) is str, 'Wrong type for [arguments], should be a string [was {0}]'.format(type(arguments))

        f_args = shlex.split(arguments)
        
        args = [self._nmap_path, '-oX', '-', hosts] + ['-p', ports]*(ports!=None) + f_args

        print args

        p = subprocess.Popen(args, bufsize=100000, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        (self._nmap_last_output, nmap_err) = p.communicate()
        self._nmap_last_output = bytes.decode(self._nmap_last_output)
        nmap_err = bytes.decode(nmap_err)

        if len(nmap_err) > 0:
            regex_warning = re.compile('^Warning: .*')
            for line in nmap_err.split('\n'):
                if len(line) > 0:
                    rgw = regex_warning.search(line)
                    if rgw is not None:
                        sys.stderr.write(line+'\n')
                        pass
                    else:
                        raise PortScannerError(nmap_err)

        scan_result = {}

        # Starting the XML parsing 
        
        dom = xml.dom.minidom.parseString(self._nmap_last_output)

        scan_result['nmap'] = {
            'command_line': dom.getElementsByTagName('nmaprun')[0].getAttributeNode('args').value,
            'scaninfo': {},
            'scanstats':{'timestr':dom.getElementsByTagName("finished")[0].getAttributeNode('timestr').value,                                        'elapsed':dom.getElementsByTagName("finished")[0].getAttributeNode('elapsed').value,                                                     'uphosts':dom.getElementsByTagName("hosts")[0].getAttributeNode('up').value,
            'downhosts':dom.getElementsByTagName("hosts")[0].getAttributeNode('down').value,
            'totalhosts':dom.getElementsByTagName("hosts")[0].getAttributeNode('total').value}
            }
        for dsci in dom.getElementsByTagName('scaninfo'):
            scan_result['nmap']['scaninfo'][dsci.getAttributeNode('protocol').value] = {                
                'method': dsci.getAttributeNode('type').value,
                'services': dsci.getAttributeNode('services').value
                }


        scan_result['scan'] = {}
        
        for dhost in  dom.getElementsByTagName('host'):
            host = dhost.getElementsByTagName('address')[0].getAttributeNode('addr').value
            hostname = ''
            for dhostname in dhost.getElementsByTagName('hostname'):
                hostname = dhostname.getAttributeNode('name').value
            scan_result['scan'][host] = PortScannerHostDict({'hostname': hostname})
            for dstatus in dhost.getElementsByTagName('status'):
                scan_result['scan'][host]['status'] = {'state': dstatus.getAttributeNode('state').value,
                                               'reason': dstatus.getAttributeNode('reason').value}
            for dport in dhost.getElementsByTagName('port'):
                proto = dport.getAttributeNode('protocol').value
                port =  int(dport.getAttributeNode('portid').value)
                state = dport.getElementsByTagName('state')[0].getAttributeNode('state').value
                reason = dport.getElementsByTagName('state')[0].getAttributeNode('reason').value
                name = ''
                for dname in dport.getElementsByTagName('service'):
                    name = dname.getAttributeNode('name').value
                if not proto in list(scan_result['scan'][host].keys()):
                    scan_result['scan'][host][proto] = {}
                scan_result['scan'][host][proto][port] = {'state': state,
                                                  'reason': reason,
                                                  'name': name}
                
        self._scan_result = scan_result 
        return scan_result


    
    def __getitem__(self, host):

        #        assert type(host) is str, 'Wrong type for [host], should be a string [was {0}]'.format(type(host))
        return self._scan_result['scan'][host]


    def all_hosts(self):

        if not 'scan' in list(self._scan_result.keys()):
            return []

        listh = list(self._scan_result['scan'].keys())
        listh.sort()
        return listh
        


class PortScannerHostDict(dict):
    def hostname(self):
        return self['hostname']



class PortScannerError(Exception):

    def __init__(self, value):
        self.value = value


    def __str__(self):
        return repr(self.value)


