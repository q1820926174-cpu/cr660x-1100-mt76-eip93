module("luci.controller.cr660x_native", package.seeall)

function index()
    entry({"admin", "network", "cr660x_native"}, cbi("cr660x_native"),
        _("CR660x Native Wi-Fi"), 15).dependent = true
end
