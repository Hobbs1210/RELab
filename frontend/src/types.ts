export interface RequestEvent {
  id: number;
  ts: string;
  source_ip: string;
  method: string;
  host: string;
  path: string;
  headers: Record<string, string>;
  body_b64: string;
  response_status: number;
  rule_name: string | null;
  request_body_utf8?: string;
}

export interface MockRule {
  name: string;
  enabled?: boolean;
  method?: string;
  host_regex?: string;
  path_regex: string;
  status: number;
  headers?: Record<string, string>;
  body?: any;
  delay_ms?: number;
}

export interface ScenarioStep {
  method: string;
  host?: string;
  path_regex: string;
  status: number;
  body?: any;
  headers?: Record<string, string>;
  delay_ms?: number;
}

export interface Scenario {
  id: string;
  enabled: boolean;
  name?: string;
  steps: ScenarioStep[];
}

export interface ProfileInfo {
  active: string;
  profile: any;
  available: string[];
  automatic_dns_changes: boolean;
}

export interface McpServerInfo {
  id: string;
  name: string;
  port: number;
  url: string;
  status: 'online' | 'offline' | 'optional';
  toolsCount?: number;
  tools?: string[];
  description: string;
}

export interface SystemInfo {
  cpu_percent?: number;
  ram_percent?: number;
  disk_free_gb?: number;
  disk_total_gb?: number;
  active_containers?: string[];
  target_profile?: string;
}

export interface Experiment {
  id: string;
  name: string;
  hypothesis: string;
  created_at: string;
  finished_at?: string;
  state_snapshot?: any;
}

export interface AnalysisItem {
  id: string;
  filename: string;
  sha256?: string;
  timestamp?: string;
  summary?: any;
}
