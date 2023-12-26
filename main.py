import pymem
import struct
import sys
import pynput
import time

# Just copying some code from pymem's source code...

def scan_float_range_page(handle, address, fmin, fmax):
    try:
        mbi = pymem.memory.virtual_query(handle, address)
    except:
        # Some insanely high number to indicate that we're done
        return 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF, []
    next_region = mbi.BaseAddress + mbi.RegionSize
    allowed_protections = [
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_EXECUTE,
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_EXECUTE_READ,
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_EXECUTE_READWRITE,
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_READWRITE,
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_READONLY,
    ]
    if mbi.state != pymem.ressources.structure.MEMORY_STATE.MEM_COMMIT or mbi.protect not in allowed_protections:
        return next_region, None

    page_bytes = pymem.memory.read_bytes(handle, address, mbi.RegionSize)

    found = []

    for i in range(len(page_bytes) - 3):
        try:
            f = struct.unpack("<f", page_bytes[i : i + 4])[0]
            if fmin <= f <= fmax:
                found.append(address + i)
        except struct.error:
            pass

    return next_region, found

def scan_float_range_module(handle, module, fmin, fmax):
    address = module.lpBaseOfDll
    size = module.SizeOfImage

    found = []

    while address < module.lpBaseOfDll + size:
        address, found_in_page = scan_float_range_page(handle, address, fmin, fmax)
        if found_in_page is not None:
            found.extend(found_in_page)

    return found

def scan_float_range(handle, fmin, fmax):
    found = []
    next_region = 0

    user_space_limit = 0x7FFFFFFF0000 if sys.maxsize > 2**32 else 0x7fff0000
    while next_region < user_space_limit:
        next_region, page_found = scan_float_range_page(
            handle,
            next_region,
            fmin,
            fmax
        )

        if page_found:
            found += page_found

    return found

# Now the actual code

input("Open Geometry Dash and press enter...")

pm = None

try:
    pm = pymem.Pymem("GeometryDash.exe")
except:
    pm = pymem.Pymem("GeometryDash.ex")

if pm == None:
    exit(1)

addrs = []

while True:
    xpos = input("Enter X pos or press Enter to finish: ")
    if xpos == "":
        break
    xpos = int(xpos)
    xmin = float(xpos - 1)
    xmax = float(xpos + 1)
    print("Please wait...")

    if(len(addrs) == 0):
        addrs = scan_float_range(pm.process_handle, xmin, xmax)
    else:
        addrs_new = addrs
        for addr in addrs:
            f = pm.read_float(addr)
            if not (xmin <= f <= xmax):
                addrs_new.remove(addr)
        addrs = addrs_new
    
    print("Found " + str(len(addrs)) + " addresses.")

if(len(addrs) == 0):
    print("No addresses found, exiting...")
    exit(0)

def autocomplete():
    for i in addrs:
        pm.write_float(i, 999999.0)
    prompt()

clicks = None

def record():
    global clicks
    exitnow = False
    clicks = {}

    def on_down():
        global clicks
        clicks[pm.read_float(addrs[0])] = 1
    def on_up():
        global clicks
        clicks[pm.read_float(addrs[0])] = 0
    
    def on_click(x, y, button, pressed):
        if button != pynput.mouse.Button.left:
            return
        if pressed:
            on_down()
        else:
            on_up()
    
    def on_press(key):
        global exitnow
        if (key == pynput.keyboard.Key.space
            or key == pynput.keyboard.Key.up
            or key == pynput.keyboard.KeyCode.from_char('w')):
            on_down()
        elif(key == pynput.keyboard.Key.ctrl_r):
            exitnow = True
    def on_release(key):
        if (key == pynput.keyboard.Key.space
            or key == pynput.keyboard.Key.up
            or key == pynput.keyboard.KeyCode.from_char('w')):
            on_up()
    
    listener_mouse = pynput.mouse.Listener(on_click=on_click)
    listener_mouse.start()
    listener_keyboard = pynput.keyboard.Listener(on_press=on_press, on_release=on_release)
    listener_keyboard.start()
    while(True):
        if(exitnow):
            listener_mouse.stop()
            listener_keyboard.stop()
            break
        if(pm.read_float(addrs[0]) < 10):
            clicks = {}
        time.sleep(0.004)
    prompt()

def replay():
    global clicks
    exitnow = False

    controller = pynput.keyboard.Controller()

    def on_press(key):
        global exitnow
        if(key == pynput.keyboard.Key.ctrl_r):
            exitnow = True

    listener_keyboard = pynput.keyboard.Listener(on_press=on_press)
    listener_keyboard.start()
    
    last = 0
    while(True):
        if(exitnow):
            listener_keyboard.stop()
            break
        x = pm.read_float(addrs[0])
        if(x < 10):
            last = 0
        else:
            for i in clicks:
                if i > last and i < x:
                    (controller.press if clicks[i] else controller.release)(pynput.keyboard.Key.space)
            last = x
        time.sleep(0.004)
    prompt()

def prompt():
    print("What would you like me to do?")
    print("[1] Autocomplete")
    print("[2] Record")
    print("[3] Replay")
    a = input()
    if(a == "1"): autocomplete()
    elif(a == "2"): record()
    elif(a == "3"): replay()
    else:
        print("Invalid option, try again.")
        prompt()

prompt()