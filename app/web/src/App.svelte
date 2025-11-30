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
  let discoveredScanners = [];
  let isDiscovering = false;
  let lastDiscoveryTime = null;

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
      const [devicesRes, targetsRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/devices`),
        fetch(`${API_BASE}/targets`),
        fetch(`${API_BASE}/history`)
      ]);

      if (devicesRes.ok) {
        const devices = await devicesRes.json();
        // Split devices into printers and scanners
        printers = devices.filter(d => d.device_type === 'printer');
        scanners = devices.filter(d => d.device_type === 'scanner');
        console.log('Loaded devices:', printers.length, 'printers,', scanners.length, 'scanners');
      } else {
        console.error('Failed to load devices:', devicesRes.status);
      }
      
      if (targetsRes.ok) {
        targets = await targetsRes.json();
      } else {
        console.error('Failed to load targets:', targetsRes.status);
      }
      
      if (historyRes.ok) {
        history = await historyRes.json();
      } else {
        console.error('Failed to load history:', historyRes.status);
      }

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

  async function saveTarget(skipValidation = false) {
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

    const payload = {
      id: `target_${Date.now()}`,
      type: targetType,
      name: targetName,
      config: config,
      enabled: true,
      description: null
    };

    console.log('Saving target:', payload);
    console.log('Skip validation:', skipValidation);

    try {
      const url = skipValidation 
        ? `${API_BASE}/targets?validate=false`
        : `${API_BASE}/targets`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        await loadData();
        targetName = '';
        targetConnection = '';
        targetUsername = '';
        targetPassword = '';
        alert('✅ Target saved successfully');
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('Failed to save target:', response.status, errorData);
        alert(`❌ Failed to save target: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Save target error:', error);
      alert(`❌ Failed to save target: ${error.message}`);
    }
  }

  async function removeTarget(targetId) {
    if (!confirm(`Remove target "${targetId}"?`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/targets/${targetId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        await loadData();
        alert('✅ Target removed successfully');
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        alert(`❌ Failed to remove target: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Remove target error:', error);
      alert(`❌ Failed to remove target: ${error.message}`);
    }
  }

  async function removeDevice(deviceId, deviceType) {
    const typeName = deviceType === 'printer' ? 'printer' : 'scanner';
    if (!confirm(`Remove ${typeName} "${deviceId}"?`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/devices/${deviceId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        await loadData();
        alert(`✅ ${typeName.charAt(0).toUpperCase() + typeName.slice(1)} removed successfully`);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        alert(`❌ Failed to remove ${typeName}: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error(`Remove ${typeName} error:`, error);
      alert(`❌ Failed to remove ${typeName}: ${error.message}`);
    }
  }

  async function discoverPrinters() {
    isDiscovering = true;
    try {
      // Use new unified devices endpoint
      const response = await fetch(`${API_BASE}/devices/discover`);
      if (response.ok) {
        const allDevices = await response.json();
        
        // Filter to only show printers (not scanners)
        discoveredDevices = allDevices.filter(device => device.device_type === 'printer');
        lastDiscoveryTime = new Date();
        
        console.log('Discovery complete:', discoveredDevices.length, 'printers found');
        console.log('All devices:', allDevices.length);
      } else {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        alert(`Failed to discover printers: ${error.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Discovery error:', error);
      alert(`Failed to discover printers: ${error.message}`);
    } finally {
      isDiscovering = false;
    }
  }

  async function addDiscoveredPrinter(device) {
    try {
      // Use new unified devices endpoint
      const response = await fetch(`${API_BASE}/devices/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uri: device.uri,
          name: device.name,
          device_type: 'printer',
          make: device.make,
          model: device.model,
          connection_type: device.connection_type,
          description: `${device.connection_type} - ${device.model || device.name}`
        })
      });

      if (response.ok) {
        await loadData();
        // Refresh discovery to update "already_added" status
        await discoverPrinters();
        alert(`✅ Printer "${device.name}" added successfully`);
      } else {
        const error = await response.json();
        alert(`❌ Failed to add printer: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Add printer error:', error);
      alert(`❌ Failed to add printer: ${error.message || 'Network error'}`);
    }
  }

  async function discoverScanners() {
    isDiscovering = true;
    try {
      const response = await fetch(`${API_BASE}/devices/discover`);
      if (response.ok) {
        const allDevices = await response.json();
        
        // Filter to only show scanners (not printers)
        discoveredScanners = allDevices.filter(device => device.device_type === 'scanner');
        lastDiscoveryTime = new Date();
        
        console.log('Discovery complete:', discoveredScanners.length, 'scanners found');
      } else {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        alert(`Failed to discover scanners: ${error.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Discovery error:', error);
      alert(`Failed to discover scanners: ${error.message}`);
    } finally {
      isDiscovering = false;
    }
  }

  async function addDiscoveredScanner(device) {
    try {
      const response = await fetch(`${API_BASE}/devices/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uri: device.uri,
          name: device.name,
          device_type: 'scanner',
          make: device.make,
          model: device.model,
          connection_type: device.connection_type,
          description: `${device.connection_type} - ${device.model || device.name}`
        })
      });

      if (response.ok) {
        await loadData();
        // Refresh discovery to update "already_added" status
        await discoverScanners();
        alert(`✅ Scanner "${device.name}" added successfully`);
      } else {
        const error = await response.json();
        alert(`❌ Failed to add scanner: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Add scanner error:', error);
      alert(`❌ Failed to add scanner: ${error.message || 'Network error'}`);
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
        const error = await response.json();
        alert(`Failed to add printer: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Add printer error:', error);
      alert(`Failed to add printer: ${error.message || 'Network error'}`);
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
        <h3>Configured Scanners</h3>
        {#if scanners.length === 0}
          <p class="muted">No scanners configured. Use Settings → Scanner Management to add.</p>
        {:else}
          <ul class="list">
            {#each scanners as scanner}
              <li style="display: flex; align-items: center; justify-content: space-between;">
                <div style="flex: 1;">
                  <div class="list-title">{scanner.name}</div>
                  <div class="muted">{scanner.connection_type || scanner.type || 'Unknown'}</div>
                  <span class="badge {scanner.status === 'online' ? 'success' : 'warning'}">{scanner.status || 'unknown'}</span>
                </div>
                <button class="ghost small" on:click={() => removeDevice(scanner.id, 'scanner')}>Remove</button>
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
        <h3>Configured Printers</h3>
        {#if printers.length === 0}
          <p class="muted">No printers configured. Use Settings → Discover Printers to add.</p>
        {:else}
          <ul class="list">
            {#each printers as printer}
              <li>
                <div class="list-title">{printer.name}</div>
                <div class="muted">{printer.type || 'Unknown'} · {printer.id}</div>
                <div style="display: flex; gap: 0.5rem; align-items: center; margin-top: 0.5rem;">
                  <span class={`badge ${printer.status === 'idle' ? 'success' : 'warning'}`}>{printer.status}</span>
                  <button class="ghost small" on:click={() => removeDevice(printer.id, 'printer')}>Remove</button>
                </div>
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
              <li style="display: flex; align-items: center; justify-content: space-between;">
                <div style="flex: 1;">
                  <div class="list-title">{target.name}</div>
                  <div class="muted">{target.type}: {target.config?.connection || 'N/A'}</div>
                  <span class="badge {target.enabled ? 'success' : 'warning'}">{target.enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                <button class="danger small" on:click={() => removeTarget(target.id)}>Remove</button>
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
          
          <div style="display: flex; gap: 0.5rem;">
            <button class="primary" style="flex: 1;" on:click={() => saveTarget(false)}>Test & Save</button>
            <button style="flex: 1;" on:click={() => saveTarget(true)}>Save without test</button>
          </div>
          <p style="font-size: 0.85rem; color: #888; margin-top: 0.5rem;">
            💡 "Test & Save" validates the connection before saving. Use "Save without test" if the server is temporarily offline.
          </p>
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
        <h3>Printer Management</h3>
        <p class="muted">Discover and add USB/wireless printers to CUPS. Printers must be manually added - they are never added automatically.</p>
        <button class="primary" on:click={discoverPrinters} disabled={isDiscovering}>
          {isDiscovering ? 'Searching...' : 'Discover Printers'}
        </button>
        {#if lastDiscoveryTime}
          <p class="muted small" style="margin-top: 0.5rem;">
            Last scan: {lastDiscoveryTime.toLocaleTimeString()} · Click "Discover" to refresh
          </p>
        {/if}
        
        {#if discoveredDevices.length > 0}
          <h4 class="mt">Discovered Devices ({discoveredDevices.length})</h4>
          <ul class="list">
            {#each discoveredDevices as device}
              <li>
                <div class="list-title">{device.name}</div>
                <div class="muted">
                  {device.connection_type || device.type}
                  {#if device.already_added}
                    <span class="badge success" style="margin-left: 0.5rem;">✓ Already Added</span>
                  {:else}
                    <span class="badge warning" style="margin-left: 0.5rem;">Not Added Yet</span>
                  {/if}
                </div>
                <div class="muted small" style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.25rem;">
                  {device.uri}
                </div>
                {#if !device.already_added}
                  <button class="primary small" on:click={() => addDiscoveredPrinter(device)}>Add Printer</button>
                {:else}
                  <button class="ghost small" disabled>Already Added</button>
                {/if}
              </li>
            {/each}
          </ul>
        {:else if !isDiscovering}
          <p class="muted small mt">No devices found. Make sure printers are powered on and connected (USB or network).</p>
        {/if}
      </div>
      <div>
        <h3>Scanner Management</h3>
        <p class="muted">Discover and add USB/wireless scanners via SANE/eSCL. Scanners must be manually added - they are never added automatically.</p>
        <button class="primary" on:click={discoverScanners} disabled={isDiscovering}>
          {isDiscovering ? 'Searching...' : 'Discover Scanners'}
        </button>
        {#if lastDiscoveryTime}
          <p class="muted small" style="margin-top: 0.5rem;">
            Last scan: {lastDiscoveryTime.toLocaleTimeString()} · Click "Discover" to refresh
          </p>
        {/if}
        
        {#if discoveredScanners.length > 0}
          <h4 class="mt">Discovered Scanners ({discoveredScanners.length})</h4>
          <ul class="list">
            {#each discoveredScanners as device}
              <li>
                <div class="list-title">{device.name}</div>
                <div class="muted">
                  {device.connection_type || device.type}
                  {#if device.already_added}
                    <span class="badge success" style="margin-left: 0.5rem;">✓ Already Added</span>
                  {:else}
                    <span class="badge warning" style="margin-left: 0.5rem;">Not Added Yet</span>
                  {/if}
                </div>
                <div class="muted small" style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.25rem;">
                  {device.uri}
                </div>
                {#if !device.already_added}
                  <button class="primary small" on:click={() => addDiscoveredScanner(device)}>Add Scanner</button>
                {:else}
                  <button class="ghost small" disabled>Already Added</button>
                {/if}
              </li>
            {/each}
          </ul>
        {:else if !isDiscovering}
          <p class="muted small mt">No scanners found. Make sure scanners are powered on and connected (USB or network).</p>
        {/if}
      </div>
    </div>
  </SectionCard>
</main>
