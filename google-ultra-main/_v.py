import ultra0
ultra0.ADB = ultra0.find_adb(); ultra0.SERIAL = "127.0.0.1:16384"
print((ultra0.verify() or "(空)")[:500])
