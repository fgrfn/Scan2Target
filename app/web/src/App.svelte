<script>
  import { onMount } from 'svelte';
  import NavBar from './components/NavBar.svelte';
  import SectionCard from './components/SectionCard.svelte';
  import StatGrid from './components/StatGrid.svelte';

  const API_BASE = '/api/v1';

  let printers = [];
  let scanners = [];
  let targets = [];
  let history = [];
  let statCards = [];
  
  let selectedScanner = '';
  let selectedProfile = '';
  let selectedTarget = '';
  let selectedPrinter = '';
  let printCopies = 1;
  let printFile = null;
  
  let targetType = 'SMB';
  let targetName = '';
  let targetConnection = '';
  let targetUsername = '';
  let targetPassword = '';
  
  let showPrinterSettings = false;
  let newPrinterUri = '';
  let newPrinterName = '';
  let discoveredDevices = [];
  let isDiscovering = false;

  const navLinks = [
    { label: 'Dashboard', href: '#dashboard' },
    { label: 'Scan', href: '#scan' },
    { label: 'Print', href: '#print' },
    { label: 'Targets', href: '#targets' },
    { label: 'History', href: '#history' },
    { label: 'Settings', href: '#settings' }
  ];

  const quickProfiles = [
    { name: 'Color @300 DPI', description: 'PDF to target' },
    { name: 'Grayscale @150 DPI', description: 'Lightweight PDF' },
    { name: 'Photo @600 DPI', description: 'High quality JPEG' }
  ];

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    try {
      const [printersRes, scannersRes, targetsRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/printers`),
        fetch(`${API_BASE}/scan/devices`),
        fetch(`${API_BASE}/targets`),
        fetch(`${API_BASE}/history`)
      ]);

      printers = await printersRes.json();
      scanners = await scannersRes.json();
      targets = await targetsRes.json();
      history = await historyRes.json();

      updateStats();
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  }

  function updateStats() {
    const readyPrinters = printers.filter(p => p.status === 'idle' || p.status === 'Ready').length;
    const todayScans = history.filter(h => h.type === 'Scan' && isToday(h.ts)).length;
    const activeJobs = history.filter(h => h.status === 'In queue' || h.status === 'processing').length;

    statCards = [
      { label: 'Ready printers', value: String(readyPrinters).padStart(2, '0'), icon: '🖨️', sub: 'Available' },
      { label: 'Scanners found', value: String(scanners.length).padStart(2, '0'), icon: '📑', sub: 'eSCL + SANE' },
      { label: 'Today scans', value: String(todayScans), icon: '✅', sub: 'Completed today' },
      { label: 'Active jobs', value: String(activeJobs).padStart(2, '0'), icon: '⏳', sub: 'In progress' }
    ];
  }

  function isToday(timestamp) {
    const date = new Date(timestamp);
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }

  async function startScan() {
    if (!selectedScanner || !selectedTarget) {
      alert('Please select scanner and target');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/scan/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: selectedScanner,
          profile: selectedProfile || quickProfiles[0].name,
          target_id: selectedTarget
        })
      });

      if (response.ok) {
        await loadData();
        alert('Scan started successfully');
      } else {
        alert('Failed to start scan');
      }
    } catch (error) {
      console.error('Scan error:', error);
      alert('Failed to start scan');
    }
  }

  async function submitPrintJob() {
    if (!selectedPrinter || !printFile) {
      alert('Please select printer and file');
      return;
    }

    const formData = new FormData();
    formData.append('file', printFile);
    formData.append('printer_id', selectedPrinter);
    formData.append('options', JSON.stringify({ copies: printCopies }));

    try {
      const response = await fetch(`${API_BASE}/printers/print`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        await loadData();
        printFile = null;
        alert('Print job submitted');
      } else {
        alert('Failed to submit print job');
      }
    } catch (error) {
      console.error('Print error:', error);
      alert('Failed to submit print job');
    }
  }

  async function saveTarget() {
    if (!targetName || !targetConnection) {
      alert('Please fill in all required fields');
      return;
    }

    const config = {
      connection: targetConnection
    };

    if (targetType === 'SMB') {
      config.username = targetUsername;
      config.password = targetPassword;
    }

    try {
      const response = await fetch(`${API_BASE}/targets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: `target_${Date.now()}`,
          type: targetType,
          name: targetName,
          config: config,
          enabled: true
        })
      });

      if (response.ok) {
        await loadData();
        targetName = '';
        targetConnection = '';
        targetUsername = '';
        targetPassword = '';
        alert('Target saved');
      } else {
        alert('Failed to save target');
      }
    } catch (error) {
      console.error('Save target error:', error);
      alert('Failed to save target');
    }
  }

  async function discoverPrinters() {
    isDiscovering = true;
    try {
      const response = await fetch(`${API_BASE}/printers/discover`);
      if (response.ok) {
        discoveredDevices = await response.json();
      } else {
        alert('Failed to discover printers');
      }
    } catch (error) {
      console.error('Discovery error:', error);
      alert('Failed to discover printers');
    } finally {
      isDiscovering = false;
    }
  }

  async function addDiscoveredPrinter(device) {
    try {
      const response = await fetch(`${API_BASE}/printers/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uri: device.uri,
          name: device.name,
          description: `${device.type} - ${device.model}`
        })
      });

      if (response.ok) {
        await loadData();
        discoveredDevices = discoveredDevices.filter(d => d.uri !== device.uri);
        alert(`Printer "${device.name}" added successfully`);
      } else {
        alert('Failed to add printer');
      }
    } catch (error) {
      console.error('Add printer error:', error);
      alert('Failed to add printer');
    }
  }

  async function addPrinter() {
    if (!newPrinterUri || !newPrinterName) {
      alert('Please enter printer URI and name');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/printers/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uri: newPrinterUri,
          name: newPrinterName
        })
      });

      if (response.ok) {
        await loadData();
        newPrinterUri = '';
        newPrinterName = '';
        showPrinterSettings = false;
        alert('Printer added successfully');
      } else {
        alert('Failed to add printer');
      }
    } catch (error) {
      console.error('Add printer error:', error);
      alert('Failed to add printer');
    }
  }
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

  <SectionCard id="scan" title="Scan" subtitle="Start server-side scans and route results to targets.">
    <div class="grid two-cols">
      <div>
        <h3>Scanners</h3>
        {#if scanners.length === 0}
          <p class="muted">No scanners detected. Make sure SANE/eSCL is configured.</p>
        {:else}
          <ul class="list">
            {#each scanners as scanner}
              <li>
                <div class="list-title">{scanner.name}</div>
                <div class="muted">{scanner.type || 'Unknown type'}</div>
              </li>
            {/each}
          </ul>
        {/if}
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
          <label for="scanner-select">Choose scanner</label>
          <select id="scanner-select" bind:value={selectedScanner}>
            <option value="">-- Select scanner --</option>
            {#each scanners as scanner}
              <option value={scanner.id}>{scanner.name}</option>
            {/each}
          </select>
          <label for="profile-select">Profile</label>
          <select id="profile-select" bind:value={selectedProfile}>
            {#each quickProfiles as profile}
              <option value={profile.name}>{profile.name}</option>
            {/each}
          </select>
          <label for="target-select">Target</label>
          <select id="target-select" bind:value={selectedTarget}>
            <option value="">-- Select target --</option>
            {#each targets as target}
              <option value={target.id}>{target.name}</option>
            {/each}
          </select>
          <button class="primary block" on:click={startScan}>Start scan</button>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="print" title="Print" subtitle="Upload PDFs or images and forward them to CUPS printers.">
    <div class="grid two-cols">
      <div>
        <h3>Printers</h3>
        {#if printers.length === 0}
          <p class="muted">No printers configured. Add printers in Settings.</p>
        {:else}
          <ul class="list">
            {#each printers as printer}
              <li>
                <div class="list-title">{printer.name}</div>
                <div class="muted">{printer.id}</div>
                <span class={`badge ${printer.status === 'idle' ? 'success' : 'warning'}`}>{printer.status}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
      <div class="panel">
        <div class="panel-header">Send a print job</div>
        <div class="panel-body">
          <label for="printer-select">Choose printer</label>
          <select id="printer-select" bind:value={selectedPrinter}>
            <option value="">-- Select printer --</option>
            {#each printers as printer}
              <option value={printer.id}>{printer.name}</option>
            {/each}
          </select>
          <label for="file-input">File</label>
          <input id="file-input" type="file" accept="application/pdf,image/*" on:change={(e) => printFile = e.target.files[0]} />
          <label for="copies-input">Copies</label>
          <input id="copies-input" type="number" min="1" bind:value={printCopies} />
          <button class="primary block" on:click={submitPrintJob}>Upload &amp; print</button>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="targets" title="Targets" subtitle="Destinations for scanned documents.">
    <div class="grid two-cols">
      <div>
        <h3>Configured targets</h3>
        {#if targets.length === 0}
          <p class="muted">No targets configured yet.</p>
        {:else}
          <ul class="list">
            {#each targets as target}
              <li>
                <div class="list-title">{target.name}</div>
                <div class="muted">{target.type}: {target.config?.connection || 'N/A'}</div>
                <span class="badge {target.enabled ? 'success' : 'warning'}">{target.enabled ? 'Enabled' : 'Disabled'}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
      <div class="panel">
        <div class="panel-header">Add target</div>
        <div class="panel-body">
          <label for="target-type">Type</label>
          <select id="target-type" bind:value={targetType}>
            <option>SMB</option>
            <option>SFTP</option>
            <option>Email</option>
            <option>Paperless-ngx</option>
            <option>Webhook</option>
          </select>
          <label for="target-name">Name</label>
          <input id="target-name" type="text" placeholder="e.g. NAS scans" bind:value={targetName} />
          <label for="target-connection">Connection</label>
          <input id="target-connection" type="text" placeholder="//nas/share or URL" bind:value={targetConnection} />
          
          {#if targetType === 'SMB'}
            <label for="target-username">Username</label>
            <input id="target-username" type="text" placeholder="Network username" bind:value={targetUsername} />
            <label for="target-password">Password</label>
            <input id="target-password" type="password" placeholder="Network password" bind:value={targetPassword} />
          {/if}
          
          <button class="primary block" on:click={saveTarget}>Save target</button>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="history" title="History" subtitle="Recent scan and print jobs.">
    {#if history.length === 0}
      <p class="muted">No jobs in history yet.</p>
    {:else}
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
            <span class={`badge ${job.status === 'Done' || job.status === 'completed' ? 'success' : 'warning'}`}>{job.status}</span>
          </div>
        {/each}
      </div>
    {/if}
  </SectionCard>

  <SectionCard id="settings" title="Settings" subtitle="Configure printers and system settings.">
    <div class="grid two-cols">
      <div>
        <h3>Printer Discovery</h3>
        <p class="muted">Auto-detect USB and wireless printers. USB port is detected automatically by CUPS.</p>
        <button class="primary" on:click={discoverPrinters} disabled={isDiscovering}>
          {isDiscovering ? 'Searching...' : 'Discover Printers'}
        </button>
        
        {#if discoveredDevices.length > 0}
          <h4 class="mt">Discovered Devices</h4>
          <ul class="list">
            {#each discoveredDevices as device}
              <li>
                <div class="list-title">{device.name}</div>
                <div class="muted">
                  Type: {device.type} · {device.uri}
                </div>
                <button class="ghost small" on:click={() => addDiscoveredPrinter(device)}>Add</button>
              </li>
            {/each}
          </ul>
        {:else if !isDiscovering && discoveredDevices.length === 0}
          <p class="muted small mt">No devices discovered. Click "Discover Printers" to scan.</p>
        {/if}
      </div>
      <div class="panel">
        <div class="panel-header">Manual Setup</div>
        <div class="panel-body">
          <p class="muted small">For advanced users: add printer manually with custom URI.</p>
          <label for="printer-uri">Printer URI</label>
          <input id="printer-uri" type="text" placeholder="usb://HP/Envy or ipp://printer.local" bind:value={newPrinterUri} />
          <label for="printer-name">Printer Name</label>
          <input id="printer-name" type="text" placeholder="My Printer" bind:value={newPrinterName} />
          <button class="ghost block" on:click={addPrinter}>Add Manually</button>
          <hr style="margin: 1rem 0; border: none; border-top: 1px solid rgba(255,255,255,0.1);">
          <h4>Supported Connections:</h4>
          <ul class="muted small" style="margin-left: 1rem;">
            <li><strong>USB:</strong> Auto-detected, any USB port</li>
            <li><strong>Wireless:</strong> AirPrint/IPP (dnssd://)</li>
            <li><strong>Network:</strong> IPP (ipp://)</li>
          </ul>
          <p class="muted small"><strong>Note:</strong> Scanners are managed separately via SANE (/scan section). Multi-function devices appear in both if they support both printing and scanning.</p>
        </div>
      </div>
    </div>
  </SectionCard>
</main>
