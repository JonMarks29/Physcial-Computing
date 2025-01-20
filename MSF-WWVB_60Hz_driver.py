from machine import Pin, PWM
import time
import gc
import _thread


# Driver for  WWVB 60hZ ferrite antenna to collect MST Anthorn (NPL national time signal) radio signal
# as set up, runs in the background on the second core of a RPi Pico, but the driver function could be adapated


# monitors the incoming signal from a 60hz ferrite rod and adaptor module
# reads the signal as the MST-Anthorn (NPL) time radio broadcast
# after reading a complete minute, saves it to the global variable:   time_mst
def monitor_MST(RF_data_pin, RF_power_pin, utc_correction=True):
    RF_power_pin.value(0)
    global time_mst
    global time_since_reset
    global using_time_flag
    
    data = []
    while True:
        if time_since_reset < 60:
            RF_led.value(1)
        else:
            RF_led.toggle()
        set_signal_center = True
        
        while RF_data_pin.value() == 0:
            time.sleep(0.01)
            set_signal_center = False

        # i.e. exit loop when first 1 bit reaached
        if set_signal_center == False:
            time.sleep(0.04) # let the signal get into the middle of the curent bit
            set_signal_center = True
            data = []
        
        # print(RF_data.value())
        data.append(RF_data_pin.value())
        time.sleep(0.1)

        if (data[-5:] != [1,1,1,1,1]):
            while (len(data) >= 10):
                del data[0]
        
        else:
            print("reading minute start")
 #           gc.collect() 
            seconds = 1
            a_bits, b_bits = [1],[1]
            while seconds < 60:
                while RF_data.value() == 0:
                    time.sleep(0.01)
                # i.e. when exit loop reached 1 at start of next second
                start = time.ticks_ms()
                seconds += 1
                time.sleep(0.145)
                a_bits.append(RF_data_pin.value())
                time.sleep(0.1)
                b_bits.append(RF_data_pin.value())
                
                count = len(a_bits)
                
                if count == 9:
                    dut1_positive = sum(b_bits[1:9])
                elif count == 17:
                    dut1_negative = sum(b_bits[9:17])
                elif count == 26:
                    year = 80*a_bits[17] + 40*a_bits[18] + 20*a_bits[19] + 10*a_bits[20] + 8*a_bits[21] + 4*a_bits[22] + 2*a_bits[23] + 1*a_bits[24]
                elif count == 30:
                    month = 10*a_bits[25] + 8*a_bits[26] + 4*a_bits[27] + 2*a_bits[28] + 1*a_bits[29]
                elif count == 36:
                    day = 20*a_bits[30] + 10*a_bits[31] + 8*a_bits[32] + 4*a_bits[33] + 2*a_bits[34] + 1*a_bits[35]
                elif count == 39:
                    day_of_week = 4*a_bits[36] + 2*a_bits[37] + 1*a_bits[38]
                elif count == 45:
                    hour = 20*a_bits[39] + 10*a_bits[40] + 8*a_bits[41] + 4*a_bits[42] + 2*a_bits[43] + 1*a_bits[44]
                elif count == 52:
                    minute = 40*a_bits[45] + 20*a_bits[46] + 10*a_bits[47] + 8*a_bits[48] + 4*a_bits[49] + 2*a_bits[50] + 1*a_bits[51]
        
                elif count == 55:    
                    year_parity = sum([b_bits[54]]+a_bits[17:25])
                elif count == 56:   
                    month_parity = sum([b_bits[55]]+a_bits[25:36])
                elif count == 57:   
                    day_of_week_parity = sum([b_bits[56]]+a_bits[36:39])
                elif count == 58:   
                    time_parity = sum([b_bits[57]]+a_bits[39:52])
                elif count == 59:
                    bst = b_bits[58]
    
                
                if seconds == 60:
                    if utc_correction == True:
                        hour -= bst
                    
                    if year_parity%2 != 1:
                        year = None
                    if month_parity%2 !=1:
                        month = None
                    if day_of_week_parity%2 != 1:
                        day_of_week = None
                    if time_parity%2 != 1:
                        hour, minute = None, None
                    
                    current_time = (year, month, day, hour, minute)
                    while using_time_flag == True:
                        time.sleep(0.0001)
                    using_time_flag == True
                    if None not in current_time and current_time[0] > 23 and current_time[1] < 13 and current_time[2] < 32 and current_time[3] < 25 and current_time[4] < 61:
                        time_mst = current_time
                        time_since_reset = 0
                    else:
                        time_since_reset += 1
                    using_time_flag = False
                    #print(current_time)
                        
                
                # pause here until 600ms of the current second have passed
                while time.ticks_diff(time.ticks_ms(), start) < 600:
                    time.sleep(0.1)


# initialse components and variables for time
RF_power = machine.Pin(19, machine.Pin.OUT)
RF_data = machine.Pin(28, machine.Pin.IN)
RF_led = machine.Pin(27, machine.Pin.OUT)

# GLOBAL VARIABLES, to be read by both cores
# NEED LOCKING FLAGS TO PREVENT DOUBLE ACCESS
using_time_flag = False
time_mst = tuple()
time_since_reset = 100



# initialise and run the timing thread on core 1 (i.e. not the base core 0)
time_thread2 = _thread.start_new_thread(monitor_MST, (RF_data, RF_power, True))

start = time.ticks_ms()

# allow up to 5 minutes to get a good time signal
# once signal received, break out of the loop
# RF_led flashes while searching for time signal
while time.ticks_diff(time.ticks_ms(), start) < 300000: 
    while using_time_flag == True:
        pass
    using_time_flag = True
    if time_since_reset < 5:
        year, month, day, hour, minute = time_mst
        minute += time_since_reset
        using_time_flag = False
        set_time = (hour, minute)
        set_date = (month, day)
        break
    using_time_flag = False
    time.sleep(2)
    RF_led.toggle()

RF_led.value(1)



                