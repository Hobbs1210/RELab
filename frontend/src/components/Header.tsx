import React, { useState } from 'react';
import { ProfileInfo } from '../types';
import { labFetch } from '../api';

interface HeaderProps {
  profile: ProfileInfo | null;
  onOpenIdeModal: () => void;
  onRefresh: () => void;
  onShowToast: (msg: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ profile, onOpenIdeModal, onRefresh, onShowToast }) => {
  const [killing, setKilling] = useState(false);
  const rawHost = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : '127.0.0.1';
  const host = rawHost.includes(':') && !rawHost.startsWith('[') ? `[${rawHost}]` : rawHost;

  const handleKillswitch = async () => {
    if (!confirm('EMERGENCY KILLSWITCH:\nThis will immediately disable all DNS rewrites, clear stateful sessions, and restore safe defaults. Proceed?')) {
      return;
    }
    setKilling(true);
    try {
      // 1. Disable DNS
      await labFetch('dns', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hosts: '# Emergency Killswitch activated: all rewrites disabled\n' })
      });
      // 2. Reset scenarios
      await labFetch('scenarios/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
      onShowToast('🛡️ Killswitch executed: DNS rewrites disabled & sessions reset.');
      onRefresh();
    } catch (err: any) {
      alert(`Killswitch failed: ${err.message}`);
    } finally {
      setKilling(false);
    }
  };

  return (
    <header>
      <div className="header-inner">
        <div className="brand-section">
          <div className="brand-title">
            <span>🛠️ RELab</span>
            <span style={{ color: 'var(--text-sub)', fontWeight: 400, fontSize: '14px' }}>| Operations Hub</span>
          </div>
          {profile && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span className="badge badge-safe">Profile: {profile.active}</span>
              <span className="badge badge-blue">Safety: Observing</span>
            </div>
          )}
        </div>

        <div className="nav-links">
          <a href={`http://${host}:3000`} target="_blank" rel="noreferrer" className="nav-link" title="AdGuard Home DNS Web Interface">
            🌐 DNS (3000)
          </a>
          <a href={`http://${host}:8310`} target="_blank" rel="noreferrer" className="nav-link" title="Universal Protocol Workbench">
            🔬 Workbench (8310)
          </a>
          <a href={`http://${host}:8320`} target="_blank" rel="noreferrer" className="nav-link" title="Integrated Research Hub">
            📊 Research (8320)
          </a>
          <a href={`http://${host}:8443`} target="_blank" rel="noreferrer" className="nav-link" title="Browser VS Code Server">
            💻 Code IDE (8443)
          </a>
          <a href="/docs" target="_blank" rel="noreferrer" className="nav-link" title="Interactive OpenAPI Swagger">
            📑 API Docs
          </a>
          <button onClick={onOpenIdeModal} className="btn btn-secondary btn-sm" title="IDE and Agent Configuration Guide">
            🤖 IDE / MCP Config
          </button>
          <button 
            onClick={handleKillswitch} 
            disabled={killing}
            className="btn btn-danger btn-sm"
            title="Immediately disable all DNS rewrites and reset simulator state"
          >
            {killing ? 'Resetting...' : '🛑 Kill Switch'}
          </button>
        </div>
      </div>
    </header>
  );
};
