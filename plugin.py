# Domoticz TP-Link Wi-Fi SmartDevice plugin
#
# Based on "Domoticz TP-Link Wi-Fi Smart Plug plugin" by Dan Hallgren, which itself
# was based on the reverse-engineering work of Lubomir Stroetmann and Tobias Esser.
# (https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/)
#
# This plugin leverages the excellent pyHS100 library, which abstracts the various
# implementation variances of the TP-Link product line into an easily-controlled unified
# object.
#
# Devices that support power metering will automatically have their statistics collected.
# The plugin will attempt to enable devices that are configured but unavailable at startup
# each heartbeat event (currently set to sixty seconds).
#
# Author: Christopher KOBAYASHI <software+github@disavowed.jp>

"""
<plugin key="tplink-smartdevice"
        name="TP-Link SmartDevice"
        version="0.0.1"
        author="Christopher KOBAYASHI"
        wikilink="https://www.domoticz.com/wiki/plugins/plugin.html"
        externallink="https://github.com/christopherkobayashi/domoticz-tplink-smartbulb/blob/master/plugin.py"
    >
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
    Discover
)

import Domoticz
import time

class TpLinkPlugin:
    enabled = False
    alive = False
    brightness = 0
    color = False

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

        if self.bulb.is_dimmable:
            self.brightness = self.bulb.brightness
            device_type = 'Dimmer'
            n_Value = self.bulb.is_on * 2
        else:
            self.brightness = self.bulb.is_on * 100
            device_type = 'Switch'
            n_Value = self.bulb.is_on * 1
        if self.bulb.is_color:
            self.color = True

        if Devices[1]:
            if self.bulb.is_dimmable:
                Devices[1].Update(nValue=0, sValue = str(self.brightness), Description=self.bulb.model, Type=244, Subtype=73, Switchtype=7, Image=1, Used=1)
            else:
                Devices[1].Update(nValue=0, sValue = str(self.brightness), TypeName='Switch', Image=1, Used=1)
        else:
            if self.bulb.is_dimmable:
                Domoticz.Device(Name='Dimmer', Description=self.bulb.model, Unit=1,  Type=244, Subtype=73, Switchtype=7, Image=1, Used=1).Create()
            else:
                Domoticz.Device(Name='Switch', Description=self.bulb.model, Unit=1, TypeName='Switch', Image=1, Used=1).Create()

        if self.bulb.has_emeter:
            realtime_result = self.bulb.get_emeter_realtime()
            if Devices[2]:
              Devices[2].Update(nValue=0, sValue=str(realtime_result['power_mw'] / 1000), TypeName='kWh', Image=1, Used=1)
            else:
              Domoticz.Device(Name="power consumed (watts)", Unit=2, TypeName='kWh', Image=1, Used=1).Create()

        # Clean up unused
        if Devices[3]:
            Devices[3].Delete()

    def onStop(self):
        Domoticz.Log("onStop called")
        if self.bulb:
            Domoticz.Log("onStop deleting self.bulb")
            del self.bulb
        Domoticz.Log("onStop exiting")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data, Status, Extra):
        Domoticz.Log("onMessage called")

    def onCommand(self, unit, command, level, hue):
        command = command.lower()
        if self.alive:
            Domoticz.Log("onCommand called for Unit " +
                     str(unit) + ": Parameter '" + str(command) + "', Level: " + str(level))
            n_Value = 0
            okay = False
            try:
                if command == 'on':
                    self.bulb.turn_on()
                    okay = self.bulb.is_on
                    n_Value = 1
#                    n_Value = 2
                elif command == 'off':
                    self.bulb.turn_off()
                    okay = self.bulb.is_off
                elif command == 'set level':
                    if self.bulb.is_off:
                        self.bulb.turn_on()
                        time.sleep(5)
                    self.bulb.brightness = level
                    okay = self.bulb.is_on
                    n_Value = 2
            except:
                Domoticz.Log("failed command execution, disabling")
                self.alive = False
                return

            if okay:
                Devices[unit].Update(nValue = n_Value, sValue=str(level))
                # Reset counter so we trigger emeter poll next heartbeat
                self.heartbeatcounter = 0

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        if self.alive:
            try:
                if (self.heartbeatcounter % self.interval == 0) and self.bulb.has_emeter:
                    realtime_result = self.bulb.get_emeter_realtime()
                    if realtime_result is not False:
                        Domoticz.Log("power consumption: " + str(realtime_result['power_mw'] / 1000) + "W")
                        Devices[2].Update(nValue=0, sValue=str(realtime_result['power_mw'] / 1000))
                self.heartbeatcounter += 1
                if self.bulb.is_dimmable:
                    self.brightness = self.bulb.brightness
                    n_Value = self.bulb.is_on * 2
                else:
                    self.brightness = self.bulb.is_on * 100
                    n_Value = self.bulb.is_on * 1
                Devices[1].Update(nValue=n_Value, sValue=str(self.brightness))
            except:
                Domoticz.Log("failed heartbeat, disabling")
                self.alive = False
                return
        else:
            Devices[1].Update(nValue=0, sValue="Unavailable")
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
