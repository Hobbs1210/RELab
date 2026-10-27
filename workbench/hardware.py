"""Read-only sysfs inventory, not permission to control devices."""
from pathlib import Path

def enumerate_hardware(sysroot:Path=Path('/sys')) -> dict:
    serial=[];usb=[]
    byid=Path('/dev/serial/by-id')
    if byid.is_dir():
        for p in sorted(byid.iterdir())[:64]:serial.append({'id':p.name,'device':str(p.resolve())})
    tty=sysroot/'class/tty'
    if tty.is_dir():
        for p in sorted(tty.iterdir())[:200]:
            if p.name.startswith(('ttyUSB','ttyACM')) and not any(x['device'].endswith('/'+p.name) for x in serial):
                serial.append({'id':p.name,'device':'/dev/'+p.name})
    devices=sysroot/'bus/usb/devices'
    if devices.is_dir():
        for p in sorted(devices.iterdir())[:150]:
            try:
                vid=(p/'idVendor').read_text().strip();pid=(p/'idProduct').read_text().strip()
                product=(p/'product').read_text(errors='replace').strip()[:100] if (p/'product').exists() else ''
                usb.append({'path':p.name,'vendor_id':vid,'product_id':pid,'product':product})
            except OSError:pass
    return {'serial':serial,'usb':usb,'reads_only':True,
            'note':'Sysfs visibility is host-dependent. Serial writes, flash, GPIO, SWD and JTAG are not exposed by default.'}
