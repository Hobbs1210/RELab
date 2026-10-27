import React, { useState } from 'react';
import { McpServerInfo } from '../types';

interface McpGridProps {
  servers: McpServerInfo[];
  hostIp?: string;
  onShowToast?: (msg: string) => void;
}

export const McpGrid: React.FC<McpGridProps> = ({ servers, hostIp, onShowToast }) => {
  const [selectedMcp, setSelectedMcp] = useState<McpServerInfo | null>(null);

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">
            <span>🔌 MCP Server Ecosystem</span>
            {hostIp && <span className="badge badge-blue">Host: {hostIp}</span>}
            <span className="badge badge-safe">{servers.filter(s => s.status === 'online').length} / {servers.length} Online</span>
          </div>
          <div className="card-desc">
            Model Context Protocol endpoints providing LLM tools to Antigravity, Claude Code, Codex, and VS Code.
          </div>
        </div>
      </div>

      <div className="grid-cols-4">
        {servers.map(server => (
          <div 
            key={server.id} 
            className="mcp-card"
            style={{ cursor: 'pointer' }}
            onClick={() => setSelectedMcp(server)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, fontSize: '13px', color: '#fff' }}>{server.name}</span>
              <span className={`mcp-status-dot dot-${server.status}`} title={`Status: ${server.status}`} />
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-sub)' }}>
              Port: <span className="font-mono" style={{ color: 'var(--accent-cyan)' }}>{server.port}</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--accent-blue)', wordBreak: 'break-all' }} className="font-mono">
              {server.url}
            </div>
            <div style={{ fontSize: '11px', color: '#cbd5e1', lineHeight: '1.4' }}>
              {server.description}
            </div>
            <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px' }}>
              <span style={{ color: 'var(--accent-blue)' }}>Click to view details</span>
              {server.toolsCount !== undefined && (
                <span className="badge badge-blue">{server.toolsCount} tools</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {selectedMcp && (
        <div className="modal-overlay" onClick={() => setSelectedMcp(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ color: '#fff', fontSize: '16px' }}>{selectedMcp.name} ({selectedMcp.id})</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedMcp(null)}>✕ Close</button>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-sub)' }}>{selectedMcp.description}</p>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600 }}>Endpoint URL:</span>
                {onShowToast && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      navigator.clipboard.writeText(selectedMcp.url);
                      onShowToast(`Copied ${selectedMcp.name} URL to clipboard`);
                    }}
                  >
                    Copy URL
                  </button>
                )}
              </div>
              <pre className="code-view" style={{ padding: '8px' }}>{selectedMcp.url}</pre>
            </div>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>Available Tools:</div>
              <ul style={{ paddingLeft: '20px', fontSize: '12px', color: '#cbd5e1', lineHeight: '1.6' }}>
                {selectedMcp.tools && selectedMcp.tools.length > 0 ? (
                  selectedMcp.tools.map(tool => <li key={tool} className="font-mono">{tool}</li>)
                ) : (
                  <li style={{ color: 'var(--text-sub)' }}>Standard read-only tools loaded dynamically during agent handshake.</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
