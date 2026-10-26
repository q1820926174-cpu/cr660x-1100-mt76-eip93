-- Generate native hostapd configs from the owner's existing MTK profiles.
local root = arg[1] or ''
local output = assert(arg[2], 'output directory required')
local function profile(band)
    local marker = io.open(root .. '/etc/config/cr660x_native', 'r')
    if marker then
        -- Read UCI's quoted tokens without executing a shell or requiring libuci-lua.
        -- The public base uses an ubus-backed LuCI UCI layer rather than uci.so.
        local function tokens(line)
            local result, word, quote, started = {}, '', nil, false
            local index = 1
            local function finish()
                if started then result[#result+1] = word end
                word, started = '', false
            end
            while index <= #line do
                local ch = line:sub(index,index)
                if quote == "'" then
                    if ch == quote then quote = nil else word = word .. ch end
                elseif ch == '\\' then
                    index = index + 1
                    assert(index <= #line, 'invalid UCI escape')
                    word = word .. line:sub(index,index)
                    started = true
                elseif quote then
                    if ch == quote then quote = nil else word = word .. ch end
                elseif ch == "'" or ch == '"' then
                    quote, started = ch, true
                elseif ch:match('%s') then
                    finish()
                elseif ch == '#' and not started then
                    break
                else
                    word, started = word .. ch, true
                end
                index = index + 1
            end
            assert(not quote, 'unterminated UCI quote')
            finish()
            return result
        end
        local section, values = nil, {}
        for line in marker:lines() do
            local t = tokens(line)
            if t[1] == 'config' then section = t[3] end
            if t[1] == 'option' and section == 'band' .. band then values[t[2]] = t[3] end
        end
        marker:close()
        return {
            SSID1 = values.ssid,
            WPAPSK1 = values.key,
            CountryCode = values.country,
            Channel = values.channel
        }
    end
    local file = assert(io.open(root .. '/etc/wireless/mediatek/mt7915.dbdc.b' .. band .. '.dat', 'r'))
    local values = {}
    for line in file:lines() do
        local key, value = line:gsub('\r$', ''):match('^([^=#]+)=(.*)$')
        if key then values[key] = value end
    end
    file:close()
    return values
end
for band = 0, 1 do
    local p = profile(band)
    local ssid, pass = assert(p.SSID1), assert(p.WPAPSK1)
    assert(#ssid > 0 and #ssid <= 32 and not ssid:find('[%c]'), 'invalid SSID length')
    assert((#pass >= 8 and #pass <= 63) or (#pass == 64 and pass:match('^%x+$')), 'invalid WPA key length')
    assert(not pass:find('[%c]'), 'invalid WPA key characters')
    local country = p.CountryCode or 'CN'
    assert(country:match('^%u%u$'), 'invalid country code')
    local channel = assert(tonumber(p.Channel), 'channel must be fixed')
    local center
    if band == 0 then
        assert(channel >= 1 and channel <= 13 and channel == math.floor(channel), 'invalid 2G channel')
    else
        local groups = {{36,48,42},{52,64,58},{100,112,106},{116,128,122},{132,144,138},{149,161,155}}
        for _, group in ipairs(groups) do
            if channel >= group[1] and channel <= group[2] and (channel-group[1]) % 4 == 0 then center=group[3] end
        end
        assert(center, 'invalid 5G80 channel')
    end
    local file = assert(io.open(output .. '/hostapd-' .. band .. '.conf', 'w'))
    local function put(value) assert(file:write(value .. '\n')) end
    put('driver=nl80211')
    put('interface=' .. (band == 0 and 'ra0' or 'rax0'))
    put('bridge=br-lan')
    put('ctrl_interface=/run/cr660x-mt76/ctrl')
    put('ssid=' .. ssid)
    put('country_code=' .. country)
    put('ieee80211d=1')
    put('hw_mode=' .. (band == 0 and 'g' or 'a'))
    put('channel=' .. channel)
    put('wmm_enabled=1')
    put('ieee80211n=1')
    put('ieee80211ax=1')
    put('auth_algs=1')
    put('wpa=2')
    put('wpa_key_mgmt=WPA-PSK')
    put('rsn_pairwise=CCMP')
    put((#pass == 64 and 'wpa_psk=' or 'wpa_passphrase=') .. pass)
    put('ieee80211w=' .. (band == 0 and '0' or '1'))
    if band == 1 then
        put('ht_capab=' .. ((channel == center-6 or channel == center+2) and '[HT40+]' or '[HT40-]'))
        put('ieee80211ac=1')
        put('vht_oper_chwidth=1')
        put('vht_oper_centr_freq_seg0_idx=' .. center)
        put('he_oper_chwidth=1')
        put('he_oper_centr_freq_seg0_idx=' .. center)
    end
    file:close()
end
