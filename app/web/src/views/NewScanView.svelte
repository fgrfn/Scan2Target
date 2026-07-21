<script>
  import { onDestroy, onMount } from 'svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { lang } from '../lib/i18n';
  import { captureModeFor, movedPageIds } from '../lib/scanSession';

  export let data;
  export let onNotify = () => {};
  export let onNavigate = () => {};

  let step = 1;
  let source = 'Flatbed';
  let captureMode = 'interactive';
  let category = 'document';
  let deviceId = '';
  let targetId = '';
  let profileId = '';
  let session = null;
  let resumableSessions = [];
  let pages = [];
  let previewUrls = {};
  let preview = '';
  let busy = false;
  let cancelling = false;
  let filename = '';
  let advanced = false;
  let askForAnotherPage = false;
  let optimize = true;
  let removeBlankPages = false;
  let ocr = false;
  let pdfa = false;
  let ocrLanguage = 'deu+eng';

  $: copy = $lang === 'de' ? {
    title: 'Was möchtest du scannen?', lead: 'Wähle Papierquelle, Erfassungsmodus und Qualität.',
    flatbed: 'Flachbett', flatbedHint: 'Fotos, Belege und einzelne Seiten', adf: 'Dokumenteneinzug', adfHint: 'Einzelne Seiten oder ganze Stapel',
    mode: 'ADF-Modus', interactive: 'Nach jeder Seite fragen', interactiveHint: 'Zieht pro Scan genau eine Seite ein.',
    automatic: 'Kompletten Stapel scannen', automaticHint: 'Erfasst alle eingelegten Seiten in einem Durchlauf.',
    quality: 'Inhalt', document: 'Dokument', color: 'Farbe', photo: 'Foto', advanced: 'Weitere Einstellungen',
    scanner: 'Scanner', target: 'Ziel', profile: 'Profil', preview: 'Vorschau', start: 'Scan starten', scanning: 'Scanner arbeitet …',
    resumeTitle: 'Unvollständigen Scan fortsetzen?', resumeLead: '{n} Seiten wurden sicher auf dem Server gespeichert.', resume: 'Fortsetzen', discard: 'Verwerfen',
    captureTitle: 'Seiten prüfen', captureLead: 'Drehe, sortiere oder entferne Seiten, bevor du sie speicherst.',
    anotherQuestion: 'Möchtest du eine weitere Seite scannen?', anotherStack: 'Möchtest du einen weiteren Stapel scannen?',
    anotherLead: 'Lege die nächste Seite auf das Flachbett oder in den Dokumenteneinzug.', anotherStackLead: 'Lege den nächsten Stapel in den Dokumenteneinzug.',
    addPage: 'Ja, weitere Seite scannen', addStack: 'Ja, weiteren Stapel scannen', finishPages: 'Nein, PDF erstellen',
    page: 'Seite', rotate: 'Drehen', up: 'Nach vorne', down: 'Nach hinten', remove: 'Entfernen', cancel: 'Scan abbrechen',
    back: 'Zurück', saveTitle: 'Dokument speichern', saveLead: 'Dateiname, Ziel und Dokumentoptimierung festlegen.',
    filename: 'Dateiname', filenameHint: 'Alle Sitzungen werden als PDF gespeichert.', save: 'Speichern', saving: 'Wird verarbeitet …',
    optimize: 'Kontrast und Seitenränder optimieren', blanks: 'Leere Seiten entfernen', ocr: 'Durchsuchbaren Text per OCR erzeugen (inkl. Begradigung)', pdfa: 'Als PDF/A-2 archivieren', language: 'OCR-Sprachen',
    required: 'Bitte einen Dateinamen eingeben.', saved: 'Scan wurde verarbeitet und zur Zustellung eingeplant.', noSetup: 'Richte zuerst mindestens einen Scanner und ein Ziel ein.',
    manage: 'Jetzt einrichten', empty: 'Noch keine Seite erfasst.', captured: '{n} Seiten erfasst', cancelled: 'Scan-Sitzung wurde verworfen.'
  } : {
    title: 'What would you like to scan?', lead: 'Choose the paper source, capture mode and quality.',
    flatbed: 'Flatbed', flatbedHint: 'Photos, receipts and single pages', adf: 'Document feeder', adfHint: 'Individual pages or complete stacks',
    mode: 'ADF mode', interactive: 'Ask after every page', interactiveHint: 'Feeds exactly one page per scan.',
    automatic: 'Scan complete stack', automaticHint: 'Captures all loaded pages in one pass.',
    quality: 'Content', document: 'Document', color: 'Color', photo: 'Photo', advanced: 'More settings',
    scanner: 'Scanner', target: 'Target', profile: 'Profile', preview: 'Preview', start: 'Start scan', scanning: 'Scanner is working …',
    resumeTitle: 'Resume unfinished scan?', resumeLead: '{n} pages are safely stored on the server.', resume: 'Resume', discard: 'Discard',
    captureTitle: 'Review pages', captureLead: 'Rotate, reorder or remove pages before saving.',
    anotherQuestion: 'Would you like to scan another page?', anotherStack: 'Would you like to scan another stack?',
    anotherLead: 'Place the next page on the flatbed or in the document feeder.', anotherStackLead: 'Load the next stack into the document feeder.',
    addPage: 'Yes, scan another page', addStack: 'Yes, scan another stack', finishPages: 'No, create PDF',
    page: 'Page', rotate: 'Rotate', up: 'Move forward', down: 'Move back', remove: 'Remove', cancel: 'Cancel scan',
    back: 'Back', saveTitle: 'Save document', saveLead: 'Choose the filename, destination and document processing.',
    filename: 'Filename', filenameHint: 'All sessions are saved as PDF.', save: 'Save', saving: 'Processing …',
    optimize: 'Optimize contrast and page margins', blanks: 'Remove blank pages', ocr: 'Create searchable text with OCR (including deskew)', pdfa: 'Archive as PDF/A-2', language: 'OCR languages',
    required: 'Enter a filename.', saved: 'Scan was processed and queued for delivery.', noSetup: 'Set up at least one scanner and one target first.',
    manage: 'Set up now', empty: 'No page captured yet.', captured: '{n} pages captured', cancelled: 'Scan session was discarded.'
  };

  $: devices = data.devices || [];
  $: targets = (data.targets || []).filter((item) => item.enabled !== false);
  $: profiles = data.profiles || [];
  $: if (!deviceId && devices.length) deviceId = (devices.find((item) => item.is_favorite) || devices[0]).id;
  $: if (!targetId && targets.length) targetId = (targets.find((item) => item.is_favorite) || targets[0]).id;
  $: effectiveCaptureMode = captureModeFor(source, captureMode);

  function profilesFor(value) {
    return profiles.filter((profile) => {
      const haystack = `${profile.id} ${profile.name} ${profile.description}`.toLowerCase();
      if (value === 'photo') return /photo|foto|jpeg|jpg/.test(haystack);
      if (value === 'color') return /color|colour|farbe/.test(haystack) && !/photo|foto/.test(haystack);
      return !/photo|foto/.test(haystack);
    });
  }

  $: matchingProfiles = profilesFor(category);
  $: if ((!profileId || !profiles.some((profile) => profile.id === profileId)) && profiles.length) profileId = (matchingProfiles[0] || profiles[0]).id;

  function chooseCategory(value) {
    category = value;
    profileId = (profilesFor(value)[0] || profiles[0])?.id || '';
  }

  function revokePreviews() {
    Object.values(previewUrls).forEach((url) => URL.revokeObjectURL(url));
    previewUrls = {};
  }

  async function applySession(nextSession) {
    const urls = {};
    await Promise.all(nextSession.pages.map(async (page) => {
      const blob = await api.scanSessionPageImage(nextSession.id, page.id);
      urls[page.id] = URL.createObjectURL(blob);
    }));
    revokePreviews();
    previewUrls = urls;
    session = nextSession;
    pages = nextSession.pages.map((page) => ({ ...page, image: urls[page.id] }));
  }

  async function loadResumableSessions() {
    try {
      resumableSessions = await api.listScanSessions();
    } catch (error) {
      if (error.message !== 'Unauthorized') onNotify(error.message, 'error');
    }
  }

  async function resumeSession(candidate) {
    busy = true;
    try {
      deviceId = candidate.device_id;
      profileId = candidate.profile_id;
      targetId = candidate.target_id || targetId;
      source = candidate.source;
      captureMode = candidate.capture_mode;
      await applySession(candidate);
      resumableSessions = resumableSessions.filter((item) => item.id !== candidate.id);
      askForAnotherPage = true;
      step = 2;
    } catch (error) { onNotify(error.message, 'error'); }
    finally { busy = false; }
  }

  async function discardSession(candidate = session) {
    if (!candidate) return;
    busy = true;
    cancelling = true;
    try {
      await api.cancelScanSession(candidate.id);
      if (session?.id === candidate.id) {
        revokePreviews();
        session = null;
        pages = [];
        step = 1;
      }
      resumableSessions = resumableSessions.filter((item) => item.id !== candidate.id);
      onNotify(copy.cancelled, 'success');
    } catch (error) { onNotify(error.message, 'error'); }
    finally { cancelling = false; busy = false; }
  }

  async function capture() {
    if (!deviceId || !profileId) return;
    busy = true;
    askForAnotherPage = false;
    preview = '';
    try {
      let current = session;
      if (!current) {
        current = await api.createScanSession({ device_id: deviceId, profile_id: profileId, target_id: targetId || null, source, capture_mode: effectiveCaptureMode });
        session = current;
      }
      current = await api.captureScanSession(current.id);
      await applySession(current);
      step = 2;
      askForAnotherPage = true;
    } catch (error) {
      if (!cancelling) onNotify(error.message, 'error');
      askForAnotherPage = pages.length > 0;
    } finally { busy = false; }
  }

  async function scanPreview() {
    busy = true;
    try {
      const result = await api.scanPreview({ device_id: deviceId, profile_id: profileId });
      preview = result.image;
    } catch (error) { onNotify(error.message, 'error'); }
    finally { busy = false; }
  }

  async function move(index, delta) {
    if (!session) return;
    busy = true;
    try { await applySession(await api.reorderScanSessionPages(session.id, movedPageIds(pages, index, delta))); }
    catch (error) { onNotify(error.message, 'error'); }
    finally { busy = false; }
  }

  async function remove(index) {
    if (!session) return;
    busy = true;
    try { await applySession(await api.removeScanSessionPage(session.id, pages[index].id)); }
    catch (error) { onNotify(error.message, 'error'); }
    finally { busy = false; }
  }

  async function rotate(index) {
    if (!session) return;
    busy = true;
    try { await applySession(await api.rotateScanSessionPage(session.id, pages[index].id)); }
    catch (error) { onNotify(error.message, 'error'); }
    finally { busy = false; }
  }

  function proceed() { askForAnotherPage = false; step = 3; }

  async function saveDocument() {
    if (!filename.trim() || !session) { onNotify(copy.required, 'error'); return; }
    busy = true;
    try {
      await api.finalizeScanSession(session.id, { target_id: targetId, filename_prefix: filename.trim().replace(/\.pdf$/i, ''), optimize, remove_blank_pages: removeBlankPages, ocr, pdfa, ocr_language: ocrLanguage });
      onNotify(copy.saved, 'success');
      revokePreviews();
      session = null; pages = []; filename = ''; askForAnotherPage = false; step = 1;
      onNavigate('history');
    } catch (error) { onNotify(error.message, 'error'); }
    finally { busy = false; }
  }

  onMount(loadResumableSessions);
  onDestroy(revokePreviews);
