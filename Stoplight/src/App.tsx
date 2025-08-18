import { useState } from 'react'
import './App.css'
import './index.css'

// Data models
export type Category = 'ingestion' | 'processing' | 'handling' | 'docker'

interface Service {
  id: string
  name: string
  port?: string
  category: Category
  description?: string
  dockerized?: boolean
  status?: 'up' | 'down'
  startup?: string[]
  logPath?: string
  configPath?: string
  docs?: string // documentation reference (now required for all entries we create)
  notes?: string
  site?: string // URL to web UI if applicable
}

interface HostNode {
  id: string
  name: string
  ip: string
  services: Service[]
  group?: string // e.g. FM-1 group label etc.
  notes?: string
}

// Example data approximating the provided diagram
const hosts: HostNode[] = [
  {
    id: 'crash',
    name: 'Crash',
    ip: '10.129.47.227',
    services: [
      { id: 'json-recv', name: 'JSON Receive Code', port: ':50000', category: 'ingestion', description: 'Receives JSON payloads from field modules.', status: 'up', startup: ['Ensure dependencies installed', 'Start service: systemctl start json-recv', 'Verify listening on :50000'], logPath: '/var/log/json-recv.log', configPath: '/etc/json-recv/config.yml', docs: '/docs/json-recv.md' },
      { id: 'watch-tower', name: 'Watch Tower', category: 'ingestion', description: 'Monitoring / supervisory ingestion layer.', status: 'up', startup: ['systemctl start watchtower', 'Check health endpoint /health'], logPath: '/var/log/watchtower.log', docs: '/docs/watch-tower.md' },
      { id: 'ndjson', name: 'NDJSON Script', category: 'processing', description: 'Parses newline-delimited JSON into structured events.', status: 'up', startup: ['python3 ndjson_consumer.py &'], configPath: '/opt/ndjson/config.ini', docs: '/docs/ndjson-script.md' },
      { id: 'filebeats', name: 'Filebeats', category: 'processing', description: 'Ship logs to log pipeline.', status: 'down', startup: ['systemctl start filebeat', 'filebeat test output'], logPath: '/var/log/filebeat/filebeat', configPath: '/etc/filebeat/filebeat.yml', docs: 'https://www.elastic.co/guide/en/beats/filebeat/current/index.html' },
      { id: 'zeek', name: 'Zeek', category: 'processing', description: 'Network security monitoring system extracting metadata from traffic.', status: 'up', startup: ['zeekctl deploy', 'zeekctl status'], logPath: '/opt/zeek/logs/current/', docs: 'https://docs.zeek.org/' },
      { id: 'suricata', name: 'Suricata', category: 'processing', description: 'IDS/IPS engine performing deep packet inspection.', status: 'up', startup: ['systemctl start suricata', 'suricata -T (config test)'], logPath: '/var/log/suricata/', configPath: '/etc/suricata/suricata.yaml', docs: 'https://docs.suricata.io/' },
      { id: 'pcap-roll', name: 'PCAP Data Rollover', category: 'handling', description: 'Rotates PCAP capture files to NAS storage.', status: 'up', startup: ['cron handles rotation automatically'], notes: 'Check disk usage weekly.', docs: '/docs/pcap-rollover.md' },
      { id: 'py-dash', name: 'Python Dashboard', category: 'handling', description: 'Custom analytics dashboard.', status: 'down', startup: ['pip install -r requirements.txt', 'python app.py'], logPath: '/var/log/py-dash/app.log', docs: '/docs/python-dashboard.md', site: 'https://dashboard.internal/' }
    ],
    notes: 'Primary sensor & ingest host.'
  },
  {
    id: 'onix',
    name: 'Onix',
    ip: '10.129.47.225',
    services: [
      { id: 'logstash', name: 'Logstash', port: ':5601', category: 'processing', description: 'Pipelines events into Elasticsearch.', dockerized: true, status: 'up', startup: ['docker compose up -d logstash', 'Check logs for pipeline started'], configPath: '/docker/elk/logstash/pipeline.conf', docs: 'https://www.elastic.co/guide/en/logstash/current/index.html' },
      { id: 'elastic', name: 'Elastic', port: ':9200', category: 'handling', description: 'Data store & search engine.', dockerized: true, status: 'up', startup: ['docker compose up -d elasticsearch', 'curl :9200/_cluster/health'], docs: 'https://www.elastic.co/guide/' },
      { id: 'kibana', name: 'Kibana', port: ':443', category: 'handling', description: 'Visualization and exploration UI.', dockerized: true, status: 'down', startup: ['docker compose up -d kibana', 'Open UI to confirm'], docs: 'https://www.elastic.co/guide/en/kibana/current/index.html', site: 'https://kibana.internal/' }
    ],
    notes: 'Elastic stack core.'
  },
  {
    id: 'abra',
    name: 'Abra',
    ip: '10.129.47.230',
    services: [
      { id: 'glpi', name: 'GLPI', port: ':443', category: 'handling', description: 'ITSM / asset management.', status: 'up', startup: ['docker compose up -d glpi'], docs: 'https://glpi-project.org/', site: 'https://glpi.internal/' },
      { id: 'opencti', name: 'OpenCTI', port: ':8443', category: 'handling', description: 'Cyber threat intelligence platform.', dockerized: true, status: 'up', startup: ['docker compose up -d opencti', 'Check web UI'], docs: 'https://www.opencti.io/', site: 'https://opencti.internal:8443/' }
    ],
    notes: 'Management & intel host.'
  },
  {
    id: 'nas1',
    name: 'IAES-NAS-1',
    ip: '10.129.47.231',
    services: [
      { id: 'pcap-store', name: 'PCAP Storage', port: ':21', category: 'ingestion', description: 'Stores rolled over packet captures.', status: 'up', notes: 'FTP service restricted to local network.', docs: '/docs/pcap-storage.md' }
    ]
  },
  {
    id: 'nas2',
    name: 'IAES-NAS-2',
    ip: '10.129.47.232',
    services: [
      { id: 'db-store', name: 'Database Storage', port: ':21', category: 'handling', description: 'Persistent database volume storage.', status: 'up', notes: 'Mounted via NFS.', docs: '/docs/db-storage.md' }
    ]
  }
]

