<script>
  import NavBar from './components/NavBar.svelte';
  import SectionCard from './components/SectionCard.svelte';
  import StatGrid from './components/StatGrid.svelte';

  const printers = [
    { name: 'HP Envy 6400', status: 'Ready', jobs: 1, protocol: 'IPP', color: true },
    { name: 'Brother HL-L2350DW', status: 'Idle', jobs: 0, protocol: 'AirPrint', color: false }
  ];

  const scanners = [
    { name: 'HP Envy 6400 (eSCL)', dpi: [150, 300, 600], color: true },
    { name: 'Fujitsu ScanSnap (SANE)', dpi: [150, 300], color: true }
  ];

  const targets = [
    { name: 'NAS (SMB)', details: '\\nas\scans', status: 'Reachable' },
    { name: 'Paperless-ngx', details: 'http://paperless.local/api', status: 'Reachable' },
    { name: 'Webhook → Home Assistant', details: 'POST /api/webhook/raspscan', status: 'Configured' }
  ];

  const history = [
    { id: 'SCAN-204', type: 'Scan', device: 'HP Envy 6400', target: 'NAS (SMB)', ts: '2024-04-01 09:12', status: 'Done' },
    { id: 'PRINT-882', type: 'Print', device: 'Brother HL-L2350DW', target: 'Queue', ts: '2024-04-01 09:05', status: 'In queue' },
    { id: 'SCAN-203', type: 'Scan', device: 'Fujitsu ScanSnap', target: 'Paperless-ngx', ts: '2024-04-01 08:53', status: 'Done' }
  ];

  const statCards = [
    { label: 'Ready printers', value: '02', icon: '🖨️', sub: 'AirPrint + USB' },
    { label: 'Scanners found', value: '02', icon: '📑', sub: 'eSCL + SANE' },
    { label: 'Today scans', value: '7', icon: '✅', sub: '2 targets succeeded' },
    { label: 'Active jobs', value: '01', icon: '⏳', sub: 'Print queue watching' }
  ];

  const navLinks = [
    { label: 'Dashboard', href: '#dashboard' },
    { label: 'Scan', href: '#scan' },
    { label: 'Print', href: '#print' },
    { label: 'Targets', href: '#targets' },
    { label: 'History', href: '#history' }
  ];

  const quickProfiles = [
    { name: 'Color @300 DPI', description: 'PDF to NAS consume folder' },
    { name: 'Grayscale @150 DPI', description: 'Lightweight for email' },
    { name: 'Photo @600 DPI', description: 'Archival JPEG to Paperless-ngx' }
  ];
</script>

<NavBar brand="RaspScan" {navLinks} links={navLinks} />

<main class="page">
  <section id="dashboard" class="hero">
    <div>
      <p class="eyebrow">Raspberry Pi · FastAPI · Svelte</p>
      <h1>Central hub for scanning &amp; printing.</h1>
      <p class="lede">Trigger scans on devices without physical buttons, route files to SMB, email, Paperless-ngx, or webhooks, and manage printers with CUPS/AirPrint.</p>
      <div class="actions">
        <a class="primary" href="#scan">Start a scan</a>
        <a class="ghost" href="#print">Send a print job</a>
      </div>
    </div>
    <div class="card hero-card">
      <div class="card-title">Live status</div>
      <StatGrid cards={statCards} />
    </div>
  </section>

  <SectionCard id="scan" title="Scan" subtitle="Kick off server-side scans and route results to your favorite targets." actions={[{ label: 'Add profile', onClick: () => alert('Profile dialog stub') }]}>
    <div class="grid two-cols">
      <div>
        <h3>Scanners</h3>
        <ul class="list">
          {#each scanners as scanner}
            <li>
              <div class="list-title">{scanner.name}</div>
              <div class="muted">DPI: {scanner.dpi.join(', ')} · Color: {scanner.color ? 'Yes' : 'No'}</div>
            </li>
          {/each}
        </ul>
        <h3 class="mt">Quick profiles</h3>
        <div class="chip-row">
          {#each quickProfiles as profile}
            <div class="chip">{profile.name}</div>
          {/each}
        </div>
      </div>
      <div class="panel">
        <div class="panel-header">Launch a scan</div>
        <div class="panel-body">
          <label>Choose scanner</label>
          <select>
            {#each scanners as scanner}
              <option>{scanner.name}</option>
            {/each}
          </select>
          <label>Profile</label>
          <select>
            {#each quickProfiles as profile}
              <option>{profile.name}</option>
            {/each}
          </select>
          <label>Target</label>
          <select>
            {#each targets as target}
              <option>{target.name}</option>
            {/each}
          </select>
          <button class="primary block">Start scan</button>
          <p class="muted small">Actions are stubbed for the UI preview; wire them to /api/scan/start in the backend.</p>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="print" title="Print" subtitle="Upload PDFs or images and forward them to any CUPS printer.">
    <div class="grid two-cols">
      <div>
        <h3>Printers</h3>
        <ul class="list">
          {#each printers as printer}
            <li>
              <div class="list-title">{printer.name}</div>
              <div class="muted">{printer.protocol} · {printer.color ? 'Color' : 'Mono'} · Jobs: {printer.jobs}</div>
              <span class={`badge ${printer.status === 'Ready' ? 'success' : 'warning'}`}>{printer.status}</span>
            </li>
          {/each}
        </ul>
      </div>
      <div class="panel">
        <div class="panel-header">Send a print job</div>
        <div class="panel-body">
          <label>Choose printer</label>
          <select>
            {#each printers as printer}
              <option>{printer.name}</option>
            {/each}
          </select>
          <label>File</label>
          <input type="file" accept="application/pdf,image/*" />
          <label>Copies</label>
          <input type="number" min="1" value="1" />
          <button class="primary block">Upload &amp; print</button>
          <p class="muted small">Wire to /api/print to forward documents to CUPS.</p>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="targets" title="Targets" subtitle="Curated destinations for scanned documents.">
    <div class="grid two-cols">
      <div>
        <h3>Configured targets</h3>
        <ul class="list">
          {#each targets as target}
            <li>
              <div class="list-title">{target.name}</div>
              <div class="muted">{target.details}</div>
              <span class="badge success">{target.status}</span>
            </li>
          {/each}
        </ul>
      </div>
      <div class="panel">
        <div class="panel-header">Add target</div>
        <div class="panel-body">
          <label>Type</label>
          <select>
            <option>SMB</option>
            <option>SFTP</option>
            <option>Email (SMTP)</option>
            <option>Paperless-ngx</option>
            <option>Webhook</option>
          </select>
          <label>Name</label>
          <input type="text" placeholder="e.g. NAS scans" />
          <label>Connection</label>
          <input type="text" placeholder="//nas/share or URL" />
          <button class="ghost block">Save target</button>
          <p class="muted small">Persist to /api/targets and validate connectivity.</p>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="history" title="History" subtitle="Recent scan and print jobs with status and routing.">
    <div class="table">
      <div class="table-head">
        <span>ID</span>
        <span>Type</span>
        <span>Device</span>
        <span>Target</span>
        <span>Time</span>
        <span>Status</span>
      </div>
      {#each history as job}
        <div class="table-row">
          <span>{job.id}</span>
          <span>{job.type}</span>
          <span>{job.device}</span>
          <span>{job.target}</span>
          <span>{job.ts}</span>
          <span class={`badge ${job.status === 'Done' ? 'success' : 'warning'}`}>{job.status}</span>
        </div>
      {/each}
    </div>
  </SectionCard>
</main>
