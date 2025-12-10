<script>
  import { onMount } from 'svelte';

  const API_BASE = '/api/v1';

  // Language support
  let currentLang = localStorage.getItem('scan2target_lang') || 'en';
  
  const translations = {
    en: {
      title: 'Quick Scan',
      selectScanner: 'Select Scanner',
      selectTarget: 'Select Target',
      selectProfile: 'Scan Quality',
      filename: 'Filename (optional)',
      filenamePlaceholder: 'e.g. invoice_2025',
      scanSingle: '📄 Scan Single Page',
      scanMulti: '📚 Scan Multi-Page (ADF)',
      scanBatch: '📑 Batch Mode',
      startScan: 'Start Scan',
      addPage: 'Add Page',
      finishBatch: 'Finish Batch',
      cancelBatch: 'Cancel',
      pagesInBatch: 'Pages',
      scanning: 'Scanning...',
      success: '✅ Scan started!',
      error: '❌ Error',
      pleaseSelect: 'Please select scanner and target',
      batchActive: 'Batch Mode Active',
      loading: 'Loading...',
      noScanners: 'No scanners found',
      noTargets: 'No targets found'
    },
    de: {
      title: 'Schnell-Scan',
      selectScanner: 'Scanner wählen',
      selectTarget: 'Ziel wählen',
      selectProfile: 'Scan-Qualität',
      filename: 'Dateiname (optional)',
      filenamePlaceholder: 'z.B. rechnung_2025',
      scanSingle: '📄 Einzelseite scannen',
      scanMulti: '📚 Mehrere Seiten (ADF)',
      scanBatch: '📑 Stapel-Modus',
      startScan: 'Scan starten',
      addPage: 'Seite hinzufügen',
      finishBatch: 'Stapel abschließen',
      cancelBatch: 'Abbrechen',
      pagesInBatch: 'Seiten',
      scanning: 'Scanne...',
      success: '✅ Scan gestartet!',
      error: '❌ Fehler',
      pleaseSelect: 'Bitte Scanner und Ziel wählen',
      batchActive: 'Stapel-Modus aktiv',
      loading: 'Lädt...',
      noScanners: 'Keine Scanner gefunden',
      noTargets: 'Keine Ziele gefunden'
    }
  };

  $: t = translations[currentLang];

  let scanners = [];
  let targets = [];
  let profiles = [];
  let selectedScanner = '';
  let selectedTarget = '';
  let selectedProfile = '';
  let scanFilename = '';
  let scanSource = 'Flatbed';
  let isScanning = false;
  let isLoading = true;
  
  // Batch mode
  let batchMode = false;
  let batchPages = [];
  let isBatchScanning = false;

  onMount(async () => {
    await loadData();
    // Auto-select favorites
    const favoriteScanner = scanners.find(s => s.is_favorite);
    if (favoriteScanner) selectedScanner = favoriteScanner.id;
    const favoriteTarget = targets.find(t => t.is_favorite);
    if (favoriteTarget) selectedTarget = favoriteTarget.id;
  });

  async function loadData() {
    isLoading = true;
    try {
      // Load scanners
      const scannersRes = await fetch(`${API_BASE}/devices`);
      if (scannersRes.ok) {
        const devices = await scannersRes.json();
        scanners = devices.filter(d => d.device_type === 'scanner');
      }

      // Load targets
      const targetsRes = await fetch(`${API_BASE}/targets`);
      if (targetsRes.ok) {
        targets = await targetsRes.json();
      }

      // Load profiles
      const profilesRes = await fetch(`${API_BASE}/scan/profiles`);
      if (profilesRes.ok) {
        profiles = await profilesRes.json();
        if (profiles.length > 0) {
          // Default to Document @200 DPI
          const defaultProfile = profiles.find(p => p.id.includes('200'));
          selectedProfile = defaultProfile ? defaultProfile.id : profiles[0].id;
        }
      }
    } catch (error) {
      console.error('Load error:', error);
    } finally {
      isLoading = false;
    }
  }

  async function startScan(source = 'Flatbed') {
    if (!selectedScanner || !selectedTarget) {
      alert(t.pleaseSelect);
      return;
    }

    isScanning = true;
    scanSource = source;

    try {
      const response = await fetch(`${API_BASE}/scan/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: selectedScanner,
          profile_id: selectedProfile,
          target_id: selectedTarget,
          filename_prefix: scanFilename || 'scan'
        })
      });

      if (response.ok) {
        alert(t.success);
        scanFilename = '';
      } else {
        const error = await response.json();
        alert(`${t.error}: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`${t.error}: ${error.message}`);
    } finally {
      isScanning = false;
    }
  }

  function startBatchMode() {
    if (!selectedScanner) {
      alert(t.pleaseSelect);
      return;
    }
    batchMode = true;
    batchPages = [];
  }

  async function addPageToBatch() {
    if (!selectedScanner || !selectedProfile) {
      alert(t.pleaseSelect);
      return;
    }
    
    isBatchScanning = true;
    try {
      const response = await fetch(`${API_BASE}/scan/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: selectedScanner,
          profile_id: selectedProfile
        })
      });

      if (response.ok) {
        const data = await response.json();
        batchPages.push({
          id: Date.now(),
          url: data.preview_url,
          pageNumber: batchPages.length + 1
        });
      } else {
        const error = await response.json();
        alert(`${t.error}: ${error.detail || 'Scan failed'}`);
      }
    } catch (error) {
      alert(`${t.error}: ${error.message}`);
    } finally {
      isBatchScanning = false;
    }
  }

  async function finishBatch() {
    if (batchPages.length === 0 || !selectedTarget) {
      alert(t.pleaseSelect);
      return;
    }

    isScanning = true;
    try {
      const response = await fetch(`${API_BASE}/scan/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: selectedScanner,
          pages: batchPages.map(p => ({ preview_url: p.url })),
          target_id: selectedTarget,
          filename_prefix: scanFilename || 'scan'
        })
      });

      if (response.ok) {
        alert(t.success);
        batchMode = false;
        batchPages = [];
        scanFilename = '';
      } else {
        const error = await response.json();
        alert(`${t.error}: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`${t.error}: ${error.message}`);
    } finally {
      isScanning = false;
    }
  }

  function cancelBatch() {
    batchMode = false;
    batchPages = [];
  }

  function formatScannerName(name) {
    return name.replace(/_/g, ' ').replace(/\[.*?\]/g, '').trim();
  }
</script>

<svelte:head>
  <title>{t.title} - Scan2Target</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
</svelte:head>

<main>
  <div class="header">
    <h1>📱 {t.title}</h1>
    <button class="lang-toggle" on:click={() => currentLang = currentLang === 'en' ? 'de' : 'en'}>
      {currentLang === 'en' ? '🇩🇪' : '🇺🇸'}
    </button>
  </div>

  {#if isLoading}
    <div class="loading">{t.loading}</div>
  {:else}
    <div class="container">
      <!-- Scanner Selection -->
      <div class="card">
        <label>{t.selectScanner}</label>
        <select bind:value={selectedScanner} disabled={batchMode}>
          <option value="">-- {t.selectScanner} --</option>
          {#each scanners as scanner}
            <option value={scanner.id}>
              {#if scanner.is_favorite}⭐ {/if}{formatScannerName(scanner.name)}
            </option>
          {/each}
        </select>
        {#if scanners.length === 0}
          <p class="muted">{t.noScanners}</p>
        {/if}
      </div>

      <!-- Target Selection -->
      <div class="card">
        <label>{t.selectTarget}</label>
        <select bind:value={selectedTarget} disabled={batchMode && batchPages.length > 0}>
          <option value="">-- {t.selectTarget} --</option>
          {#each targets as target}
            <option value={target.id}>
              {#if target.is_favorite}⭐ {/if}{target.name}
            </option>
          {/each}
        </select>
        {#if targets.length === 0}
          <p class="muted">{t.noTargets}</p>
        {/if}
      </div>

      <!-- Profile Selection -->
      <div class="card">
        <label>{t.selectProfile}</label>
        <select bind:value={selectedProfile} disabled={batchMode}>
          {#each profiles as profile}
            <option value={profile.id}>{profile.name}</option>
          {/each}
        </select>
      </div>

      <!-- Filename -->
      <div class="card">
        <label>{t.filename}</label>
        <input 
          type="text" 
          bind:value={scanFilename} 
          placeholder={t.filenamePlaceholder}
          disabled={batchMode && batchPages.length > 0}
        />
      </div>

      {#if !batchMode}
        <!-- Normal Scan Buttons -->
        <div class="actions">
          <button 
            class="btn btn-primary btn-large"
            on:click={() => startScan('Flatbed')}
            disabled={isScanning || !selectedScanner || !selectedTarget}
          >
            {isScanning ? t.scanning : t.scanSingle}
          </button>

          <button 
            class="btn btn-secondary btn-large"
            on:click={() => startScan('ADF')}
            disabled={isScanning || !selectedScanner || !selectedTarget}
          >
            {isScanning ? t.scanning : t.scanMulti}
          </button>

          <button 
            class="btn btn-ghost btn-large"
            on:click={startBatchMode}
            disabled={!selectedScanner}
          >
            {t.scanBatch}
          </button>
        </div>
      {:else}
        <!-- Batch Mode UI -->
        <div class="card batch-card">
          <div class="batch-header">
            <span class="batch-title">📑 {t.batchActive}</span>
            <span class="badge">{t.pagesInBatch}: {batchPages.length}</span>
          </div>

          {#if batchPages.length > 0}
            <div class="batch-pages">
              {#each batchPages as page}
                <div class="page-thumb">
                  <img src={page.url} alt="Page {page.pageNumber}" />
                  <div class="page-number">{page.pageNumber}</div>
                </div>
              {/each}
            </div>
          {/if}

          <button 
            class="btn btn-primary btn-large"
            on:click={addPageToBatch}
            disabled={isBatchScanning}
          >
            {isBatchScanning ? t.scanning : t.addPage}
          </button>

          <div class="batch-actions">
            <button 
              class="btn btn-success"
              on:click={finishBatch}
              disabled={batchPages.length === 0 || !selectedTarget || isScanning}
            >
              {isScanning ? t.scanning : t.finishBatch}
            </button>
            <button 
              class="btn btn-danger"
              on:click={cancelBatch}
              disabled={isScanning}
            >
              {t.cancelBatch}
            </button>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    color: #333;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
  }

  main {
    padding: env(safe-area-inset-top, 20px) 16px env(safe-area-inset-bottom, 20px);
    max-width: 600px;
    margin: 0 auto;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding: 16px 20px;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  }

  h1 {
    font-size: 24px;
    margin: 0;
    font-weight: 700;
    color: #667eea;
  }

  .lang-toggle {
    font-size: 24px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px;
    transition: transform 0.2s;
  }

  .lang-toggle:active {
    transform: scale(0.9);
  }

  .loading {
    text-align: center;
    padding: 60px 20px;
    font-size: 18px;
    color: white;
    font-weight: 500;
  }

  .container {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .card {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  }

  .batch-card {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
    border: 2px solid #667eea;
  }

  label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: #555;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  select, input {
    width: 100%;
    padding: 16px;
    font-size: 16px;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    background: white;
    color: #333;
    box-sizing: border-box;
    transition: all 0.2s;
    -webkit-appearance: none;
    appearance: none;
  }

  select {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 20 20'%3E%3Cpath fill='%23667eea' d='M10 13l-5-5h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 40px;
  }

  select:focus, input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  select:disabled, input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .muted {
    color: #999;
    font-size: 14px;
    margin: 8px 0 0;
  }

  .actions {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 8px;
  }

  .btn {
    padding: 18px 24px;
    font-size: 18px;
    font-weight: 600;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }

  .btn:active {
    transform: scale(0.98);
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none !important;
  }

  .btn-large {
    padding: 24px 32px;
    font-size: 20px;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .btn-secondary {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
  }

  .btn-success {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    color: white;
    flex: 2;
  }

  .btn-danger {
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    color: white;
    flex: 1;
  }

  .btn-ghost {
    background: rgba(255, 255, 255, 0.9);
    color: #667eea;
    border: 2px dashed #667eea;
  }

  .batch-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .batch-title {
    font-weight: 700;
    font-size: 18px;
    color: #667eea;
  }

  .badge {
    background: #667eea;
    color: white;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
  }

  .batch-pages {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
    padding: 12px;
    background: white;
    border-radius: 12px;
  }

  .page-thumb {
    position: relative;
    aspect-ratio: 1;
  }

  .page-thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 8px;
    border: 2px solid #e0e0e0;
  }

  .page-number {
    position: absolute;
    top: 4px;
    left: 4px;
    background: #667eea;
    color: white;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
  }

  .batch-actions {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 8px;
    margin-top: 12px;
  }

  /* Touch optimizations */
  @media (hover: none) {
    .btn:hover {
      transform: none;
    }
  }

  /* Landscape mode */
  @media (orientation: landscape) and (max-height: 600px) {
    main {
      padding: 12px;
    }
    .header {
      padding: 12px 16px;
      margin-bottom: 16px;
    }
    h1 {
      font-size: 20px;
    }
  }
</style>
