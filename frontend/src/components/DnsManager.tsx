import React, { useState } from 'react';
import { labFetch } from '../api';

interface DnsManagerProps {
  hostsText: string;
  onSaveHosts: (hosts: string) => Promise<void>;
  onShowToast: (msg: string) => void;
}

export const DnsManager: React.FC<DnsManagerProps> = ({ hostsText, onSaveHosts, onShowToast }) => {
  const [text, setText] = useState(hostsText);
  const [saving, setSaving] = useState(false);
  const [customDomain, setCustomDomain] = useState('');
  const [targetIp, setTargetIp] = useState('127.0.0.1');

  React.useEffect(() => {
    setText(hostsText);
  }, [hostsText]);

  const handleSave = async (contentToSave: string) => {
    setSaving(true);
    try {
      await onSaveHosts(contentToSave);
      onShowToast('DNS rewrites updated and synced to AdGuard Home');
    } catch (err: any) {
      alert(`DNS update failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleAddDomain = async (sinkhole = false) => {
    if (!customDomain.trim()) return;
    const ip = sinkhole ? '0.0.0.0' : targetIp;
    const newLine = `${ip} ${customDomain.trim()}`;
    const updated = text.trim() ? `${text.trim()}\n${newLine}\n` : `${newLine}\n`;
    setText(updated);
    await handleSave(updated);
    setCustomDomain('');
  };

  const handleDisableAll = async () => {
    const disabled = '# Lab-managed DNS rewrites disabled\n';
    setText(disabled);
    await handleSave(disabled);
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">
            <span>🌐 Lab DNS Rewrites (AdGuard Home)</span>
          </div>
          <div className="card-desc">
            Directs target device domain lookups to the lab IP or sinkholes telemetry. Keep rewrites disabled until passive baseline capture is complete.
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-danger btn-sm" onClick={handleDisableAll} disabled={saving}>
            🛑 Disable All Rewrites
          </button>
          <a href="http://127.0.0.1:3000" target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">
            Open AdGuard Web UI ↗
          </a>
        </div>
      </div>

      {/* Quick Add Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 140px 100px 100px', gap: '8px', alignItems: 'center', background: '#050a14', padding: '12px', borderRadius: '6px' }}>
        <input
          type="text"
          placeholder="Domain to redirect (e.g. api.devicevendor.com)"
          value={customDomain}
          onChange={e => setCustomDomain(e.target.value)}
        />
        <input
          type="text"
          placeholder="Target IP"
          value={targetIp}
          onChange={e => setTargetIp(e.target.value)}
        />
        <button className="btn btn-primary btn-sm" onClick={() => handleAddDomain(false)}>
          Redirect
        </button>
        <button className="btn btn-secondary btn-sm" onClick={() => handleAddDomain(true)}>
          Sinkhole
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ fontSize: '12px', color: 'var(--text-sub)' }}>
          Standard <span className="font-mono">/etc/hosts</span> format (synced directly with AdGuard filter engine):
        </div>
        <textarea
          className="code-area"
          style={{ minHeight: '180px' }}
          value={text}
          onChange={e => setText(e.target.value)}
          spellCheck={false}
        />
        <button className="btn btn-primary" onClick={() => handleSave(text)} disabled={saving}>
          {saving ? 'Syncing...' : '💾 Save & Apply DNS Hosts'}
        </button>
      </div>
    </div>
  );
};
