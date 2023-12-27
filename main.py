import pymem
import struct
import sys
import pynput
import time
import os

debug = False
try:
    debug = os.environ["DEBUG"]
except KeyError:
    pass


class Bot:
    def __init__(self, addrs, mode):
        self.addrs = addrs
        self.clicks = {}
        self.exitnow = False
        self.mode = mode

    def on_down(self):
        self.clicks[pm.read_float(self.addrs[0])] = 1

    def on_up(self):
        self.clicks[pm.read_float(self.addrs[0])] = 0

    def on_click(self, x, y, button, pressed):
        if debug:
            print(button)
        if button != pynput.mouse.Button.left:
            return
        if pressed:
            self.on_down()
        else:
            self.on_up()

    def on_press_a(self, key):
        if debug:
            print(key)
        if (key == pynput.keyboard.Key.space
            or key == pynput.keyboard.Key.up
                or key == pynput.keyboard.KeyCode.from_char('w')):
            self.on_down()
        elif (key == pynput.keyboard.KeyCode.from_char('\\')):
            self.exitnow = True

    def on_press_b(self, key):
        if debug:
            print(key)
        if (key == pynput.keyboard.KeyCode.from_char('\\')):
            self.exitnow = True

    def on_release(self, key):
        if debug:
            print(key)
        if (key == pynput.keyboard.Key.space
            or key == pynput.keyboard.Key.up
                or key == pynput.keyboard.KeyCode.from_char('w')):
            self.on_up()

    def record(self):
        self.exitnow = False
        self.clicks = {}

        listener_mouse = pynput.mouse.Listener(on_click=self.on_click)
        listener_mouse.start()
        listener_keyboard = pynput.keyboard.Listener(
            on_press=self.on_press_a, on_release=self.on_release)
        listener_keyboard.start()

        last = 0
        while (True):
            if (self.exitnow):
                listener_mouse.stop()
                listener_keyboard.stop()
                break
            x = pm.read_float(self.addrs[0])
            if (x < last):
                clicks_new = self.clicks.copy()
                for i in self.clicks:
                    if (debug):
                        print(i, type(i), x, type(x))
                    if i > x:
                        clicks_new.pop(i)
                self.clicks = clicks_new.copy()
            last = x
            time.sleep(0.004)

        if (debug):
            print(self.clicks)

    def replay(self):
        self.exitnow = False

        controller = pynput.keyboard.Controller()

        listener_keyboard = pynput.keyboard.Listener(on_press=self.on_press_b)
        listener_keyboard.start()

        last = 0
        while (True):
            if (self.exitnow):
                listener_keyboard.stop()
                break
            x = pm.read_float(self.addrs[0])
            if (x < 10):
                last = 0
            else:
                for i in self.clicks:
                    if i > last and i <= x:
                        (controller.press if self.clicks[i] else controller.release)(
                            pynput.keyboard.Key.space)
                last = x
            time.sleep(0.004)

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
            f = struct.unpack("<f", page_bytes[i: i + 4])[0]
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
        address, found_in_page = scan_float_range_page(
            handle, address, fmin, fmax)
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

if debug:
    print(pm)

method = "x"


def prompt_a():
    global method
    print("What would you like to use?")
    print("[1] X pos (Practice Mode, Autocomplete)")
    print("[2] Time (Platformer Mode, not yet supported)")
    a = input()
    if (a == "1"):
        method = "x"
    elif (a == "2"):
        method = "t"
    else:
        print("Invalid option, try again.")
        prompt_a()


prompt_a()

addrs = []

while True:
    xpos = input("Enter X pos or press Enter to finish: " if method ==
                 "x" else "Enter time or press Enter to finish: ")
    if xpos == "":
        break
    xpos = float(xpos)
    xmin = float(xpos - (1 if method == "x" else 0.02))
    xmax = float(xpos + (1 if method == "x" else 0.02))
    print("Please wait...")

    if (len(addrs) == 0):
        addrs = scan_float_range(pm.process_handle, xmin, xmax)
    else:
        addrs_new = addrs
        for addr in addrs:
            f = pm.read_float(addr)
            if not (xmin <= f <= xmax):
                addrs_new.remove(addr)
        addrs = addrs_new

    print("Found " + str(len(addrs)) + " addresses.")

if (len(addrs) == 0):
    print("No addresses found, exiting...")
    exit(0)

bot = Bot(addrs, method)


def autocomplete():
    for i in addrs:
        try:
            pm.write_float(i, 999999.0)
        except:
            print("Failed to write to address {}".format(i))
    prompt_b()


def prompt_b():
    print("What would you like me to do?")
    if method == "x":
        print("[1] Autocomplete")
        print("[2] Record")
        print("[3] Replay")
        a = input()
        if (a == "1"):
            autocomplete()
        elif (a == "2"):
            bot.record()
        elif (a == "3"):
            bot.replay()
        else:
            print("Invalid option, try again.")
            prompt_b()
    elif method == "t":
        print("[1] Record")
        print("[2] Replay")
        a = input()
        if (a == "1"):
            bot.record()
        elif (a == "2"):
            bot.replay()
        else:
            print("Invalid option, try again.")
            prompt_b()


while True:
    prompt_b()
