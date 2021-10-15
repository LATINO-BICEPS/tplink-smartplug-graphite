#!/usr/bin/env python3
#
# TP-Link Wi-Fi Smart Plug Protocol Client
# For use with TP-Link HS-100 or HS-110
#
# by Lubomir Stroetmann
# Copyright 2016 softScheck GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This was greatly inspired by beardmonkey's guide on hs110 graphite integration
# https://www.beardmonkey.eu/tplink/hs110/2017/11/21/collect-and-store-realtime-data-from-the-tp-link-hs110.html
#
#
import socket
import threading
import json
import ast
import time
from struct import pack
from datetime import datetime

# Predefined Smart Plug Commands
# For a full list of commands, consult tplink_commands.txt
commands = {'info'     : '{"system":{"get_sysinfo":{}}}',
            'on'       : '{"system":{"set_relay_state":{"state":1}}}',
            'off'      : '{"system":{"set_relay_state":{"state":0}}}',
            'ledoff'   : '{"system":{"set_led_off":{"off":1}}}',
            'ledon'    : '{"system":{"set_led_off":{"off":0}}}',
            'cloudinfo': '{"cnCloud":{"get_info":{}}}',
            'wlanscan' : '{"netif":{"get_scaninfo":{"refresh":0}}}',
            'time'     : '{"time":{"get_time":{}}}',
            'schedule' : '{"schedule":{"get_rules":{}}}',
            'countdown': '{"count_down":{"get_rules":{}}}',
            'antitheft': '{"anti_theft":{"get_rules":{}}}',
            'reboot'   : '{"system":{"reboot":{"delay":1}}}',
            'reset'    : '{"system":{"reset":{"delay":1}}}',
            'energy'   : '{"emeter":{"get_realtime":{}}}'
}

# Set target IP, port and command to send
ip = "192.168.1.230"
port = 9999
preset_cmd = "energy"
cmd = commands[preset_cmd]

def encrypt(string):
    key = 171
    result = pack(">I", len(string))
    for i in string:
        a = key ^ ord(i)
        key = a
        result += bytes([a])
    return result

def decrypt(string):
    key = 171
    result = ""
    for i in string:
        a = key ^ i
        key = i
        result += chr(a)
    return result

def store_metrics(current, voltage, power):
    current_time = time.time()
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_sock.connect(("localhost", 2003))
        tcp_sock.send("hs110-tv.voltage {0} {1} \n".format(voltage, current_time).encode())
        tcp_sock.send("hs110-tv.current {0} {1} \n".format(current, current_time).encode())
        tcp_sock.send("hs110-tv.power {0} {1} \n".format(power, current_time).encode())
    except socket.error:
        print("Unable to open socket on graphite-carbon.", file=sys.stderr)
    finally:
        tcp_sock.close()

# Send command and receive reply
def send_hs_command(ip, port, cmd):  
    try:
        sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        sock_tcp.settimeout(int(10))
        sock_tcp.connect((ip, port)) 
        sock_tcp.settimeout(None)
        sock_tcp.send(encrypt(cmd)) 
        data = sock_tcp.recv(2048) 
        sock_tcp.close()
        
        decrypted = decrypt(data[4:])
        return decrypted
    except socket.error:
        quit(f"Could not connect to host {ip}:{port}")



def run():
    threading.Timer(10.0, run).start()
    decrypted_data = send_hs_command("192.168.1.230", 9999, '{"emeter":{"get_realtime":{}}}')
    decrypted_data_dict = ast.literal_eval(decrypted_data)

    # returns string from dictionary
    data = json.dumps(decrypted_data_dict)
    json_data = json.loads(data)
    emeter = json_data["emeter"]["get_realtime"]
    power = emeter["power_mw"]/1000
    voltage = emeter["voltage_mv"]/1000
    current = emeter["current_ma"]/1000
    #total_kwh = emeter["total_wh"]/1000
    #err_code = emeter["err_code"]



    store_metrics(current, voltage, power)
    # can uncomment to display all the stats
    #now = datetime.now()
    #current_time = now.strftime("%H:%M:%S")
    #print("\nPower: {0}W\nVoltage: {1}V\nCurrent: {2}A\nTotal kW Consumed: {3}kW\n".format(power, voltage, current, total_kwh, current_time))

run()