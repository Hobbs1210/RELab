import React, { useState, useMemo } from 'react';
import { RequestEvent, MockRule } from '../types';

interface TrafficInspectorProps {
  events: RequestEvent[];
  onRefresh: () => void;
  onClear: () => void;
  onAdoptAsRule: (rule: MockRule) => void;
  onShowToast: (msg: string) => void;
}

export const TrafficInspector: React.FC<TrafficInspectorProps> = ({
  events,
  onRefresh,
  onClear,
  onAdoptAsRule,
  onShowToast,
}) => {
  const [filterText, setFilterText] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<RequestEvent | null>(null);
  const [viewFormat, setViewFormat] = useState<'json' | 'raw' | 'hex'>('json');

  const filteredEvents = useMemo(() => {
    if (!filterText.trim()) return events;
    const lower = filterText.toLowerCase();
    return events.filter(e =>
      e.host.toLowerCase().includes(lower) ||
      e.path.toLowerCase().includes(lower) ||
      e.method.toLowerCase().includes(lower) ||
      e.source_ip.includes(lower) ||
      (e.rule_name && e.rule_name.toLowerCase().includes(lower))
    );
  }, [events, filterText]);

  const handleAdopt = (ev: RequestEvent) => {
    // Generate an escaped path regex from literal path
    const escapedPath = '^' + ev.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '$';
    const newRule: MockRule = {
      name: `mock-${ev.method.toLowerCase()}-${ev.path.replace(/[^a-zA-Z0-9]/g, '_').slice(0, 30)}`,
      enabled: true,
      method: ev.method,
      path_regex: escapedPath,
      status: 200,
      headers: { 'content-type': 'application/json' },
      body: { message: 'simulated response', original_path: ev.path },
      delay_ms: 0,
    };
    onAdoptAsRule(newRule);
    onShowToast(`Created mock rule template for ${ev.method} ${ev.path}`);
  };

  const copyAsCurl = (ev: RequestEvent) => {
    let curl = `curl -k -X ${ev.method} "https://${ev.host}${ev.path}"`;
    for (const [k, v] of Object.entries(ev.headers || {})) {
      if (!['host', 'content-length'].includes(k.toLowerCase())) {
        curl += ` -H "${k}: ${v}"`;
      }
    }
    if (ev.body_b64) {
      try {
        const bodyStr = atob(ev.body_b64);
        curl += ` --data '${bodyStr.replace(/'/g, "'\\''")}'`;
      } catch {
        // ignore
      }
    }
    navigator.clipboard.writeText(curl);
    onShowToast('Copied cURL command to clipboard!');
  };

  const formatHex = (b64: string): string => {
    try {
      const raw = atob(b64);
      let out = '';
      for (let i = 0; i < raw.length; i += 16) {
        const slice = raw.slice(i, i + 16);
        const hex = Array.from(slice)
          .map(c => c.charCodeAt(0).toString(16).padStart(2, '0'))
          .join(' ');
        const ascii = Array.from(slice)
          .map(c => (c.charCodeAt(0) >= 32 && c.charCodeAt(0) <= 126 ? c : '.'))
          .join('');
        out += `${i.toString(16).padStart(6, '0')}  ${hex.padEnd(48, ' ')}  |${ascii}|\n`;
      }
      return out || 'Empty body';
    } catch {
      return 'Unable to decode base64 body as hex';
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">
            <span>📡 Live Device Request Journal</span>
            <span className="badge badge-safe">{events.length} Observed</span>
          </div>
          <div className="card-desc">
            Captures HTTP/HTTPS requests completing TLS at the RELab edge with raw headers and payloads.
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={onRefresh}>🔄 Refresh</button>
          <button className="btn btn-danger btn-sm" onClick={onClear}>🗑️ Clear</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Filter by IP, method, domain, path regex, or rule name..."
          value={filterText}
          onChange={e => setFilterText(e.target.value)}
        />
        {filterText && (
          <button className="btn btn-secondary btn-sm" onClick={() => setFilterText('')}>✕ Clear</button>
        )}
      </div>

      <div className="grid-cols-2" style={{ marginTop: '8px' }}>
        {/* Left: Request List */}
        <div style={{ maxHeight: '550px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {filteredEvents.length === 0 ? (
            <div style={{ color: 'var(--text-sub)', padding: '24px', textAlign: 'center', fontSize: '13px' }}>
              No incoming requests observed yet. Ensure device DNS or Wi-Fi is directed to lab edge.
            </div>
          ) : (
            filteredEvents.map(ev => {
              const statusClass = ev.response_status < 400 ? 'status-2xx' : (ev.response_status < 500 ? 'status-4xx' : 'status-5xx');
              const isSelected = selectedEvent?.id === ev.id;
              return (
                <div
                  key={ev.id}
                  className={`event-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => setSelectedEvent(ev)}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'hidden' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontWeight: 700, fontSize: '11px', color: 'var(--accent-cyan)' }}>{ev.method}</span>
                      <span style={{ fontWeight: 600, fontSize: '12px', color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {ev.host}{ev.path}
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-sub)' }}>
                      #{ev.id} · {ev.ts} · {ev.source_ip}
                      {ev.rule_name && <span style={{ color: 'var(--accent-purple)', marginLeft: '6px' }}>[{ev.rule_name}]</span>}
                    </div>
                  </div>
                  <div>
                    <span className={`status-tag ${statusClass}`}>{ev.response_status}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right: Selected Event Details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {selectedEvent ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ fontWeight: 600, fontSize: '13px', color: '#fff' }}>
                  Request #{selectedEvent.id} Details
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button className="btn btn-primary btn-sm" onClick={() => handleAdopt(selectedEvent)}>
                    ⚡ Adopt as Mock Rule
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => copyAsCurl(selectedEvent)}>
                    📋 Copy cURL
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '6px', fontSize: '12px' }}>
                <button
                  className={`btn btn-sm ${viewFormat === 'json' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setViewFormat('json')}
                >
                  JSON Tree
                </button>
                <button
                  className={`btn btn-sm ${viewFormat === 'raw' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setViewFormat('raw')}
                >
                  Decoded UTF-8
                </button>
                <button
                  className={`btn btn-sm ${viewFormat === 'hex' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setViewFormat('hex')}
                >
                  Hex Dump
                </button>
              </div>

              <pre className="code-view">
                {viewFormat === 'json' && (() => {
                  const data: any = { ...selectedEvent };
                  try { data.request_body_utf8 = atob(selectedEvent.body_b64); } catch {}
                  return JSON.stringify(data, null, 2);
                })()}
                {viewFormat === 'raw' && (() => {
                  try {
                    return atob(selectedEvent.body_b64) || '(Empty Body)';
                  } catch {
                    return '(Binary Body - Cannot decode as UTF-8)';
                  }
                })()}
                {viewFormat === 'hex' && formatHex(selectedEvent.body_b64)}
              </pre>
            </>
          ) : (
            <div style={{ color: 'var(--text-sub)', padding: '40px', textAlign: 'center', background: '#050a14', borderRadius: '6px' }}>
              Select a request on the left to inspect headers, payload, and adopt as a mock rule.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
