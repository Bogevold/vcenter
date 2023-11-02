#! /usr/bin/env python3
import requests
import json
import getpass
import re
import curses
import threading
from time import sleep
from base64 import b64encode
 
# Authorization token: we need to base 64 encode it
# and then decode it to acsii as python 3 stores it as a byte string
def basic_auth(username, password):
    token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
    return f'Basic {token}'

def isLocalIP(vm, auth):
  api_url = f"{vmHost}rest/vcenter/vm/{vm}/guest/networking/interfaces"
  try:
    vmr = requests.get(api_url, headers=auth)
    ips = [f["ip"]["ip_addresses"][0]["ip_address"] for f in vmr.json().get("value") if 1==1]
    ipsf = list(filter(lambda x: not x.startswith('10.'), ips)) # Remove ips starting with 10. 
    ipsf2 = list(filter(lambda x: not x.startswith('192.'), ips)) # Remove ips starting with 192. 
    return len(ipsf2)>0
  except Exception as err:
    return false
 
def getOs(vm, auth):
    api_url_vm_det = "https://vcprod.skead.no/rest/vcenter/vm/"
    vm_r = requests.get(api_url_vm_det + vm, headers=auth)
    os = vm_r.json().get("value")["guest_OS"]
    r_os = ""
    if re.search("rhel", os, re.IGNORECASE):
        r_os = "rhel"
    elif re.search("oracle", os, re.IGNORECASE):
        r_os = "oel"
    else:
        r_os = os
    return r_os
 
def getHostDns(vm, auth):
    api_url_vm_host = f"https://vcprod.skead.no/rest/vcenter/vm/{vm}/guest/networking"
    try:
      vmh_r = requests.get(api_url_vm_host,headers=auth)
      dns = vmh_r.json().get("value")["dns_values"]["host_name"]
      return dns
    except Exception as err:
      return ""
 
def writeInventory(vmList, name):
  f = open("inventory/{}.yml".format(name), "w")
  f.writelines(["{}:\n".format(name), "  hosts:\n"])
  for h in vmList:
    f.writelines(["    {}:\n".format(h)])
  f.close()
 
def loginVCenter():
  un = input("User for vCenter: ")
  pw = getpass.getpass()
 
  auth_headers = { 'Authorization' : basic_auth(un,pw) }
  api_url_auth = "https://vcprod.skead.no/api/session"
  aut_r = requests.post(api_url_auth, headers=auth_headers)
  headers = {"vmware-api-session-id":aut_r.json()}
  return headers
 
def lesMappe(headers, folderNm, folderId, folderNum, stdscr):
  api_url_vm = f"https://vcprod.skead.no/rest/vcenter/vm/?filter.power_states=POWERED_ON&filter.folders.1={folderId}"
  r2=requests.get(api_url_vm, headers=headers)
  vmEr=r2.json().get("value")
  antVmer = len(vmEr)
  if antVmer == 0:
    stdscr.addstr(folderNum +2,0, f'{0:3}/{0:3} vmer i {folderNm}')
  curVm = 0
  for vm in vmEr:
    curVm+=1
    stdscr.addstr(folderNum +2,0, f'{curVm:3}/{antVmer:3} vmer i {folderNm}')
    stdscr.refresh()
    hostnameFromGuest = getHostDns(vm["vm"], headers)
    vmName = vm["name"]
    host = vmName if hostnameFromGuest == "" else hostnameFromGuest
    if not isLocalIP(vm["vm"], headers):
      lister["miljoDmz"].append(host)
    elif folderNm == "SIAN ProdSupport":
      lister["miljoProd"].append(host)
    elif folderNm ==  "Linux-support":
      lister["miljoProd"].append(host)
    elif folderNm == "SIAN PROD":
      lister["miljoProd"].append(host)
    elif folderNm == "SIAN DataGuard":
      lister["miljoProd"].append(host)
    elif folderNm == "Datavarehus (sap-hana)":
      lister["miljoProd"].append(host)
    elif folderNm == "SIAN OPPL":
      lister["miljoOppl"].append(host)
    elif folderNm == "SIAN TEST":
      lister["miljoTest"].append(host)
    elif folderNm == "SIAN AKS":
      lister["miljoAks"].append(host)
    elif folderNm == "SIAN UTV":
      lister["miljoUtv"].append(host)
    elif folderNm == "SIAN Anon&DBA":
      lister["miljoAnon"].append(host)
    else:
      lister["miljoIgn"].append(host)
    if re.search("db[0-9]{2}", host):
      lister["grpDb"].append(host)
    os = getOs(vm["vm"], headers)
    if os == "oel":
        lister["osOel"].append(host)
    elif os == "rhel":
        lister["osRhel"].append(host)
 
 
def lagInventory(stdscr, headers):
  api_url_top = "https://vcprod.skead.no/rest/vcenter/folder?filter.names.1=SIAN-MO"
  api_url_sub = "https://vcprod.skead.no/rest/vcenter/folder?filter.parent_folders.1="
  resp_top = requests.get(api_url_top, headers=headers)
  top_grp = resp_top.json().get("value")[0]["folder"]
  res_sub = requests.get(api_url_sub + top_grp, headers=headers)
  subFolders=res_sub.json().get("value")
  name = ""
  stdscr.clear() # Tømmer skjermen
  stdscr.clrtoeol()
  curses.curs_set(0)
  antFolders = len(subFolders)
  curFolder = 0
  for subFolder in subFolders:
    curFolder+=1
    name = subFolder["name"]
    folderId = subFolder["folder"]
    stdscr.addstr(1,0, f'{curFolder:3}/{antFolders:3} mapper {" "*30}')
    traader.append(threading.Thread(target=lesMappe,args=(headers,name,folderId,curFolder,stdscr,)))
  for t in traader:
    t.start()
  for t in traader:
    t.join()
  for k,v in lister.items():
    v.sort()
    if k != "miljoIgn":
      writeInventory(v, k)
  sleep(4)
 
traader = []
# Miljølister
lister = {
  "miljoProd":[],
  "miljoAks" :[],
  "miljoTest":[],
  "miljoUtv" :[],
  "miljoOppl":[],
  "miljoAnon":[],
  "miljoIgn" :[], 
  "miljoDmz" :[],
  "grpDb" :[],
  "osRhel":[],
  "osOel" :[]
    }
headers = loginVCenter()
curses.wrapper(lagInventory, headers)