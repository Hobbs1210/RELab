import React, { useState } from 'react';
import { Experiment, AnalysisItem } from '../types';
import { labFetch } from '../api';

interface ExperimentTimelineProps {
  experiments: Experiment[];
  analyses: AnalysisItem[];
  onRefresh: () => void;
  onShowToast: (msg: string) => void;
}

export const ExperimentTimeline: React.FC<ExperimentTimelineProps> = ({
  experiments,
  analyses,
  onRefresh,
  onShowToast,
}) => {
  const [expName, setExpName] = useState('');
  const [hypothesis, setHypothesis] = useState('');
  const [starting, setStarting] = useState(false);

  const handleStart = async () => {
    if (!expName.trim() || !hypothesis.trim()) {
      alert('Please provide both experiment name and hypothesis');
      return;
    }
    setStarting(true);
    try {
      const res = await labFetch('experiments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: expName, hypothesis })
      });
      onShowToast(`Experiment ${res.id} started with state snapshot`);
      setExpName('');
      setHypothesis('');
      onRefresh();
    } catch (err: any) {
      alert(`Failed to start experiment: ${err.message}`);
    } finally {
      setStarting(false);
    }
  };

  const handleRollback = async (eid: string) => {
    if (!confirm(`Rollback lab DNS and mock rules to snapshot of experiment "${eid}"?`)) return;
    try {
      await labFetch(`experiments/${eid}/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
      onShowToast(`Successfully rolled back to experiment ${eid}`);
      onRefresh();
    } catch (err: any) {
      alert(`Rollback failed: ${err.message}`);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">
            <span>⏱️ Experiment Snapshots & Rollback Timeline</span>
            <span className="badge badge-safe">{experiments.length} Recorded</span>
          </div>
          <div className="card-desc">
            Hypothesis-driven testing history. Snapshots record mock rules and managed DNS rewrites for instant one-click rollback.
          </div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={onRefresh}>🔄 Refresh</button>
      </div>

      {/* New Experiment Form */}
      <div style={{ background: '#050a14', padding: '14px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <span style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>Start New Hypothesis-Driven Experiment</span>
        <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 140px', gap: '8px' }}>
          <input
            type="text"
            placeholder="Experiment Name"
            value={expName}
            onChange={e => setExpName(e.target.value)}
          />
          <input
            type="text"
            placeholder="Hypothesis (e.g. Test if device falls back to NTP when HTTP 501 is returned)"
            value={hypothesis}
            onChange={e => setHypothesis(e.target.value)}
          />
          <button className="btn btn-primary btn-sm" onClick={handleStart} disabled={starting}>
            {starting ? 'Snapshotting...' : '📸 Start & Snapshot'}
          </button>
        </div>
      </div>

      {/* Experiment List */}
      <div className="grid-cols-2" style={{ marginTop: '8px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)' }}>Experiment Snapshots</span>
          {experiments.length === 0 ? (
            <div style={{ color: 'var(--text-sub)', fontSize: '12px', padding: '20px', textAlign: 'center' }}>
              No experiments recorded yet.
            </div>
          ) : (
            experiments.map((exp: any, i) => (
              <div key={exp.id || i} style={{ background: '#091220', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, color: '#fff', fontSize: '13px' }}>{exp.name || exp.id}</span>
                  <button className="btn btn-danger btn-sm" onClick={() => handleRollback(exp.id)}>
                    ↩️ Rollback
                  </button>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-sub)', marginTop: '4px' }}>
                  {exp.hypothesis || '(No hypothesis text)'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--accent-blue)', marginTop: '6px' }}>
                  ID: {exp.id} · {exp.created_at || 'Recorded'}
                </div>
              </div>
            ))
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)' }}>Zeek Capture Analyses</span>
          {analyses.length === 0 ? (
            <div style={{ color: 'var(--text-sub)', fontSize: '12px', padding: '20px', textAlign: 'center' }}>
              No Zeek analyses processed yet.
            </div>
          ) : (
            analyses.map((an: any, i) => (
              <div key={an.id || i} style={{ background: '#091220', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '10px' }}>
                <div style={{ fontWeight: 600, color: '#fff', fontSize: '12px' }}>{an.filename || an.id}</div>
                <div style={{ fontSize: '11px', color: 'var(--accent-cyan)', marginTop: '2px' }}>
                  SHA256: {an.sha256 ? an.sha256.slice(0, 16) + '...' : 'Available'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
