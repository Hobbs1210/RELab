import React, { useState } from 'react';

interface ProtocolPlaygroundProps {
  onShowToast: (msg: string) => void;
}

export const ProtocolPlayground: React.FC<ProtocolPlaygroundProps> = ({ onShowToast }) => {
  const [hexInput, setHexInput] = useState('00 0e 01 02 48 65 6c 6c 6f 20 57 6f 72 6c 64 21');
  const [framingType, setFramingType] = useState<'len16_be' | 'len16_le' | 'cobs' | 'tlv'>('len16_be');
  const [generatedKsy, setGeneratedKsy] = useState('');

  const parseHex = (hex: string): number[] => {
    return hex.replace(/[^0-9a-fA-F]/g, '').match(/.{1,2}/g)?.map(byte => parseInt(byte, 16)) || [];
  };

  const handleDissect = () => {
    const bytes = parseHex(hexInput);
    if (bytes.length === 0) {
      alert('Please provide valid hex bytes');
      return;
    }

    let ksy = `meta:\n  id: candidate_protocol\n  endian: ${framingType.includes('le') ? 'le' : 'be'}\nseq:\n`;
    if (framingType === 'len16_be') {
      const len = bytes.length >= 2 ? (bytes[0] << 8) | bytes[1] : 0;
      ksy += `  - id: payload_length\n    type: u2\n    # Observed length: ${len}\n`;
      ksy += `  - id: payload\n    size: payload_length\n`;
    } else if (framingType === 'len16_le') {
      const len = bytes.length >= 2 ? bytes[0] | (bytes[1] << 8) : 0;
      ksy += `  - id: payload_length\n    type: u2\n    # Observed length: ${len}\n`;
      ksy += `  - id: payload\n    size: payload_length\n`;
    } else if (framingType === 'tlv') {
      ksy += `  - id: tag\n    type: u1\n  - id: length\n    type: u1\n  - id: value\n    size: length\n`;
    } else {
      ksy += `  - id: cobs_data\n    type: strz\n    encoding: ASCII\n`;
    }

    setGeneratedKsy(ksy);
    onShowToast('Candidate Kaitai format generated!');
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">
            <span>🧩 Protocol Framing & Dissector Playground</span>
          </div>
          <div className="card-desc">
            Test candidate binary message framing heuristics and export starter Kaitai Struct specs (.ksy) or Wireshark Lua dissectors.
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 180px 120px', gap: '8px' }}>
        <input
          type="text"
          placeholder="Hex bytes (e.g. 00 0e 01 02 ...)"
          value={hexInput}
          onChange={e => setHexInput(e.target.value)}
        />
        <select value={framingType} onChange={e => setFramingType(e.target.value as any)}>
          <option value="len16_be">16-bit Length (BE)</option>
          <option value="len16_le">16-bit Length (LE)</option>
          <option value="tlv">Type-Length-Value (TLV)</option>
          <option value="cobs">COBS Delimited (0x00)</option>
        </select>
        <button className="btn btn-primary btn-sm" onClick={handleDissect}>
          Analyze Hex
        </button>
      </div>

      {generatedKsy && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>Candidate Kaitai Struct (.ksy):</span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                navigator.clipboard.writeText(generatedKsy);
                onShowToast('Copied Kaitai YAML to clipboard');
              }}
            >
              📋 Copy .ksy
            </button>
          </div>
          <pre className="code-view" style={{ maxHeight: '200px' }}>{generatedKsy}</pre>
        </div>
      )}
    </div>
  );
};
