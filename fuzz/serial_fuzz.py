"""Opt-in bounded serial protocol testing for physically attached, operator-owned lab hardware.

No automatic device discovery or mutation of unapproved ports. Does not control
power supplies or bootloader/flash interfaces. Review each mutation before use.
"""
from __future__ import annotations
import argparse,os,time

def plan(seed:bytes,count:int):
    if not seed or len(seed)>256:raise ValueError('Seed must be 1..256 bytes')
    for i in range(count):
        arr=bytearray(seed)
        arr[i%len(arr)]^=(1 << (i%8))
        yield bytes(arr)

def main():
    p=argparse.ArgumentParser(description='Bounded serial fuzz: explicit approval required')
    p.add_argument('--device',default='/dev/fuzz-serial')
    p.add_argument('--baud',type=int,default=115200)
    p.add_argument('--seed-hex',required=True)
    p.add_argument('--cases',type=int,default=5)
    p.add_argument('--delay',type=float,default=0.3)
    p.add_argument('--confirm',action='store_true')
    args=p.parse_args()
    if not (args.confirm and os.getenv('SERIAL_FUZZ_ACK')=='I_OWN_THIS_DEVICE'):
        p.error('Use --confirm and SERIAL_FUZZ_ACK=I_OWN_THIS_DEVICE to enable hardware writes')
    if args.device!='/dev/fuzz-serial':p.error('Device must be explicit Compose mapped /dev/fuzz-serial')
    if args.cases<1 or args.cases>100 or args.delay<0.2 or args.baud<1200 or args.baud>921600:
        p.error('Cases <=100, delay >=0.2 seconds and safe baud range required')
    try:seed=bytes.fromhex(args.seed_hex)
    except ValueError:p.error('Invalid seed hex')
    import serial
    # pySerial serial writes are physical device operations: NEVER invoked by MCP.
    with serial.Serial(args.device,args.baud,timeout=1,write_timeout=1) as port:
        for n,msg in enumerate(plan(seed,args.cases),1):
            port.write(msg);port.flush()
            print(f'{n}: wrote {len(msg)} bytes; SHA/secret content suppressed',flush=True)
            time.sleep(args.delay)
if __name__=='__main__':main()
