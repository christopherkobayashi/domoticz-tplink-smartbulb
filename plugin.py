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

class TpLinkPlugin:
    enabled = False
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

        if self.bulb.is_dimmable:
            brightness = self.bulb.brightness
            device_type = 'Dimmer'
        else:
            brightness = self.bulb.is_on * 100
            device_type = 'Switch'
        if len(Devices) < 1:
            Domoticz.Device(Name=device_type, Description=self.bulb.model, Unit=1, Type=device_type, Image=1, Used=1).Create()
        else:
            Devices[1].Update(nValue = self.bulb.is_on, sValue = str(brightness), TypeName=device_type, Description=self.bulb.model, Used=1)

        if self.bulb.has_emeter:
            if len(Devices) < 2:
                Domoticz.Device(Name="power consumed (watts)", Unit=2, TypeName='kWh', Image=1, Used=1).Create()
            else:
                realtime_result = self.bulb.get_emeter_realtime()
                Devices[2].Update(nValue=0, sValue=str(realtime_result['power_mw'] / 1000), TypeName='kWh', Image=1, Used=1)
        # Reap any devices that might have been erroneously created
        if len(Devices) > 2:
            for i in range (3, len(Devices)+1):
               Devices[i].Delete()

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
                okay = self.bulb.is_on
            elif command.lower() == 'off':
                self.bulb.turn_off()
                okay = self.bulb.is_off
            elif command.lower() == 'set level':
                if self.bulb.is_off:
                    self.bulb.turn_on()
                self.bulb.set_brightness(level)
                okay = self.bulb.is_on
            else:
                okay = False

            if okay is True:
                Devices[unit].Update(nValue = self.bulb.is_on, sValue=str(level))
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
                    Domoticz.Log("power consumption: " + str(realtime_result['power_mw'] / 1000) + "W")
                    Devices[2].Update(nValue=0, sValue=str(realtime_result['power_mw'] / 1000))
            self.heartbeatcounter += 1
            if self.bulb.is_dimmable:
                brightness = self.bulb.brightness
            else:
                brightness = self.bulb.is_on * 100
            Devices[1].Update(nValue=self.bulb.is_on, sValue=str(brightness))
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