const categoryLabels: Record<Category, string> = {
  ingestion: 'Ingestion',
  processing: 'Processing',
  handling: 'Handling',
  docker: 'Docker'
}

const categoryColors: Record<Category, string> = {
  ingestion: 'var(--cat-ingestion)',
  processing: 'var(--cat-processing)',
  handling: 'var(--cat-handling)',
  docker: 'var(--cat-docker)'
}

interface DrawerState {
  host?: HostNode
  service?: Service
  open: boolean
}

function App() {
  const [drawer, setDrawer] = useState<DrawerState>({ open: false })
  const [filter, setFilter] = useState<Category | 'all'>('all')

  const openHost = (host: HostNode) => {
    setDrawer({ host, service: undefined, open: true })
  }
  const openService = (host: HostNode, service: Service) => {
    setDrawer({ host, service, open: true })
  }
  const closeDrawer = () => setDrawer({ open: false })

  return (
    <div className="layout">
      <Header />
      <div className="legend">
        <span className="legend-title">Categories:</span>
        {(['all', 'ingestion', 'processing', 'handling', 'docker'] as const).map(c => (
          <button key={c} className={"legend-chip" + (filter === c ? ' active' : '')}
            style={c !== 'all' ? { ['--chip-color' as any]: categoryColors[c] } : {}}
            onClick={() => setFilter(c)}>{c === 'all' ? 'All' : categoryLabels[c]}</button>
        ))}
      </div>
      <div className="content-wrap">
        <main className="diagram-area" aria-label="Infrastructure diagram">
          {hosts.map(h => {
            const visible = h.services.filter(s =>
              filter === 'all' || s.category === filter || (filter === 'docker' && s.dockerized)
            )
            if (!visible.length) return null
            const normal = visible.filter(s => !s.dockerized)
            const dockerSubset = visible.filter(s => s.dockerized)
            return (
              <div key={h.id} className="host-card" tabIndex={0} role="group" aria-label={`${h.name} host`} onClick={() => openHost(h)} onKeyDown={e => { if (e.key === 'Enter') openHost(h) }}>
                <div className="host-header">
                  <h3>{h.name}</h3>
                  <span className="ip">{h.ip}</span>
                </div>
                <div className="services">
                  {normal.map(s => (
                    <button key={s.id} className={"service" + (s.dockerized ? ' dockerized' : '')}
                      style={{ ['--service-color' as any]: categoryColors[s.category] }}
                      onClick={e => { e.stopPropagation(); openService(h, s) }}>
                      <span className={"status-icon " + (s.status || '')} aria-label={s.status === 'up' ? 'status up' : 'status down'}>{s.status === 'up' ? '✔' : '✖'}</span>
                      <span className="svc-row"><span className="svc-name">{s.name}</span>{s.port && <span className="port inline">{s.port}</span>}</span>
                    </button>
                  ))}
                  {dockerSubset.length > 1 && h.id !== 'abra' && (
                    <div className="docker-group" aria-label={`Docker services (${dockerSubset.length})`} onClick={e => e.stopPropagation()}>
                      {dockerSubset.map(s => (
                        <button key={s.id} className="service dockerized"
                          style={{ ['--service-color' as any]: categoryColors[s.category] }}
                          onClick={e => { e.stopPropagation(); openService(h, s) }}>
                          <span className={"status-icon " + (s.status || '')} aria-label={s.status === 'up' ? 'status up' : 'status down'}>{s.status === 'up' ? '✔' : '✖'}</span>
                          <span className="svc-row"><span className="svc-name">{s.name}</span>{s.port && <span className="port inline">{s.port}</span>}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {(dockerSubset.length === 1 || h.id === 'abra') && dockerSubset.map(s => (
                    <button key={s.id} className="service dockerized"
                      style={{ ['--service-color' as any]: categoryColors[s.category] }}
                      onClick={e => { e.stopPropagation(); openService(h, s) }}>
                      <span className={"status-icon " + (s.status || '')} aria-label={s.status === 'up' ? 'status up' : 'status down'}>{s.status === 'up' ? '✔' : '✖'}</span>
                      <span className="svc-row"><span className="svc-name">{s.name}</span>{s.port && <span className="port inline">{s.port}</span>}</span>
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
          {hosts.every(h => h.services.filter(s => (filter === 'all' || s.category === filter || (filter === 'docker' && s.dockerized))).length === 0) && (
            <p className="empty-msg" role="status">No services match current filter.</p>
          )}
        </main>
      </div>
      {drawer.open && (
        <aside className="drawer" aria-label="Details sidebar">
          <button className="close-btn" onClick={closeDrawer} aria-label="Close details">×</button>
          {drawer.host && !drawer.service && <HostDetails host={drawer.host} onOpenService={(s)=> setDrawer({ host: drawer.host, service: s, open: true })} />}
          {drawer.host && drawer.service && <ServiceDetails host={drawer.host} service={drawer.service} />}
        </aside>
      )}
    </div>
  )
}

function Header() {
  return (
    <header className="app-header">
      <h1>IAES Stoplight Chart</h1>
      <p className="subtitle">Click a host or individual service for details.</p>
    </header>
  )
}

const HostDetails = ({ host, onOpenService }: { host: HostNode, onOpenService: (s: Service)=>void }) => (
  <div className="details">
    <h2>{host.name}</h2>
    <p className="muted">IP: {host.ip}</p>
    {host.notes && <p>{host.notes}</p>}
    <h3>Services</h3>
    <ul className="svc-list">
      {host.services.map(s => (
        <li key={s.id}
          className={"svc-row-btn" + (s.dockerized ? ' docker' : '')}
          role="button"
          tabIndex={0}
          onClick={() => onOpenService(s)}
          onKeyDown={e => { if (e.key === 'Enter') onOpenService(s) }}
          style={{ ['--svc-color' as any]: categoryColors[s.category], borderLeftColor: s.dockerized ? 'var(--cat-docker)' : categoryColors[s.category] }}>
          <span className={"status-icon inline " + (s.status || '')} aria-label={s.status === 'up' ? 'status up' : 'status down'}>{s.status === 'up' ? '✔' : '✖'}</span>
          <strong>{s.name}</strong> {s.port} <em className="cat-label" style={{ color: categoryColors[s.category] }}>{categoryLabels[s.category]}</em>
          {s.dockerized && <span className="cat-label" style={{ color: 'var(--cat-docker)', marginLeft: '.35rem' }}>Docker</span>}
          {s.description && <p className="svc-desc">{s.description}</p>}
        </li>
      ))}
    </ul>
  </div>
)

const ServiceDetails = ({ host, service }: { host: HostNode, service: Service }) => (
  <div className="details">
    <h2>{service.name}</h2>
    <p className="muted">Host: {host.name} ({host.ip})</p>
    <p><strong>Status:</strong> <span className={service.status === 'up' ? 'status-chip up' : 'status-chip down'}>{service.status === 'up' ? '✔ Running' : '✖ Down'}</span></p>
    <p><strong>Category:</strong> <span style={{ color: categoryColors[service.category] }}>{categoryLabels[service.category]}</span>{service.dockerized && service.id.startsWith('docker-group-') ? <> (Group)</> : service.dockerized ? <> (Container)</> : null}</p>
    {service.description && (
      <div className="detail-section">
        <h3>Overview</h3>
        <p>{service.description}</p>
      </div>
    )}
    {service.startup && (
      <div className="detail-section">
        <h3>Startup Procedure</h3>
        <ol className="step-list">
          {service.startup.map((step,i)=>(<li key={i}>{step}</li>))}
        </ol>
      </div>
    )}
    {(service.configPath || service.logPath || service.notes) && (
      <div className="detail-section">
        <h3>Paths & Notes</h3>
        <ul className="kv-list">
          {service.configPath && <li><strong>Config:</strong> <code>{service.configPath}</code></li>}
            {service.logPath && <li><strong>Logs:</strong> <code>{service.logPath}</code></li>}
            {service.notes && <li><strong>Notes:</strong> {service.notes}</li>}
        </ul>
      </div>
    )}
    {service.site && (
      <div className="detail-section">
        <h3>Website</h3>
        <p><a href={service.site} target="_blank" rel="noreferrer">Open Site ↗</a></p>
      </div>
    )}
    {service.docs && (
      <div className="detail-section">
        <h3>Documentation</h3>
        <p><a href={service.docs} target="_blank" rel="noreferrer">Reference Docs ↗</a></p>
      </div>
    )}
    {service.id.startsWith('docker-group-') && (
      <>
        <h3>Included</h3>
        <ul className="svc-list">
          {host.services.filter(s => s.dockerized).map(s => (
            <li key={s.id} style={{ borderLeftColor: 'var(--cat-docker)' }}>
              <strong>{s.name}</strong> {s.port}
              {s.description && <p className="svc-desc">{s.description}</p>}
            </li>
          ))}
        </ul>
      </>
    )}
  </div>
)

export default App