</script>

<section class="scan-flow">
  <ol class="flow-steps" aria-label="Progress">{#each [1, 2, 3] as number}<li class:active={step === number} class:done={step > number}><span>{step > number ? '✓' : number}</span></li>{/each}</ol>
  {#if step === 1}
    <div class="flow-heading"><span class="eyebrow">1 / 3</span><h2>{copy.title}</h2><p>{copy.lead}</p></div>
    {#if resumableSessions.length}<div class="decision-card resume-card"><Icon name="page" size={32} /><h3>{copy.resumeTitle}</h3><p>{copy.resumeLead.replace('{n}', resumableSessions[0].pages.length)}</p><div class="flow-actions"><button class="btn danger" disabled={busy} on:click={() => discardSession(resumableSessions[0])}>{copy.discard}</button><button class="btn primary" disabled={busy} on:click={() => resumeSession(resumableSessions[0])}>{copy.resume}</button></div></div>{/if}
    {#if !devices.length || !targets.length}
      <div class="empty-state"><Icon name="alert" size={28} /><strong>{copy.noSetup}</strong><button class="btn primary" on:click={() => onNavigate('manage')}>{copy.manage}</button></div>
    {:else}
      <div class="source-grid"><button class="source-card" class:selected={source === 'Flatbed'} on:click={() => source = 'Flatbed'}><span class="source-visual"><Icon name="scan" size={30} /></span><strong>{copy.flatbed}</strong><small>{copy.flatbedHint}</small></button><button class="source-card" class:selected={source === 'ADF'} on:click={() => source = 'ADF'}><span class="source-visual"><Icon name="page" size={30} /></span><strong>{copy.adf}</strong><small>{copy.adfHint}</small></button></div>
      <div class="flow-panel">
        {#if source === 'ADF'}<div class="field-label">{copy.mode}</div><div class="capture-mode-grid"><button class:active={captureMode === 'interactive'} on:click={() => captureMode = 'interactive'}><strong>{copy.interactive}</strong><small>{copy.interactiveHint}</small></button><button class:active={captureMode === 'automatic'} on:click={() => captureMode = 'automatic'}><strong>{copy.automatic}</strong><small>{copy.automaticHint}</small></button></div>{/if}
        <div class="field-label top-gap">{copy.quality}</div><div class="choice-pills">{#each [['document', copy.document], ['color', copy.color], ['photo', copy.photo]] as choice}<button class:active={category === choice[0]} on:click={() => chooseCategory(choice[0])}>{choice[1]}</button>{/each}</div>
        <button class="disclosure" on:click={() => advanced = !advanced}>{copy.advanced}<span>{advanced ? '−' : '+'}</span></button>
        {#if advanced}<div class="form-grid"><label>{copy.scanner}<select bind:value={deviceId}>{#each devices as item}<option value={item.id}>{item.name}</option>{/each}</select></label><label>{copy.target}<select bind:value={targetId}>{#each targets as item}<option value={item.id}>{item.name}</option>{/each}</select></label><label>{copy.profile}<select bind:value={profileId}>{#each profiles as item}<option value={item.id}>{item.name}</option>{/each}</select></label></div>{/if}
      </div>
      {#if preview}<div class="preview-frame"><img src={preview} alt={copy.preview} /></div>{/if}
      <div class="flow-actions">{#if session && busy}<button class="btn danger" on:click={() => discardSession()}>{copy.cancel}</button>{/if}{#if source === 'Flatbed'}<button class="btn secondary" disabled={busy} on:click={scanPreview}>{copy.preview}</button>{/if}<button class="btn primary large" disabled={busy} on:click={capture}><Icon name="scan" />{busy ? copy.scanning : copy.start}</button></div>
    {/if}
  {:else if step === 2}
    <div class="flow-heading"><span class="eyebrow">2 / 3</span><h2>{copy.captureTitle}</h2><p>{copy.captureLead}</p></div>
    {#if askForAnotherPage}<div class="decision-card"><Icon name="page" size={32} /><h3>{effectiveCaptureMode === 'automatic' ? copy.anotherStack : copy.anotherQuestion}</h3><p>{effectiveCaptureMode === 'automatic' ? copy.anotherStackLead : copy.anotherLead}</p><div class="flow-actions"><button class="btn secondary" disabled={busy || !pages.length} on:click={proceed}>{copy.finishPages}</button><button class="btn primary" disabled={busy} on:click={capture}>{busy ? copy.scanning : (effectiveCaptureMode === 'automatic' ? copy.addStack : copy.addPage)}</button></div></div>{/if}
    <div class="page-count">{copy.captured.replace('{n}', pages.length)}</div>
    {#if pages.length}<div class="page-grid">{#each pages as page, index (page.id)}<article class="page-card"><div class="page-image"><img src={page.image} alt={`${copy.page} ${index + 1}`} /><span>{index + 1}</span></div><div class="page-tools"><button title={copy.rotate} disabled={busy} on:click={() => rotate(index)}>↻</button><button title={copy.up} disabled={busy || index === 0} on:click={() => move(index, -1)}>←</button><button title={copy.down} disabled={busy || index === pages.length - 1} on:click={() => move(index, 1)}>→</button><button title={copy.remove} disabled={busy} on:click={() => remove(index)}><Icon name="trash" size={16} /></button></div></article>{/each}</div>{:else}<div class="empty-state">{copy.empty}</div>{/if}
    <div class="flow-actions between"><button class="btn danger" on:click={() => discardSession()}>{copy.cancel}</button></div>
  {:else}
    <div class="flow-heading"><span class="eyebrow">3 / 3</span><h2>{copy.saveTitle}</h2><p>{copy.saveLead}</p></div>
    <div class="save-card"><label>{copy.filename}<div class="filename-field"><input bind:value={filename} placeholder={$lang === 'de' ? 'z. B. Rechnung Stadtwerke' : 'e.g. Utility invoice'} /><span>.pdf</span></div><small>{copy.filenameHint}</small></label><label>{copy.target}<select bind:value={targetId}>{#each targets as item}<option value={item.id}>{item.name}</option>{/each}</select></label><div class="processing-options"><label class="checkbox-line"><input type="checkbox" bind:checked={optimize} />{copy.optimize}</label><label class="checkbox-line"><input type="checkbox" bind:checked={removeBlankPages} />{copy.blanks}</label><label class="checkbox-line"><input type="checkbox" bind:checked={ocr} />{copy.ocr}</label><label class="checkbox-line"><input type="checkbox" bind:checked={pdfa} on:change={() => { if (pdfa) ocr = true; }} />{copy.pdfa}</label>{#if ocr}<label class="top-gap">{copy.language}<select bind:value={ocrLanguage}><option value="deu+eng">Deutsch + English</option><option value="deu">Deutsch</option><option value="eng">English</option></select></label>{/if}</div><div class="summary-row"><span>{pages.length} × {copy.page}</span><span>{source} · PDF{pdfa ? '/A-2' : ''}</span></div></div>
    <div class="flow-actions between"><button class="btn secondary" disabled={busy} on:click={() => { step = 2; askForAnotherPage = true; }}>{copy.back}</button><button class="btn primary large" disabled={busy || !filename.trim()} on:click={saveDocument}><Icon name="upload" />{busy ? copy.saving : copy.save}</button></div>
  {/if}
</section>
