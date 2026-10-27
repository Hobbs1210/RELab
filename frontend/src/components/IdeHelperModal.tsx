import React, { useState } from 'react';

interface IdeHelperModalProps {
  onClose: () => void;
  onShowToast: (msg: string) => void;
}

export const IdeHelperModal: React.FC<IdeHelperModalProps> = ({ onClose, onShowToast }) => {
  const [activeTab, setActiveTab] = useState<'antigravity' | 'claude' | 'codex' | 'vscode'>('antigravity');

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    onShowToast(`Copied ${label} snippet to clipboard`);
  };

  const sshCmd = `ssh -N -L 8090:127.0.0.1:8090 -L 8301:127.0.0.1:8301 \\
  -L 8302:127.0.0.1:8302 -L 8303:127.0.0.1:8303 \\
  -L 8304:127.0.0.1:8304 -L 8305:127.0.0.1:8305 \\
  -L 8310:127.0.0.1:8310 -L 8320:127.0.0.1:8320 re@DEBIAN_IP`;

  const antigravitySnippet = `{
  "mcpServers": {
    "device-dns": { "serverUrl": "http://127.0.0.1:8301/" },
    "device-mitm": { "serverUrl": "http://127.0.0.1:8302/mcp" },
    "device-pcap": { "serverUrl": "http://127.0.0.1:8303/mcp" },
    "device-ble": { "serverUrl": "http://127.0.0.1:8304/mcp" },
    "device-docker": { "serverUrl": "http://127.0.0.1:8305/mcp" },
    "device-api": { "serverUrl": "http://127.0.0.1:8090/mcp" },
    "device-workbench": { "serverUrl": "http://127.0.0.1:8310/mcp" },
    "device-research": { "serverUrl": "http://127.0.0.1:8320/mcp" },
    "device-ghidra": { "serverUrl": "http://127.0.0.1:8306/mcp" }
  }
}`;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ color: '#fff', fontSize: '16px' }}>🤖 IDE & AI Agent MCP Setup Guide</h3>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕ Close</button>
        </div>

        {/* SSH Port forwarding notice */}
        <div style={{ background: '#050a14', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent-cyan)' }}>
              🔑 Remote SSH Port-Forwarding (Laptop ➔ Debian Host)
            </span>
            <button className="btn btn-secondary btn-sm" onClick={() => copy(sshCmd, 'SSH Tunnel')}>Copy SSH</button>
          </div>
          <pre className="code-view" style={{ fontSize: '11px', padding: '8px' }}>{sshCmd}</pre>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button className={`btn btn-sm ${activeTab === 'antigravity' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('antigravity')}>
            Google Antigravity
          </button>
          <button className={`btn btn-sm ${activeTab === 'claude' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('claude')}>
            Claude Code
          </button>
          <button className={`btn btn-sm ${activeTab === 'codex' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('codex')}>
            Codex CLI
          </button>
          <button className={`btn btn-sm ${activeTab === 'vscode' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('vscode')}>
            VS Code Remote-SSH
          </button>
        </div>

        {/* Tab content */}
        <div>
          {activeTab === 'antigravity' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-sub)' }}>
                Antigravity natively loads <span className="font-mono">.agents/mcp_config.json</span> in the workspace:
              </div>
              <pre className="code-view">{antigravitySnippet}</pre>
            </div>
          )}
          {activeTab === 'claude' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-sub)' }}>
                Register servers in Claude Desktop or Claude Code CLI using the automated script:
              </div>
              <pre className="code-view">bash scripts/register-claude.sh</pre>
            </div>
          )}
          {activeTab === 'codex' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-sub)' }}>
                Register servers with Codex CLI via the preconfigured script:
              </div>
              <pre className="code-view">bash scripts/register-codex.sh</pre>
            </div>
          )}
          {activeTab === 'vscode' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-sub)' }}>
                Open <span className="font-mono">/opt/RELab</span> via VS Code Remote-SSH. Server config is preloaded at <span className="font-mono">.vscode/mcp.json</span>.
              </div>
              <pre className="code-view">code --remote ssh-remote+re@DEBIAN_IP /opt/RELab</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
