import React, { useState } from 'react';
import { MockRule } from '../types';

interface RuleBuilderProps {
  rules: MockRule[];
  onSaveRules: (rules: MockRule[]) => Promise<void>;
  onShowToast: (msg: string) => void;
}

export const RuleBuilder: React.FC<RuleBuilderProps> = ({ rules, onSaveRules, onShowToast }) => {
  const [activeTab, setActiveTab] = useState<'visual' | 'json'>('visual');
  const [jsonText, setJsonText] = useState(JSON.stringify(rules, null, 2));
  const [testRegexInput, setTestRegexInput] = useState('');
  const [saving, setSaving] = useState(false);

  // Sync JSON text when rules prop changes
  React.useEffect(() => {
    setJsonText(JSON.stringify(rules, null, 2));
  }, [rules]);

  const handleToggleRule = async (index: number) => {
    const updated = [...rules];
    updated[index] = { ...updated[index], enabled: updated[index].enabled === false ? true : false };
    await save(updated);
  };

  const handleDeleteRule = async (index: number) => {
    if (!confirm(`Delete rule "${rules[index].name}"?`)) return;
    const updated = rules.filter((_, i) => i !== index);
    await save(updated);
  };

  const handleAddRule = async () => {
    const newRule: MockRule = {
      name: `custom-rule-${rules.length + 1}`,
      enabled: true,
      method: 'GET',
      path_regex: '^/v1/status$',
      status: 200,
      headers: { 'content-type': 'application/json' },
      body: { status: 'ok', device_mode: 'active' },
      delay_ms: 0,
    };
    await save([...rules, newRule]);
  };

  const save = async (rulesToSave: MockRule[]) => {
    setSaving(true);
    try {
      await onSaveRules(rulesToSave);
      onShowToast('Mock response rules saved successfully');
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveJson = async () => {
    try {
      const parsed = JSON.parse(jsonText);
      if (!Array.isArray(parsed)) throw new Error('Rules must be a JSON array');
      await save(parsed);
    } catch (err: any) {
      alert(`Invalid JSON format: ${err.message}`);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">
            <span>⚙️ Mock Response Rules</span>
            <span className="badge badge-safe">{rules.length} Configured</span>
          </div>
          <div className="card-desc">
            Ordered response simulation engine. First matching enabled rule returns the response; unhandled routes yield HTTP 501.
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn btn-sm ${activeTab === 'visual' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('visual')}
          >
            Visual Form
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'json' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => {
              setJsonText(JSON.stringify(rules, null, 2));
              setActiveTab('json');
            }}
          >
            Raw JSON
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleAddRule} disabled={saving}>
            + Add Rule
          </button>
        </div>
      </div>

      {activeTab === 'visual' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Regex quick test */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', background: '#050a14', padding: '10px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-sub)' }}>🧪 Test Path:</span>
            <input
              type="text"
              placeholder="e.g. /v1/device/auth?token=123"
              value={testRegexInput}
              onChange={e => setTestRegexInput(e.target.value)}
              style={{ flex: 1 }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '550px', overflowY: 'auto' }}>
            {rules.map((rule, idx) => {
              let isMatch = false;
              if (testRegexInput) {
                try {
                  isMatch = new RegExp(rule.path_regex).test(testRegexInput);
                } catch {}
              }

              return (
                <div
                  key={idx}
                  style={{
                    background: rule.enabled === false ? '#09101d' : '#0b1629',
                    border: isMatch ? '1px solid var(--accent-emerald)' : '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '12px',
                    opacity: rule.enabled === false ? 0.6 : 1,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        className={`btn btn-sm ${rule.enabled !== false ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => handleToggleRule(idx)}
                      >
                        {rule.enabled !== false ? 'ENABLED' : 'DISABLED'}
                      </button>
                      <span style={{ fontWeight: 600, color: '#fff', fontSize: '13px' }}>{rule.name}</span>
                      {isMatch && <span className="badge badge-safe">MATCHES TEST PATH</span>}
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <span className="badge badge-blue">HTTP {rule.status}</span>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDeleteRule(idx)}>Delete</button>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr 120px', gap: '8px', fontSize: '12px', marginBottom: '8px' }}>
                    <div>
                      <span style={{ color: 'var(--text-sub)', fontSize: '11px' }}>Method:</span>
                      <div className="font-mono" style={{ color: 'var(--accent-cyan)' }}>{rule.method || 'ANY'}</div>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-sub)', fontSize: '11px' }}>Path Regex:</span>
                      <div className="font-mono" style={{ color: '#fff' }}>{rule.path_regex}</div>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-sub)', fontSize: '11px' }}>Delay:</span>
                      <div className="font-mono">{rule.delay_ms || 0} ms</div>
                    </div>
                  </div>

                  <div style={{ background: '#050a14', padding: '8px', borderRadius: '4px', fontSize: '11px', maxHeight: '100px', overflow: 'auto' }}>
                    <span style={{ color: 'var(--text-sub)' }}>Response Body: </span>
                    <span className="font-mono" style={{ color: '#cbd5e1' }}>
                      {typeof rule.body === 'object' ? JSON.stringify(rule.body) : String(rule.body || '(empty)')}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <textarea
            className="code-area"
            value={jsonText}
            onChange={e => setJsonText(e.target.value)}
            spellCheck={false}
          />
          <button className="btn btn-primary" onClick={handleSaveJson} disabled={saving}>
            {saving ? 'Saving...' : '💾 Save Response Rules'}
          </button>
        </div>
      )}
    </div>
  );
};
