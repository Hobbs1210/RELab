"""Read-only BLE discovery (BlueZ DBus required). Never writes GATT characteristics."""
import argparse,asyncio,json
from bleak import BleakScanner,BleakClient
async def main():
    p=argparse.ArgumentParser();p.add_argument('--address');p.add_argument('--timeout',type=float,default=10);a=p.parse_args()
    if not a.address:
        devices=await BleakScanner.discover(timeout=a.timeout,return_adv=True)
        print(json.dumps([{'address':k,'name':d.name,'rssi':adv.rssi,'service_uuids':adv.service_uuids} for k,(d,adv) in devices.items()],indent=2));return
    async with BleakClient(a.address,timeout=a.timeout) as c:
        print(json.dumps([{'uuid':s.uuid,'description':s.description,'characteristics':[{'uuid':x.uuid,'properties':x.properties} for x in s.characteristics]} for s in c.services],indent=2))
asyncio.run(main())
