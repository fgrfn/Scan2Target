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
  let scanFilename = '';
  let scanSource = 'Flatbed';
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
  
  let isLoadingDevices = true;
  let isLoadingTargets = true;
  let isLoadingHistory = true;

  const navLinks = [
    { label: 'Dashboard', href: '#dashboard' },
    { label: 'Scan', href: '#scan' },
    { label: 'Targets', href: '#targets' },
    { label: 'History', href: '#history' }
  ];

  let quickProfiles = [
    { id: 'color_300_pdf', name: 'Color @300 DPI', description: 'PDF to target' },
    { id: 'gray_150_pdf', name: 'Grayscale @150 DPI', description: 'Lightweight PDF' },
    { id: 'photo_600_jpeg', name: 'Photo @600 DPI', description: 'High quality JPEG' }
  ];

  onMount(() => {
    const pageStart = performance.now();
    console.log('[TIMING] Page load started');
    loadData();
    
    // Handle hash navigation on page load
    if (window.location.hash) {
      setTimeout(() => {
        const element = document.querySelector(window.location.hash);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 200);
    }
    
    // Check when all data is loaded
    const checkComplete = setInterval(() => {
      if (!isLoadingDevices && !isLoadingTargets && !isLoadingHistory) {
        console.log(`[TIMING] Total page load: ${(performance.now() - pageStart).toFixed(0)}ms`);
        clearInterval(checkComplete);
      }
    }, 100);
  });

  async function loadData() {
    // Load devices first (most important)
    loadDevices();
    // Load other data in parallel
    loadTargets();
    loadHistory();
    loadProfiles();
  }
  
  async function loadProfiles() {
    try {
      const response = await fetch(`${API_BASE}/scan/profiles`);
      if (response.ok) {
        const profiles = await response.json();
        // Transform API profiles to match frontend structure
        quickProfiles = profiles.map(p => ({
          id: p.id,
          name: p.name || p.id,
          description: p.description || '',
          source: p.source || 'Flatbed'
        }));
        console.log('Loaded profiles from API:', quickProfiles.length);
      }
    } catch (error) {
      console.error('Failed to load profiles:', error);
      // Keep default profiles on error
    }
  }

  async function loadDevices() {
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/devices`);
      if (res.ok) {
        const devices = await res.json();
        printers = devices.filter(d => d.device_type === 'printer');
        scanners = devices.filter(d => d.device_type === 'scanner');
        updateStats();
        console.log(`[TIMING] loadDevices: ${(performance.now() - start).toFixed(0)}ms`);
      }
    } catch (error) {
      console.error('Failed to load devices:', error);
    } finally {
      isLoadingDevices = false;
    }
  }

  async function loadTargets() {
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/targets`);
      if (res.ok) {
        targets = await res.json();
        console.log(`[TIMING] loadTargets: ${(performance.now() - start).toFixed(0)}ms`);
      }
    } catch (error) {
      console.error('Failed to load targets:', error);
    } finally {
      isLoadingTargets = false;
    }
  }

  async function loadHistory() {
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/history`);
      if (res.ok) {
        history = await res.json();
        updateStats();
        console.log(`[TIMING] loadHistory: ${(performance.now() - start).toFixed(0)}ms`);
      }
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      isLoadingHistory = false;
    }
  }

  function updateStats() {
    const todayScans = history.filter(h => h.job_type === 'scan' && isToday(h.created_at)).length;
    const activeJobs = history.filter(h => h.status === 'queued' || h.status === 'running').length;

    statCards = [
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
          profile_id: selectedProfile || quickProfiles[0].id,
          target_id: selectedTarget,
          filename_prefix: scanFilename || 'scan'
        })
      });

      if (response.ok) {
        await loadData();
        alert('✅ Scan started successfully');
      } else {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        alert(`❌ Failed to start scan: ${error.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Scan error:', error);
      alert(`❌ Failed to start scan: ${error.message}`);
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
      <h1>Central hub for scanning.</h1>
      <p class="lede">Trigger scans on devices without physical buttons, and route files to SMB, email, Paperless-ngx, or webhooks.</p>
      <div class="actions">
        <a class="primary" href="#scan">Start a scan</a>
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
        {#if isLoadingDevices}
          <p class="muted">⏳ Loading scanners...</p>
        {:else if scanners.length === 0}
          <p class="muted">No scanners configured. Click "Discover Scanners" below to add.</p>
        {:else}
          <ul class="list">
            {#each scanners as scanner}
              <li style="display: flex; align-items: center; justify-content: space-between;">
                <div style="flex: 1;">
                  <div class="list-title">
                    {scanner.name}
                    {#if scanner.connection_type && scanner.connection_type.includes('eSCL')}
                      <span class="badge success" style="margin-left: 0.5rem; font-size: 0.7rem;">⭐ Recommended</span>
                    {/if}
                  </div>
                  <div class="muted">{scanner.connection_type || scanner.type || 'Unknown'}</div>
                  <span class="badge {scanner.status === 'online' ? 'success' : 'warning'}">{scanner.status || 'unknown'}</span>
                </div>
                <button class="ghost small" on:click={() => removeDevice(scanner.id, 'scanner')}>Remove</button>
              </li>
            {/each}
          </ul>
        {/if}
        
        <h3 class="mt">Scanner Management</h3>
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
                  {#if device.connection_type && device.connection_type.includes('eSCL')}
                    <span class="badge success" style="margin-left: 0.5rem;">⭐ Recommended</span>
                  {/if}
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
        
        <h3 class="mt">Quick profiles</h3>
        <div class="chip-row">
          {#each quickProfiles as profile}
            <div class="chip" title={profile.description || ''}>
              {profile.name}
              {#if profile.source === 'ADF'}<span style="color: var(--primary); margin-left: 4px;">📄</span>{/if}
            </div>
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
              <option value={scanner.id}>
                {scanner.name}
                {#if scanner.connection_type && scanner.connection_type.includes('eSCL')}⭐ Recommended{/if}
              </option>
            {/each}
          </select>
          
          <label for="source-select">🆕 Scan-Quelle</label>
          <select id="source-select" bind:value={scanSource} style="width: 100%; padding: 8px 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 14px;">
            <option value="Flatbed">📄 Flachbett (Flatbed)</option>
            <option value="ADF">📚 Dokumenteneinzug (ADF) - Multi-page</option>
          </select>
          <p class="muted small" style="margin-top: 0.25rem; margin-bottom: 0.75rem;">ADF scannt automatisch alle Seiten im Einzug</p>
          
          <label for="profile-select">Profile</label>
          <select id="profile-select" bind:value={selectedProfile}>
            {#each quickProfiles.filter(p => p.source === scanSource) as profile}
              <option value={profile.id}>
                {profile.name}
              </option>
            {/each}
          </select>
          <label for="target-select">Target</label>
          <select id="target-select" bind:value={selectedTarget}>
            <option value="">-- Select target --</option>
            {#each targets as target}
              <option value={target.id}>{target.name}</option>
            {/each}
          </select>
          <label for="filename-input">Filename (optional)</label>
          <input 
            id="filename-input" 
            type="text" 
            bind:value={scanFilename} 
            placeholder="e.g. invoice_2025" 
            style="width: 100%; padding: 8px 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 14px;"
          />
          <p class="muted small" style="margin-top: 0.25rem; margin-bottom: 0.75rem;">Leave empty for auto-generated name (scan_UUID)</p>
          
          <button class="primary block" on:click={startScan}>Start scan</button>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="targets" title="Targets" subtitle="Destinations for scanned documents.">
    <div class="grid two-cols">
      <div>
        <h3>Delivery targets</h3>
        {#if isLoadingTargets}
          <p class="muted">⏳ Loading targets...</p>
        {:else if targets.length === 0}
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
            <button class="ghost" style="flex: 1;" on:click={() => saveTarget(true)}>Save without test</button>
          </div>
          <p style="font-size: 0.85rem; color: #888; margin-top: 0.5rem;">
            💡 "Test & Save" validates the connection before saving. Use "Save without test" if the server is temporarily offline.
          </p>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="history" title="History" subtitle="Recent scan and print jobs.">
    {#if isLoadingHistory}
      <p class="muted">⏳ Loading history...</p>
    {:else if history.length === 0}
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
            <span>{job.job_type}</span>
            <span>{job.device_id || 'N/A'}</span>
            <span>{job.target_id || 'N/A'}</span>
            <span>{new Date(job.created_at).toLocaleString()}</span>
            <span class={`badge ${job.status === 'completed' ? 'success' : job.status === 'failed' ? 'danger' : 'warning'}`}>{job.status}</span>
          </div>
        {/each}
      </div>
    {/if}
  </SectionCard>

</main>
