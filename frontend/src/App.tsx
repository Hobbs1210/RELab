import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { McpGrid } from './components/McpGrid';
import { TrafficInspector } from './components/TrafficInspector';
import { RuleBuilder } from './components/RuleBuilder';
import { DnsManager } from './components/DnsManager';
import { CaTrustCenter } from './components/CaTrustCenter';
import { ProtocolPlayground } from './components/ProtocolPlayground';
import { HardwareRadar } from './components/HardwareRadar';
import { ExperimentTimeline } from './components/ExperimentTimeline';
import { ReportExporter } from './components/ReportExporter';
import { IdeHelperModal } from './components/IdeHelperModal';
import { labFetch } from './api';
import {
  RequestEvent,
  MockRule,
  ProfileInfo,
  McpServerInfo,
  Experiment,
  AnalysisItem,
} from './types';
import './styles.css';

const DEFAULT_MCP_SERVERS: McpServerInfo[] = [
  { id: 'device-dns', name: 'AdGuard DNS', port: 8301, url: 'http://127.0.0.1:8301/', status: 'online', description: 'AdGuard Home DNS rewrite inspection & testing' },
  { id: 'device-mitm', name: 'mitmproxy', port: 8302, url: 'http://127.0.0.1:8302/mcp', status: 'online', description: 'HTTP/HTTPS stream inspection and flows' },
  { id: 'device-pcap', name: 'Wireshark PCAP', port: 8303, url: 'http://127.0.0.1:8303/mcp', status: 'online', description: 'Offline packet forensics & TShark dissection' },
  { id: 'device-ble', name: 'Bluetooth LE', port: 8304, url: 'http://127.0.0.1:8304/mcp', status: 'online', description: 'BLE adapter discovery & GATT characteristic reading' },
  { id: 'device-docker', name: 'Docker Proxy', port: 8305, url: 'http://127.0.0.1:8305/mcp', status: 'online', description: 'Docker container status and health inspection' },
  { id: 'device-api', name: 'Device Mock API', port: 8090, url: 'http://127.0.0.1:8090/mcp', status: 'online', description: 'Mock device HTTP API simulation & rule engine' },
  { id: 'device-workbench', name: 'Protocol Workbench', port: 8310, url: 'http://127.0.0.1:8310/mcp', status: 'online', description: 'Universal protocol framing heuristics & candidate SDKs' },
  { id: 'device-research', name: 'Research Hub', port: 8320, url: 'http://127.0.0.1:8320/mcp', status: 'online', description: 'Durable jobs, evidence database, and pipelines' },
  { id: 'device-ghidra', name: 'Ghidra Decompiler', port: 8306, url: 'http://127.0.0.1:8306/mcp', status: 'optional', description: 'Offline firmware reverse engineering (opt-in profile)' },
];

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'traffic' | 'mcp' | 'rules' | 'dns' | 'ca' | 'protocol' | 'experiments'>('traffic');
  const [profile, setProfile] = useState<ProfileInfo | null>(null);
  const [events, setEvents] = useState<RequestEvent[]>([]);
  const [rules, setRules] = useState<MockRule[]>([]);
  const [hostsText, setHostsText] = useState('');
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisItem[]>([]);
  const [isIdeModalOpen, setIsIdeModalOpen] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => {
      setToastMsg(prev => (prev === msg ? null : prev));
    }, 3500);
  };

  const loadInitialData = useCallback(async () => {
    try {
      const [profData, rulesData, dnsData, expData, anaData] = await Promise.allSettled([
        labFetch<ProfileInfo>('profile'),
        labFetch<{ rules: MockRule[] }>('rules'),
        labFetch<{ hosts: string }>('dns'),
        labFetch<{ experiments: Experiment[] }>('experiments'),
        labFetch<{ analyses: AnalysisItem[] }>('analyses'),
      ]);

      if (profData.status === 'fulfilled') setProfile(profData.value);
      if (rulesData.status === 'fulfilled') setRules(rulesData.value.rules || []);
      if (dnsData.status === 'fulfilled') setHostsText(dnsData.value.hosts || '');
      if (expData.status === 'fulfilled') setExperiments(expData.value.experiments || []);
      if (anaData.status === 'fulfilled') setAnalyses(anaData.value.analyses || []);
    } catch (err: any) {
      console.warn('Initial data load error:', err);
    }
  }, []);

  const loadEvents = useCallback(async () => {
    try {
      const res = await labFetch<{ events: RequestEvent[] }>('events?limit=150');
      if (res && res.events) {
        setEvents(res.events);
      }
    } catch {
      // ignore transient poll errors
    }
  }, []);

  useEffect(() => {
    loadInitialData();
    loadEvents();
    const interval = setInterval(loadEvents, 4000);
    return () => clearInterval(interval);
  }, [loadInitialData, loadEvents]);

  const handleSaveRules = async (newRules: MockRule[]) => {
    await labFetch('rules', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newRules),
    });
    setRules(newRules);
  };

  const handleSaveHosts = async (hosts: string) => {
    await labFetch('dns', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hosts }),
    });
    setHostsText(hosts);
  };

  const handleClearJournal = async () => {
    if (!confirm('Clear all recorded HTTP requests from the journal database?')) return;
    try {
      await labFetch('events', { method: 'DELETE' });
      setEvents([]);
      showToast('Request journal cleared');
    } catch (err: any) {
      alert(`Clear failed: ${err.message}`);
    }
  };

  const handleAdoptRule = (rule: MockRule) => {
    setRules(prev => [rule, ...prev]);
    setActiveTab('rules');
  };

  return (
    <div className="app-container">
      <Header
        profile={profile}
        onOpenIdeModal={() => setIsIdeModalOpen(true)}
        onRefresh={() => {
          loadInitialData();
          loadEvents();
        }}
        onShowToast={showToast}
      />

      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'traffic' ? 'active' : ''}`}
          onClick={() => setActiveTab('traffic')}
        >
          📡 Live Traffic Journal ({events.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'mcp' ? 'active' : ''}`}
          onClick={() => setActiveTab('mcp')}
        >
          🔌 9-MCP Ecosystem
        </button>
        <button
          className={`tab-btn ${activeTab === 'rules' ? 'active' : ''}`}
          onClick={() => setActiveTab('rules')}
        >
          ⚙️ Mock Rules ({rules.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'dns' ? 'active' : ''}`}
          onClick={() => setActiveTab('dns')}
        >
          🌐 DNS Rewrites
        </button>
        <button
          className={`tab-btn ${activeTab === 'ca' ? 'active' : ''}`}
          onClick={() => setActiveTab('ca')}
        >
          📜 CA & Device Trust
        </button>
        <button
          className={`tab-btn ${activeTab === 'protocol' ? 'active' : ''}`}
          onClick={() => setActiveTab('protocol')}
        >
          🧩 Framing & Hardware
        </button>
        <button
          className={`tab-btn ${activeTab === 'experiments' ? 'active' : ''}`}
          onClick={() => setActiveTab('experiments')}
        >
          ⏱️ Experiments & Report
        </button>
      </nav>

      <main className="content-area">
        {activeTab === 'traffic' && (
          <TrafficInspector
            events={events}
            onRefresh={loadEvents}
            onClear={handleClearJournal}
            onAdoptAsRule={handleAdoptRule}
            onShowToast={showToast}
          />
        )}

        {activeTab === 'mcp' && (
          <McpGrid servers={DEFAULT_MCP_SERVERS} />
        )}

        {activeTab === 'rules' && (
          <RuleBuilder
            rules={rules}
            onSaveRules={handleSaveRules}
            onShowToast={showToast}
          />
        )}

        {activeTab === 'dns' && (
          <DnsManager
            hostsText={hostsText}
            onSaveHosts={handleSaveHosts}
            onShowToast={showToast}
          />
        )}

        {activeTab === 'ca' && (
          <CaTrustCenter onShowToast={showToast} />
        )}

        {activeTab === 'protocol' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <ProtocolPlayground onShowToast={showToast} />
            <HardwareRadar />
          </div>
        )}

        {activeTab === 'experiments' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <ExperimentTimeline
              experiments={experiments}
              analyses={analyses}
              onRefresh={loadInitialData}
              onShowToast={showToast}
            />
            <ReportExporter
              profile={profile}
              events={events}
              rules={rules}
              experiments={experiments}
              onShowToast={showToast}
            />
          </div>
        )}
      </main>

      {isIdeModalOpen && (
        <IdeHelperModal
          onClose={() => setIsIdeModalOpen(false)}
          onShowToast={showToast}
        />
      )}

      {toastMsg && (
        <div className="toast">
          <span>{toastMsg}</span>
        </div>
      )}
    </div>
  );
};
