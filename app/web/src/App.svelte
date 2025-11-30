<script>
  import { onMount } from 'svelte';
  import NavBar from './components/NavBar.svelte';
  import SectionCard from './components/SectionCard.svelte';
  import StatGrid from './components/StatGrid.svelte';

  const API_BASE = '/api/v1';

  // Language/i18n support
  let currentLang = localStorage.getItem('raspscan_lang') || 'en';
  
  const translations = {
    en: {
      brand: 'RaspScan',
      dashboard: 'Dashboard',
      scan: 'Scan',
      activeScansMenu: 'Active Scans',
      targets: 'Targets',
      history: 'History',
      heroTagline: 'Linux · FastAPI · Svelte',
      heroTitle: 'Central hub for scanning.',
      heroDescription: 'Trigger scans on devices without physical buttons, and route files to SMB, email, Paperless-ngx, or webhooks.',
      startScan: 'Start a scan',
      liveStatus: 'Live status',
      scannersFound: 'Scanners found',
      todayScans: 'Today scans',
      completedToday: 'Completed today',
      activeJobs: 'Active jobs',
      inProgress: 'In progress',
      configuredScanners: 'Configured Scanners',
      loadingScanners: '⏳ Loading scanners...',
      noScannersConfigured: 'No scanners configured. Click "Discover Scanners" below to add.',
      recommended: '⭐ Recommended',
      online: 'online',
      offline: 'offline',
      removeFavorite: 'Remove from favorites',
      addFavorite: 'Add to favorites',
      remove: 'Remove',
      scannerManagement: 'Scanner Management',
      scannerManagementDesc: 'Discover and add USB/wireless scanners via SANE/eSCL. Scanners must be manually added - they are never added automatically.',
      discoverScanners: 'Discover Scanners',
      searching: 'Searching...',
      lastScan: 'Last scan',
      clickRefresh: 'Click "Discover" to refresh',
      discoveredScanners: 'Discovered Scanners',
      alreadyAdded: '✓ Already Added',
      notAddedYet: 'Not Added Yet',
      addScanner: 'Add Scanner',
      noScannersFound: 'No scanners found. Make sure scanners are powered on and connected (USB or network).',
      quickProfiles: 'Quick profiles',
      scanSubtitle: 'Start server-side scans and route results to targets.',
      launchScan: 'Launch a scan',
      chooseScanner: 'Choose scanner',
      selectScanner: '-- Select scanner --',
      scanSource: '🆕 Scan Source',
      flatbed: '📄 Flatbed (single page)',
      adf: '📚 Document Feeder (ADF) - Multi-page',
      adfDesc: 'ADF automatically scans all pages in the feeder',
      profile: 'Profile',
      target: 'Target',
      selectTarget: '-- Select target --',
      filename: 'Filename (optional)',
      filenamePlaceholder: 'e.g. invoice_2025',
      filenameDesc: 'Leave empty for auto-generated name (scan_UUID)',
      startScanButton: 'Start scan',
      activeScans: 'Active Scans',
      scansInProgress: 'Scans in progress',
      mostRecentScan: 'Most recent scan',
      noScansYet: 'No scans yet',
      noScansDesc: 'No scans yet. Start your first scan above.',
      scanStatus: 'Scan:',
      uploadStatus: 'Upload:',
      queued: '⏳ Queued',
      running: '🔄 Running',
      waiting: '⏸️ Waiting',
      done: '✅ Done',
      failed: '❌ Failed',
      skipped: '⏸️ Skipped',
      retry: '🔄 Retry',
      device: 'Device',
      started: 'Started',
      completed: 'Completed',
      deliveryTargets: 'Delivery targets',
      loadingTargets: '⏳ Loading targets...',
      noTargetsConfigured: 'No targets configured yet.',
      enabled: 'Enabled',
      disabled: 'Disabled',
      test: '🔍 Test',
      addTarget: 'Add target',
      type: 'Type',
      name: 'Name',
      namePlaceholder: 'e.g. NAS scans',
      connection: 'Connection',
      connectionPlaceholder: '//nas/share or URL',
      username: 'Username',
      usernamePlaceholder: 'Network username',
      password: 'Password',
      passwordPlaceholder: 'Network password',
      testAndSave: 'Test & Save',
      saveWithoutTest: 'Save without test',
      testSaveHint: '💡 "Test & Save" validates the connection before saving. Use "Save without test" if the server is temporarily offline.',
      targetsSubtitle: 'Destinations for scanned documents.',
      historySubtitle: 'Recent scan and print jobs.',
      loadingHistory: '⏳ Loading history...',
      noJobsHistory: 'No jobs in history yet.',
      id: 'ID',
      time: 'Time',
      status: 'Status',
      uploadFailed: '⚠️ Upload failed',
      retryUpload: '🔄 Retry Upload',
      pleaseSelectScanner: '⚠️ Please select a scanner below',
      pleaseSelectTarget: '⚠️ Please select a target below'
    },
    de: {
      brand: 'RaspScan',
      dashboard: 'Dashboard',
      scan: 'Scannen',
      activeScansMenu: 'Aktive Scans',
      targets: 'Ziele',
      history: 'Verlauf',
      heroTagline: 'Linux · FastAPI · Svelte',
      heroTitle: 'Zentrale für Scannen.',
      heroDescription: 'Starten Sie Scans auf Geräten ohne physische Tasten und leiten Sie Dateien an SMB, E-Mail, Paperless-ngx oder Webhooks weiter.',
      startScan: 'Scan starten',
      liveStatus: 'Live-Status',
      scannersFound: 'Scanner gefunden',
      todayScans: 'Heutige Scans',
      completedToday: 'Heute abgeschlossen',
      activeJobs: 'Aktive Aufträge',
      inProgress: 'In Bearbeitung',
      configuredScanners: 'Konfigurierte Scanner',
      loadingScanners: '⏳ Scanner werden geladen...',
      noScannersConfigured: 'Keine Scanner konfiguriert. Klicken Sie unten auf "Scanner suchen", um welche hinzuzufügen.',
      recommended: '⭐ Empfohlen',
      online: 'online',
      offline: 'offline',
      removeFavorite: 'Aus Favoriten entfernen',
      addFavorite: 'Zu Favoriten hinzufügen',
      remove: 'Entfernen',
      scannerManagement: 'Scanner-Verwaltung',
      scannerManagementDesc: 'USB/WLAN-Scanner über SANE/eSCL suchen und hinzufügen. Scanner müssen manuell hinzugefügt werden - sie werden nie automatisch hinzugefügt.',
      discoverScanners: 'Scanner suchen',
      searching: 'Suche läuft...',
      lastScan: 'Letzte Suche',
      clickRefresh: 'Klicken Sie auf "Suchen", um zu aktualisieren',
      discoveredScanners: 'Gefundene Scanner',
      alreadyAdded: '✓ Bereits hinzugefügt',
      notAddedYet: 'Noch nicht hinzugefügt',
      addScanner: 'Scanner hinzufügen',
      noScannersFound: 'Keine Scanner gefunden. Stellen Sie sicher, dass Scanner eingeschaltet und verbunden sind (USB oder Netzwerk).',
      quickProfiles: 'Schnellprofile',
      scanSubtitle: 'Starten Sie serverseitige Scans und leiten Sie Ergebnisse an Ziele weiter.',
      launchScan: 'Scan starten',
      chooseScanner: 'Scanner wählen',
      selectScanner: '-- Scanner auswählen --',
      scanSource: '🆕 Scan-Quelle',
      flatbed: '📄 Flachbett (einzelne Seite)',
      adf: '📚 Dokumenteneinzug (ADF) - Mehrere Seiten',
      adfDesc: 'ADF scannt automatisch alle Seiten im Einzug',
      profile: 'Profil',
      target: 'Ziel',
      selectTarget: '-- Ziel auswählen --',
      filename: 'Dateiname (optional)',
      filenamePlaceholder: 'z.B. rechnung_2025',
      filenameDesc: 'Leer lassen für automatisch generierten Namen (scan_UUID)',
      startScanButton: 'Scan starten',
      activeScans: 'Aktive Scans',
      scansInProgress: 'Scans werden ausgeführt',
      mostRecentScan: 'Zuletzt gescannt',
      noScansYet: 'Noch keine Scans',
      noScansDesc: 'Noch keine Scans. Starten Sie Ihren ersten Scan oben.',
      scanStatus: 'Scan:',
      uploadStatus: 'Upload:',
      queued: '⏳ Warteschlange',
      running: '🔄 Läuft',
      waiting: '⏸️ Wartet',
      done: '✅ Fertig',
      failed: '❌ Fehlgeschlagen',
      skipped: '⏸️ Übersprungen',
      retry: '🔄 Wiederholen',
      device: 'Gerät',
      started: 'Gestartet',
      completed: 'Abgeschlossen',
      deliveryTargets: 'Lieferziele',
      loadingTargets: '⏳ Ziele werden geladen...',
      noTargetsConfigured: 'Noch keine Ziele konfiguriert.',
      enabled: 'Aktiviert',
      disabled: 'Deaktiviert',
      test: '🔍 Testen',
      addTarget: 'Ziel hinzufügen',
      type: 'Typ',
      name: 'Name',
      namePlaceholder: 'z.B. NAS Scans',
      connection: 'Verbindung',
      connectionPlaceholder: '//nas/freigabe oder URL',
      username: 'Benutzername',
      usernamePlaceholder: 'Netzwerk-Benutzername',
      password: 'Passwort',
      passwordPlaceholder: 'Netzwerk-Passwort',
      testAndSave: 'Testen & Speichern',
      saveWithoutTest: 'Ohne Test speichern',
      testSaveHint: '💡 "Testen & Speichern" validiert die Verbindung vor dem Speichern. Verwenden Sie "Ohne Test speichern", wenn der Server vorübergehend offline ist.',
      targetsSubtitle: 'Ziele für gescannte Dokumente.',
      historySubtitle: 'Letzte Scan- und Druckaufträge.',
      loadingHistory: '⏳ Verlauf wird geladen...',
      noJobsHistory: 'Noch keine Aufträge im Verlauf.',
      id: 'ID',
      time: 'Zeit',
      status: 'Status',
      uploadFailed: '⚠️ Upload fehlgeschlagen',
      retryUpload: '🔄 Upload wiederholen',
      pleaseSelectScanner: '⚠️ Bitte wählen Sie unten einen Scanner aus',
      pleaseSelectTarget: '⚠️ Bitte wählen Sie unten ein Ziel aus'
    }
  };
  
  $: t = translations[currentLang];
  
  function changeLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('raspscan_lang', lang);
  }

  let scanners = [];
  let targets = [];
  let history = [];
  let statCards = [];
  let activeJobs = [];
  let lastCompletedJob = null;
  
  let selectedScanner = '';
  let selectedProfile = '';
  let selectedTarget = '';
  let scanFilename = '';
  let scanSource = 'Flatbed';
  
  // Auto-select profile when scan source changes
  $: if (scanSource) {
    const profilesForSource = quickProfiles.filter(p => p.source === scanSource);
    if (profilesForSource.length > 0) {
      // For ADF, prefer multi-page profile
      if (scanSource === 'ADF') {
        const multiPageProfile = profilesForSource.find(p => p.id.includes('multipage') || p.name.toLowerCase().includes('multi'));
        selectedProfile = multiPageProfile ? multiPageProfile.id : profilesForSource[0].id;
      } else {
        // For Flatbed, prefer Document @200 DPI (small)
        const defaultProfile = profilesForSource.find(p => p.id.includes('200') || p.name.toLowerCase().includes('200'));
        selectedProfile = defaultProfile ? defaultProfile.id : profilesForSource[0].id;
      }
    }
  }
  
  let targetType = 'SMB';
  let targetName = '';
  let targetConnection = '';
  let targetUsername = '';
  let targetPassword = '';
  

  let discoveredDevices = [];
  let discoveredScanners = [];
  let isDiscovering = false;
  let lastDiscoveryTime = null;
  
  let isLoadingDevices = true;
  let isLoadingTargets = true;
  let isLoadingHistory = true;
  let pollInterval = null;
  let expandedThumbnail = null; // Track which thumbnail is expanded

  $: navLinks = [
    { label: t.dashboard, href: '#dashboard' },
    { label: t.scan, href: '#scan' },
    { label: t.activeScansMenu, href: '#active-scans' },
    { label: t.targets, href: '#targets' },
    { label: t.history, href: '#history' }
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
    
    // Start polling for active jobs
    pollActiveJobs();
    pollInterval = setInterval(pollActiveJobs, 3000);
    
    // Cleanup on unmount
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
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
        // Use the name from API directly - it's already well formatted
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
        scanners = devices.filter(d => d.device_type === 'scanner');
        // Auto-select favorite scanner if none selected
        const favoriteScanner = scanners.find(s => s.is_favorite);
        if (favoriteScanner && !selectedScanner) {
          selectedScanner = favoriteScanner.id;
        }
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
        // Auto-select favorite target if none selected
        const favorite = targets.find(t => t.is_favorite);
        if (favorite && !selectedTarget) {
          selectedTarget = favorite.id;
        }
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

  async function pollActiveJobs() {
    try {
      const res = await fetch(`${API_BASE}/history`);
      if (res.ok) {
        const allJobs = await res.json();
        const previousActiveCount = activeJobs.length;
        activeJobs = allJobs.filter(j => j.status === 'queued' || j.status === 'running');
        
        // Try to load thumbnails for running jobs
        for (const job of activeJobs) {
          if (job.status === 'running') {
            try {
              // Thumbnail pattern: scan_{job_id}_thumb.jpg
              const thumbRes = await fetch(`/thumbnails/scan_${job.id}_thumb.jpg`, { method: 'HEAD' });
              if (thumbRes.ok) {
                job.thumbnailUrl = `/thumbnails/scan_${job.id}_thumb.jpg?t=${Date.now()}`;
              }
            } catch (e) {
              // Thumbnail not ready yet
            }
          }
        }
        
        // If a job just completed, save it to show until next scan
        if (previousActiveCount > 0 && activeJobs.length === 0) {
          const justCompleted = allJobs.find(j => j.status === 'completed');
          if (justCompleted) {
            // Load thumbnail for completed job
            try {
              const thumbRes = await fetch(`/thumbnails/scan_${justCompleted.id}_thumb.jpg`, { method: 'HEAD' });
              if (thumbRes.ok) {
                justCompleted.thumbnailUrl = `/thumbnails/scan_${justCompleted.id}_thumb.jpg?t=${Date.now()}`;
              }
            } catch (e) {
              // No thumbnail
            }
            lastCompletedJob = justCompleted;
          }
          loadHistory();
        }
        
        // Clear last completed job when new scan starts
        if (activeJobs.length > 0 && lastCompletedJob) {
          lastCompletedJob = null;
        }
      }
    } catch (error) {
      console.error('Failed to poll active jobs:', error);
    }
  }

  function updateStats() {
    const todayScans = history.filter(h => h.job_type === 'scan' && isToday(h.created_at)).length;
    const activeJobsCount = history.filter(h => h.status === 'queued' || h.status === 'running').length;

    statCards = [
      { label: t.scannersFound, value: String(scanners.length).padStart(2, '0'), icon: '📑', sub: 'eSCL + SANE' },
      { label: t.todayScans, value: String(todayScans), icon: '✅', sub: t.completedToday },
      { label: t.activeJobs, value: String(activeJobsCount).padStart(2, '0'), icon: '⏳', sub: t.inProgress }
    ];
  }

  function isToday(timestamp) {
    const date = new Date(timestamp);
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }

  async function startScan() {
    if (!selectedScanner) {
      alert('Please select a scanner');
      return;
    }
    
    if (!selectedProfile) {
      alert('Please select a scan profile');
      return;
    }
    
    if (!selectedTarget) {
      alert('Please select a target');
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
      description: null,
      is_favorite: false
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
        alert('✅ Target saved successfully');
        targetName = '';
        targetConnection = '';
        targetUsername = '';
        targetPassword = '';
        await loadTargets();
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

  async function toggleFavorite(targetId, isFavorite) {
    try {
      const target = targets.find(t => t.id === targetId);
      if (!target) return;
      
      const response = await fetch(`${API_BASE}/targets/${targetId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...target,
          is_favorite: isFavorite
        })
      });
      
      if (response.ok) {
        await loadTargets();
      } else {
        alert('Failed to update favorite');
      }
    } catch (error) {
      console.error('Toggle favorite error:', error);
      alert('Failed to update favorite');
    }
  }

  async function toggleDeviceFavorite(deviceId, isFavorite) {
    try {
      const encodedId = encodeURIComponent(deviceId);
      const response = await fetch(`${API_BASE}/devices/${encodedId}/favorite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_favorite: isFavorite })
      });
      
      if (response.ok) {
        await loadDevices();
      } else {
        const error = await response.json().catch(() => ({}));
        console.error('Failed to update favorite:', error);
        alert('Failed to update favorite');
      }
    } catch (error) {
      console.error('Toggle device favorite error:', error);
      alert('Failed to update favorite');
    }
  }

  async function testTarget(targetId) {
    const target = targets.find(t => t.id === targetId);
    if (!target) return;
    
    const testBtn = event.target;
    const originalText = testBtn.textContent;
    testBtn.textContent = '⏳ Testing...';
    testBtn.disabled = true;
    
    try {
      const response = await fetch(`${API_BASE}/targets/${targetId}/test`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.status === 'ok') {
        alert(`✅ Connection successful!\n\nTarget: ${target.name}\nType: ${target.type}`);
      } else {
        alert(`❌ Connection failed\n\n${result.message || 'Unable to connect to target'}`);
      }
    } catch (error) {
      console.error('Test target error:', error);
      alert(`❌ Test failed: ${error.message}`);
    } finally {
      testBtn.textContent = originalText;
      testBtn.disabled = false;
    }
  }

  async function retryUpload(jobId) {
    const job = history.find(j => j.id === jobId);
    if (!job) return;
    
    if (!confirm(`Retry upload for job ${jobId.slice(0, 8)}?\n\nTarget: ${job.target_id}`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/history/${jobId}/retry-upload`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`✅ ${result.message}`);
        await loadHistory();
      } else {
        const error = await response.json();
        alert(`❌ Retry failed\n\n${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Retry upload error:', error);
      alert(`❌ Retry failed: ${error.message}`);
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
        alert(`✅ ${typeName.charAt(0).toUpperCase() + typeName.slice(1)} removed successfully`);
        await loadDevices();
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

<NavBar brand={t.brand} links={navLinks} {currentLang} onLanguageChange={changeLanguage} />

<main class="page">
  <section id="dashboard" class="hero">
    <div>
      <p class="eyebrow">{t.heroTagline}</p>
      <h1>{t.heroTitle}</h1>
      <p class="lede">{t.heroDescription}</p>
      <div class="actions">
        <button 
          class="primary" 
          on:click={startScan}
          style="font-size: 1.1rem; padding: 1rem 2rem; font-weight: 600;"
          disabled={!selectedScanner || !selectedTarget}
        >
          {t.startScan}
        </button>
        {#if !selectedScanner || !selectedTarget}
          <p class="muted" style="margin-top: 0.5rem; font-size: 0.875rem;">
            {!selectedScanner ? t.pleaseSelectScanner : t.pleaseSelectTarget}
          </p>
        {/if}
      </div>
    </div>
    <div class="card hero-card">
      <div class="card-title">{t.liveStatus}</div>
      <StatGrid cards={statCards} />
    </div>
  </section>

  <SectionCard id="scan" title={t.scan} subtitle={t.scanSubtitle}>
    <div class="grid two-cols">
      <div>
        <h3>{t.configuredScanners}</h3>
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
                    {#if scanner.is_favorite}⭐ {/if}{scanner.name}
                    {#if scanner.connection_type && scanner.connection_type.includes('eSCL')}
                      <span class="badge success" style="margin-left: 0.5rem; font-size: 0.7rem;">⭐ Recommended</span>
                    {/if}
                  </div>
                  <div class="muted">{scanner.connection_type || scanner.type || 'Unknown'}</div>
                  <span class="badge {scanner.status === 'online' ? 'success' : 'warning'}">{scanner.status || 'unknown'}</span>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                  <button 
                    class="ghost small" 
                    on:click={() => toggleDeviceFavorite(scanner.id, !scanner.is_favorite)}
                    title="{scanner.is_favorite ? 'Remove from' : 'Add to'} favorites"
                  >
                    {scanner.is_favorite ? '⭐' : '☆'}
                  </button>
                  <button class="ghost small" on:click={() => removeDevice(scanner.id, 'scanner')}>Remove</button>
                </div>
              </li>
            {/each}
          </ul>
        {/if}
        
        <h3 class="mt">{t.scannerManagement}</h3>
        <p class="muted">{t.scannerManagementDesc}</p>
        <button class="primary" on:click={discoverScanners} disabled={isDiscovering}>
          {isDiscovering ? t.searching : t.discoverScanners}
        </button>
        {#if lastDiscoveryTime}
          <p class="muted small" style="margin-top: 0.5rem;">
            {t.lastScan}: {lastDiscoveryTime.toLocaleTimeString()} · {t.clickRefresh}
          </p>
        {/if}
        
        {#if discoveredScanners.length > 0}
          <h4 class="mt">{t.discoveredScanners} ({discoveredScanners.length})</h4>
          <ul class="list">
            {#each discoveredScanners as device}
              <li>
                <div class="list-title">{device.name}</div>
                <div class="muted">
                  {device.connection_type || device.type}
                  {#if device.connection_type && device.connection_type.includes('eSCL')}
                    <span class="badge success" style="margin-left: 0.5rem;">{t.recommended}</span>
                  {/if}
                  {#if device.already_added}
                    <span class="badge success" style="margin-left: 0.5rem;">{t.alreadyAdded}</span>
                  {:else}
                    <span class="badge warning" style="margin-left: 0.5rem;">{t.notAddedYet}</span>
                  {/if}
                </div>
                <div class="muted small" style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.25rem;">
                  {device.uri}
                </div>
                {#if !device.already_added}
                  <button class="primary small" on:click={() => addDiscoveredScanner(device)}>{t.addScanner}</button>
                {:else}
                  <button class="ghost small" disabled>{t.alreadyAdded}</button>
                {/if}
              </li>
            {/each}
          </ul>
        {:else if !isDiscovering}
          <p class="muted small mt">{t.noScannersFound}</p>
        {/if}
        
        <h3 class="mt">{t.quickProfiles}</h3>
        <div class="chip-row">
          {#each quickProfiles as profile}
            <div class="chip" title={profile.description || profile.name}>
              {profile.source === 'ADF' ? '📚' : '📄'} {profile.name}
            </div>
          {/each}
        </div>
      </div>
      <div class="panel">
        <div class="panel-header">{t.launchScan}</div>
        <div class="panel-body">
          <label for="scanner-select">{t.chooseScanner}</label>
          <select id="scanner-select" bind:value={selectedScanner}>
            <option value="">-- Select scanner --</option>
            {#each scanners as scanner}
              <option value={scanner.id}>
                {#if scanner.is_favorite}⭐ {/if}{scanner.name}
                {#if scanner.connection_type && scanner.connection_type.includes('eSCL')} (Recommended){/if}
              </option>
            {/each}
          </select>
          
          <label for="source-select">{t.scanSource}</label>
          <select id="source-select" bind:value={scanSource} style="width: 100%; padding: 8px 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 14px;">
            <option value="Flatbed">📄 Flatbed (single page)</option>
            <option value="ADF">📚 Document Feeder (ADF) - Multi-page</option>
          </select>
          <p class="muted small" style="margin-top: 0.25rem; margin-bottom: 0.75rem;">{t.adfDesc}</p>
          
          <label for="profile-select">{t.profile}</label>
          <select id="profile-select" bind:value={selectedProfile}>
            {#each quickProfiles.filter(p => p.source === scanSource) as profile}
              <option value={profile.id}>
                {profile.name}
              </option>
            {/each}
          </select>
          <label for="target-select">{t.target}</label>
          <select id="target-select" bind:value={selectedTarget}>
            <option value="">-- Select target --</option>
            {#each targets as target}
              <option value={target.id}>
                {#if target.is_favorite}⭐ {/if}{target.name}
              </option>
            {/each}
          </select>
          <label for="filename-input">{t.filename}</label>
          <input 
            id="filename-input" 
            type="text" 
            bind:value={scanFilename} 
            placeholder={t.filenamePlaceholder} 
            style="width: 100%; padding: 8px 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 14px;"
          />
          <p class="muted small" style="margin-top: 0.25rem; margin-bottom: 0.75rem;">{t.filenameDesc}</p>
          
          <button class="primary block" on:click={startScan}>{t.startScanButton}</button>
        </div>
      </div>
    </div>
  </SectionCard>

  <!-- Active Scans Section -->
  <SectionCard id="active-scans" title={t.activeScans} subtitle={activeJobs.length > 0 ? t.scansInProgress : lastCompletedJob ? t.mostRecentScan : t.noScansYet}>
    {#if activeJobs.length > 0 || lastCompletedJob}
    <div class="grid" style="grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
      {#each activeJobs as job}
        <div class="panel" style="padding: 1rem;">
          <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.75rem;">
            <span class="muted" style="font-size: 0.875rem;">Job #{job.id.slice(0, 8)}</span>
          </div>
          
          {#if job.thumbnailUrl}
            <div style="margin-bottom: 0.75rem; cursor: pointer; display: flex; justify-content: flex-start;" on:click={() => expandedThumbnail = expandedThumbnail === job.id ? null : job.id}>
              <img 
                src={job.thumbnailUrl} 
                alt="Scan preview" 
                style="width: {expandedThumbnail === job.id ? '100%' : '50%'}; height: auto; border-radius: 6px; border: 1px solid var(--border); transition: width 0.3s ease;"
                title="Click to {expandedThumbnail === job.id ? 'shrink' : 'expand'}"
              />
            </div>
          {:else if job.status === 'running'}
            <div style="margin-bottom: 0.75rem; padding: 3rem 1rem; background: var(--surface-dim); border-radius: 6px; text-align: center;">
              <p class="muted">🖨️ Scanning...</p>
            </div>
          {/if}
          
          <!-- Status breakdown -->
          <div style="margin-bottom: 0.75rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
              <span style="font-size: 0.875rem; font-weight: 500; width: 50px;">Scan:</span>
              <span class={`badge ${job.status === 'running' ? 'warning' : 'info'}`} style="font-size: 0.875rem;">
                {job.status === 'queued' ? '⏳ Queued' : '🔄 Running'}
              </span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="font-size: 0.875rem; font-weight: 500; width: 50px; opacity: 0.5;">Upload:</span>
              <span class="badge" style="font-size: 0.875rem; opacity: 0.5;">⏸️ Waiting</span>
            </div>
          </div>
          
          <div style="font-size: 0.875rem;">
            <div style="margin-bottom: 0.25rem;">
              <span class="muted">Device:</span> {job.device_id || 'N/A'}
            </div>
            <div style="margin-bottom: 0.25rem;">
              <span class="muted">Target:</span> {targets.find(t => t.id === job.target_id)?.name || job.target_id || 'N/A'}
            </div>
            <div>
              <span class="muted">Started:</span> {new Date(job.created_at).toLocaleTimeString()}
            </div>
          </div>
        </div>
      {/each}
      
      {#if lastCompletedJob && activeJobs.length === 0}
        <div class="panel" style="padding: 1rem;">
          <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.75rem;">
            <span class="muted" style="font-size: 0.875rem;">Job #{lastCompletedJob.id.slice(0, 8)}</span>
          </div>
          
          {#if lastCompletedJob.thumbnailUrl}
            <div style="margin-bottom: 0.75rem; cursor: pointer; display: flex; justify-content: flex-start;" on:click={() => expandedThumbnail = expandedThumbnail === lastCompletedJob.id ? null : lastCompletedJob.id}>
              <img 
                src={lastCompletedJob.thumbnailUrl} 
                alt="Scan preview" 
                style="width: {expandedThumbnail === lastCompletedJob.id ? '100%' : '50%'}; height: auto; border-radius: 6px; border: 1px solid var(--border); transition: width 0.3s ease;"
                title="Click to {expandedThumbnail === lastCompletedJob.id ? 'shrink' : 'expand'}"
              />
            </div>
          {/if}
          
          <!-- Status breakdown -->
          <div style="margin-bottom: 0.75rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
              <span style="font-size: 0.875rem; font-weight: 500; width: 50px;">Scan:</span>
              <span class={`badge ${lastCompletedJob.status === 'failed' ? 'danger' : 'success'}`} style="font-size: 0.875rem;">
                {lastCompletedJob.status === 'failed' ? '❌ Failed' : '✅ Done'}
              </span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="font-size: 0.875rem; font-weight: 500; width: 50px; {lastCompletedJob.status === 'failed' ? 'opacity: 0.5;' : ''}">Upload:</span>
              <span class={`badge ${lastCompletedJob.status === 'failed' ? '' : lastCompletedJob.message ? 'danger' : 'success'}`} 
                    style="font-size: 0.875rem; {lastCompletedJob.status === 'failed' ? 'opacity: 0.5;' : ''}">
                {lastCompletedJob.status === 'failed' ? '⏸️ Skipped' : lastCompletedJob.message ? '❌ Failed' : '✅ Done'}
              </span>
              {#if lastCompletedJob.status === 'completed' && lastCompletedJob.message}
                <button 
                  class="primary small" 
                  style="margin-left: auto; font-size: 0.75rem; padding: 0.25rem 0.5rem;"
                  on:click={() => retryUpload(lastCompletedJob.id)}
                >
                  🔄 Retry
                </button>
              {/if}
            </div>
          </div>
          
          {#if lastCompletedJob.message}
            <div style="margin-bottom: 0.75rem; font-size: 0.8rem; color: var(--danger); padding: 0.5rem; background: rgba(255, 100, 100, 0.1); border-radius: 4px; border: 1px solid rgba(255, 100, 100, 0.3);">
              {lastCompletedJob.message}
            </div>
          {/if}
          
          <div style="font-size: 0.875rem;">
            <div style="margin-bottom: 0.25rem;">
              <span class="muted">Device:</span> {lastCompletedJob.device_id || 'N/A'}
            </div>
            <div style="margin-bottom: 0.25rem;">
              <span class="muted">Target:</span> {targets.find(t => t.id === lastCompletedJob.target_id)?.name || lastCompletedJob.target_id || 'N/A'}
            </div>
            <div>
              <span class="muted">Completed:</span> {new Date(lastCompletedJob.created_at).toLocaleTimeString()}
            </div>
          </div>
        </div>
      {/if}
    </div>
    {:else}
      <p class="muted">{t.noScansDesc}</p>
    {/if}
  </SectionCard>

  <SectionCard id="targets" title={t.targets} subtitle={t.targetsSubtitle}>
    <div class="grid two-cols">
      <div>
        <h3>{t.deliveryTargets}</h3>
        {#if isLoadingTargets}
          <p class="muted">⏳ Loading targets...</p>
        {:else if targets.length === 0}
          <p class="muted">No targets configured yet.</p>
        {:else}
          <ul class="list">
            {#each targets as target}
              <li style="display: flex; align-items: center; justify-content: space-between;">
                <div style="flex: 1;">
                  <div class="list-title">
                    {#if target.is_favorite}⭐ {/if}{target.name}
                  </div>
                  <div class="muted">{target.type}: {target.config?.connection || 'N/A'}</div>
                  <span class="badge {target.enabled ? 'success' : 'warning'}">{target.enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                  <button 
                    class="ghost small" 
                    on:click={() => testTarget(target.id)}
                    title="Test connection"
                  >
                    🔍 Test
                  </button>
                  <button 
                    class="ghost small" 
                    on:click={() => toggleFavorite(target.id, !target.is_favorite)}
                    title="{target.is_favorite ? 'Remove from' : 'Add to'} favorites"
                  >
                    {target.is_favorite ? '⭐' : '☆'}
                  </button>
                  <button class="danger small" on:click={() => removeTarget(target.id)}>Remove</button>
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
      <div class="panel">
        <div class="panel-header">{t.addTarget}</div>
        <div class="panel-body">
          <label for="target-type">{t.type}</label>
          <select id="target-type" bind:value={targetType}>
            <option>SMB</option>
            <option>SFTP</option>
            <option>Email</option>
            <option>Paperless-ngx</option>
            <option>Webhook</option>
          </select>
          <label for="target-name">{t.name}</label>
          <input id="target-name" type="text" placeholder={t.namePlaceholder} bind:value={targetName} />
          <label for="target-connection">{t.connection}</label>
          <input id="target-connection" type="text" placeholder={t.connectionPlaceholder} bind:value={targetConnection} />
          
          {#if targetType === 'SMB'}
            <label for="target-username">{t.username}</label>
            <input id="target-username" type="text" placeholder={t.usernamePlaceholder} bind:value={targetUsername} />
            <label for="target-password">{t.password}</label>
            <input id="target-password" type="password" placeholder={t.passwordPlaceholder} bind:value={targetPassword} />
          {/if}
          
          <div style="display: flex; gap: 0.5rem;">
            <button class="primary" style="flex: 1;" on:click={() => saveTarget(false)}>{t.testAndSave}</button>
            <button class="ghost" style="flex: 1;" on:click={() => saveTarget(true)}>{t.saveWithoutTest}</button>
          </div>
          <p style="font-size: 0.85rem; color: #888; margin-top: 0.5rem;">
            {t.testSaveHint}
          </p>
        </div>
      </div>
    </div>
  </SectionCard>

  <SectionCard id="history" title={t.history} subtitle={t.historySubtitle}>
    {#if isLoadingHistory}
      <p class="muted">⏳ Loading history...</p>
    {:else if history.length === 0}
      <p class="muted">No jobs in history yet.</p>
    {:else}
      <div class="table" style="display: block;">
        <div style="display: grid; grid-template-columns: 100px 80px 1fr 1fr 180px 200px; gap: 1rem; padding: 0.75rem 1rem; font-weight: 600; border-bottom: 2px solid var(--border); background: var(--surface-dim);">
          <span>ID</span>
          <span>Type</span>
          <span>Device</span>
          <span>Target</span>
          <span>Time</span>
          <span>Status</span>
        </div>
        {#each history as job}
          <div style="display: grid; grid-template-columns: 100px 80px 1fr 1fr 180px 200px; gap: 1rem; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); align-items: start;">
            <span style="font-family: monospace; font-size: 0.875rem;">{job.id.slice(0, 8)}</span>
            <span style="font-size: 0.875rem;">{job.job_type}</span>
            <span style="font-size: 0.875rem; overflow: hidden; text-overflow: ellipsis;" title={job.device_id}>{job.device_id || 'N/A'}</span>
            <span style="font-size: 0.875rem;">{targets.find(t => t.id === job.target_id)?.name || job.target_id || 'N/A'}</span>
            <span style="font-size: 0.875rem;">{new Date(job.created_at).toLocaleString()}</span>
            <div>
              <span class={`badge ${job.status === 'completed' && !job.message ? 'success' : job.status === 'failed' ? 'danger' : job.message ? 'warning' : 'warning'}`}>
                {job.status === 'completed' && job.message ? '⚠️ Upload failed' : job.status}
              </span>
              {#if job.message}
                <div style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--danger); padding: 0.5rem; background: rgba(255, 100, 100, 0.1); border-radius: 4px; border: 1px solid rgba(255, 100, 100, 0.3);">
                  ❌ {job.message}
                </div>
                <button 
                  class="primary small" 
                  style="margin-top: 0.5rem; width: 100%;"
                  on:click={() => retryUpload(job.id)}
                >
                  🔄 Retry Upload
                </button>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </SectionCard>

</main>
