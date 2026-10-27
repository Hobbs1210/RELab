import React from 'react';

export const HardwareRadar: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">
            <span>📻 Hardware & Radio Radar</span>
          </div>
          <div className="card-desc">
            Physical device interfaces, USB-to-UART bridges, and Bluetooth Low Energy advertising activity.
          </div>
        </div>
      </div>

      <div className="grid-cols-2">
        <div style={{ background: '#050a14', padding: '14px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: '13px', color: '#fff' }}>🔌 USB / Serial Converters</span>
            <span className="badge badge-safe">Auto-detected</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-sub)' }}>
            Serial ports accessible for hardware console logging or safe opt-in fuzzing:
          </div>
          <div style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.6' }}>
            <div>• <span className="font-mono" style={{ color: 'var(--accent-cyan)' }}>/dev/ttyUSB0</span> — FTDI FT232R USB UART (Default Serial Edge)</div>
            <div>• <span className="font-mono" style={{ color: 'var(--accent-cyan)' }}>/dev/ttyACM0</span> — Black Magic Probe / SWD Interface</div>
          </div>
        </div>

        <div style={{ background: '#050a14', padding: '14px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: '13px', color: '#fff' }}>📡 Bluetooth Low Energy (BLE)</span>
            <span className="badge badge-blue">device-ble (8304)</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-sub)' }}>
            Nearby BLE devices advertising GATT services on the test network:
          </div>
          <div style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.6' }}>
            <div>• Run <span className="font-mono">device-ble</span> MCP tools: <span className="font-mono">ble_discover_devices</span>, <span className="font-mono">ble_read_characteristics</span></div>
            <div>• Restrict all writes to authorized devices. Observation requires no pairing.</div>
          </div>
        </div>
      </div>
    </div>
  );
};
