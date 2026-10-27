import React from 'react';

interface CaTrustCenterProps {
  onShowToast: (msg: string) => void;
}

export const CaTrustCenter: React.FC<CaTrustCenterProps> = ({ onShowToast }) => {
  const downloadCert = (fmt: 'crt' | 'der' | 'android') => {
    window.open(`/__lab__/ca/download/${fmt}`, '_blank');
    onShowToast(`Downloading CA certificate (${fmt.toUpperCase()})`);
  };

  const copySnippet = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    onShowToast(`Copied ${label} snippet to clipboard`);
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">
            <span>📜 CA Trust & Device Interception Center</span>
          </div>
          <div className="card-desc">
            Download RELab root CA certificates or install trust anchors into test devices to inspect TLS traffic cleanly.
          </div>
        </div>
      </div>

      {/* Downloads */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <button className="btn btn-primary" onClick={() => downloadCert('crt')}>
          📥 Download CA (.crt / PEM)
        </button>
        <button className="btn btn-secondary" onClick={() => downloadCert('der')}>
          📥 Download CA (.der / Binary)
        </button>
        <button className="btn btn-secondary" onClick={() => downloadCert('android')}>
          📥 Download Android Magisk Cert
        </button>
      </div>

      {/* Quick Setup Guides */}
      <div className="grid-cols-2" style={{ marginTop: '12px' }}>
        <div style={{ background: '#050a14', padding: '14px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: '13px', color: '#fff' }}>🤖 Android / Magisk System Trust</span>
            <button className="btn btn-secondary btn-sm" onClick={() => copySnippet('adb push certs/export/*.0 /system/etc/security/cacerts/ && adb shell chmod 644 /system/etc/security/cacerts/*.0', 'Android')}>Copy</button>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-sub)' }}>
            Place the exported hashed certificate in the system trust store using root or Magisk module:
          </div>
          <pre className="code-view" style={{ fontSize: '11px', padding: '8px' }}>
{`adb root && adb remount
adb push certs/export/*.0 /system/etc/security/cacerts/
adb shell chmod 644 /system/etc/security/cacerts/*.0`}
          </pre>
        </div>

        <div style={{ background: '#050a14', padding: '14px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: '13px', color: '#fff' }}>🐍 Python / Linux Client Trust</span>
            <button className="btn btn-secondary btn-sm" onClick={() => copySnippet('export SSL_CERT_FILE=/opt/RELab/certs/export/device-mitm-ca.crt\nexport REQUESTS_CA_BUNDLE=$SSL_CERT_FILE', 'Python/Linux')}>Copy</button>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-sub)' }}>
            Instruct curl, Python requests, or Node.js test scripts to trust the lab CA:
          </div>
          <pre className="code-view" style={{ fontSize: '11px', padding: '8px' }}>
{`export SSL_CERT_FILE=/opt/RELab/certs/export/device-mitm-ca.crt
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
curl --cacert /opt/RELab/certs/export/device-mitm-ca.crt https://api.device.com`}
          </pre>
        </div>
      </div>
    </div>
  );
};
