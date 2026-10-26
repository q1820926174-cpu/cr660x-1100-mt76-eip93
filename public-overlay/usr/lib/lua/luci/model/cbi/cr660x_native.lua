local sys = require "luci.sys"
local m = Map("cr660x_native", translate("CR660x Native Wi-Fi"),
    translate("Experimental driver: 2.4GHz association is unresolved. Change the public setup Wi-Fi key and set an administrator password before normal use. Country must match your location."))

for band = 0, 1 do
    local s = m:section(NamedSection, "band" .. band, "radio", band == 0 and "2.4GHz" or "5GHz")
    s.addremove = false
    local ssid = s:option(Value, "ssid", translate("SSID"))
    ssid.rmempty = false
    function ssid.validate(self, value)
        if value and #value > 0 and #value <= 32 and not value:find("[%c]") then return value end
        return nil, translate("Use 1 to 32 bytes without control characters")
    end
    local key = s:option(Value, "key", translate("WPA2 key"))
    key.password = true
    key.rmempty = false
    key.datatype = "wpakey"
    local country = s:option(Value, "country", translate("Country code"))
    country.rmempty = false
    function country.validate(self, value)
        if value and value:match("^%u%u$") then return value end
        return nil, translate("Use a two-letter uppercase country code")
    end
    local channel = s:option(ListValue, "channel", translate("Channel"))
    channel.rmempty = false
    local channels = band == 0 and {1,2,3,4,5,6,7,8,9,10,11,12,13} or {36,40,44,48,149,153,157,161}
    for _, value in ipairs(channels) do channel:value(tostring(value)) end
end

function m.on_after_commit(self)
    sys.call("/etc/init.d/cr660x-mt76 restart >/dev/null 2>&1 &")
end

return m
