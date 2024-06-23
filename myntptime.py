import time 
import utime
import network
import ntptime

SSID = "Your SSID"
PASSWORD = "Your PASSWORD"

tm_year = 0
tm_mon = 1 # range [1, 12]
tm_mday = 2 # range [1, 31]
tm_hour = 3 # range [0, 23]
tm_min = 4 # range [0, 59]
tm_sec = 5 # range [0, 61] in strftime() description
tm_wday = 6 # range 8[0, 6] Monday = 0
tm_yday = 7 # range [0, 366]
tm_isdst = 8 # 0, 1 or -1    

def set_time():
    
    ntptime.host = 'pool.ntp.org'  # Using a public NTP server
    try:
        ntptime.settime()  # Set RTC with the current time from NTP
        print("Time set from NTP server.")
    except Exception as e:
        print("Failed to set time from NTP server:", e)


    current_time=utime.localtime()
    offset = 1 * 3600  # UTC+1 in seconds
        
    dst_active = (
        (current_time[1] > 3 and current_time[1] < 10) or
        (current_time[1] == 3 and current_time[2] >= 28) or
        (current_time[1] == 10 and current_time[2] < 28)
    )

    if dst_active:
        offset += 3600  # Additional +1 for DST
    
    now=time.time()
    cet=time.localtime(now+offset)
    machine.RTC().datetime((cet[0], cet[1], cet[2], cet[6] + 1, cet[3], cet[4], cet[5], 0))
    print("Local time after synchronization：%s" %str(time.localtime()))    
    
    
    
def main():

    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(SSID, PASSWORD) #replace with your WiFi ssid and password
# Fetch the current time from an NTP server
    
    set_time()    
    
main()