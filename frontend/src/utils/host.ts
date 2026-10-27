export function getBrowserHost(): { rawHost: string; host: string } {
  const rawHost = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : '127.0.0.1';
  const host = rawHost.includes(':') && !rawHost.startsWith('[') ? `[${rawHost}]` : rawHost;
  return { rawHost, host };
}
