import sys
import gobject
from calais import *
from nmap import *
try:
    import gtk
    import pygtk
except:
    print("gtk is not available")
    sys.exit(1)

class nmap1:
    def __init__(self):
        self.glade = "nmapnew.glade"
        self.builder = gtk.Builder()
        self.builder.add_from_file(self.glade)
        self.window = self.builder.get_object("window1")
        dic = {"on_button1_clicked":self.scanning}
        self.builder.connect_signals(dic)

    def scanning(self, widget):
        Store = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
        UrlData = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
        nm = PortScanner()
        ip = self.builder.get_object('ipaddress').get_text()
        nm.scan(hosts= ip, arguments='-n')
        host_list = [(x, nm[x]['status']['state']) for x in nm.all_hosts()]
        for host, status in host_list:
            if status in 'up':
                Store.append([host,status])
        ctree = self.builder.get_object("treeview2")
        ctree.set_model(Store)
        #running services in the system
        servicelist = []
        urllist = {}
        urllist = self.datacollection()
        company = urllist.keys()
        url = urllist.values()
        for com in company:
            for u in url:
                UrlData.append([com,u])

        ctree1 = self.builder.get_object("treeview1")
        ctree1.set_model(UrlData)


    def datacollection(self):
        API_KEY = "pqxy23ena8cy6h7679vtp5h8"
        calais = Calais(API_KEY,submitter="Vulnerability Alert Tool")
        result = calais.analyze_url("http://www.us-cert.gov/channels/techalerts.rdf")
        urllist = {}
        for i in range(0,len(result.entities)):
            if result.entities[i]["_type"] in "Company":
                for j in range(i+1,len(result.entities)):
                    if result.entities[j]["_type"] in "URL":
                        urllist[result.entities[i]["name"]] = result.entities[j]["name"]
                    else:
                        break
        return urllist


if  __name__ == "__main__":
    e = nmap1()
    gtk.main()
