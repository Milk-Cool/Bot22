import pymem
import struct
import sys

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