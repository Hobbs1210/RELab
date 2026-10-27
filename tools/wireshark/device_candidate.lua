-- Hypothetical binary device framing scaffold. Does not claim to decode any vendor protocol.
-- Set DEVICE_RE_UDP_PORT only after verifying framing and a specific test device.
local p = Proto("device_candidate", "Candidate Device Protocol (raw)")
local payload=ProtoField.bytes("device_candidate.payload","Undecoded payload")
p.fields={payload}
function p.dissector(buf,pinfo,tree)
  if buf:len()<1 then return 0 end
  pinfo.cols.protocol="DEVICE?"
  tree:add(p,buf()):add(payload,buf())
end
local port=tonumber(os.getenv("DEVICE_RE_UDP_PORT") or "0")
if port and port>0 and port<=65535 then DissectorTable.get("udp.port"):add(port,p) end
