# Domoticz TP-Link Wi-Fi Smart Device plugin
#
# Plugin based "Domoticz TP-Link Wi-Fi Smart Plug plugin" by Dan Hallgren, which itself
# was based on the reverse-engineering work of Lubomir Stroetmann and Tobias Esser.
# (https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/)
#
# Author: Christopher KOBAYASHI
#
"""
<plugin key="domoticz-tplink-smartdevice" name="TP-Link SmartDevice" version="0.0.1" author="wileyc" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://www.google.com/">
    <description>
        <h2>TP-Link SmartDevice</h2>
        <ul style="list-style-type:square">
            <li>on/off switching</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>switch - On/Off</li>
        </ul>
    </description>
    <params>
        <param field="Address" label="IP Address" width="200px" required="true"/>
        <param field="Mode1" label="Model" width="150px" required="false">
             <options>
                <option label="KL110" value="KL110"  default="true" />
            </options>
        </param>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

from pyHS100 import (
    SmartDevice,
    SmartPlug,
    SmartBulb,
    SmartStrip,
    Discover,
)

import Domoticz

class TpLinkPlugin:
    enabled = False
    connection = None
    alive = False

    def __init__(self):
        self.interval = 6  # 6*10 seconds
        self.heartbeatcounter = 0

    def onStart(self):
        try:
            self.bulb = Discover.discover_single(Parameters["Address"])
        except:
            Domoticz.Log("is not available")
            return
        Domoticz.Log("is available")
        self.alive = True
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
            DumpConfigToLog()

        Domoticz.Device(Name="switch", Unit=1, TypeName="Switch", Used=1).Create()
        Domoticz.Log("Tp-Link smart bulb device created")

        if self.bulb.has_emeter and len(Devices) <= 1:
            Domoticz.Device(Name="emeter power (W)", Unit=2, Type=243, Subtype=31, Image=1, Used=1).Create()

        if self.bulb.is_on:
            Devices[1].Update(1, '100')
        else:
            Devices[1].Update(0, '0')

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data, Status, Extra):
        Domoticz.Log("onMessage called")

    def onCommand(self, unit, command, level, hue):
        if self.alive:
            Domoticz.Log("onCommand called for Unit " +
                     str(unit) + ": Parameter '" + str(command) + "', Level: " + str(level))

            if command.lower() == 'on':
                self.bulb.turn_on()
                state = (1, '100')
                err_code = self.bulb.is_on
            elif command.lower() == 'off':
                self.bulb.turn_off()
                state = (0, '0')
                err_code = self.bulb.is_off

            if err_code is True:
                Devices[1].Update(*state)
                # Reset counter so we trigger emeter poll next heartbeat
                self.heartbeatcounter = 0

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        if self.alive:
            if (self.heartbeatcounter % self.interval == 0) and self.bulb.has_emeter:
                realtime_result = self.bulb.get_emeter_realtime()
                if realtime_result is not False:
                    Devices[2].Update(nValue=0, sValue=str(realtime_result['power_mw'] / 1000))
            self.heartbeatcounter += 1
            if self.bulb.is_on:
                Devices[1].Update(1, '100')
            else:
                Devices[1].Update(0, '0')
        else:
            onStart()

global _plugin
_plugin = TpLinkPlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Connection, Data, Status, Extra)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
