<script>
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { lang } from '../lib/i18n';

  export let data;
  export let onNotify = () => {};
  export let onNavigate = () => {};

  let step = 1;
  let source = 'Flatbed';
  let category = 'document';
  let deviceId = '';
  let targetId = '';
  let profileId = '';
  let pages = [];
  let preview = '';
  let busy = false;
  let filename = '';
  let outputFormat = 'pdf';
  let advanced = false;
  let adfState = 'fronts';
  let frontPages = [];

  $: copy = $lang === 'de' ? {
    title: 'Was möchtest du scannen?', lead: 'Wähle die Papierquelle – Scanner, Ziel und Qualität sind bereits sinnvoll vorbelegt.',
    flatbed: 'Flachbett', flatbedHint: 'Fotos, Belege und einzelne Seiten', adf: 'Dokumenteneinzug', adfHint: 'Mehrere Seiten als Stapel',
    quality: 'Inhalt', document: 'Dokument', color: 'Farbe', photo: 'Foto', advanced: 'Weitere Einstellungen',
    scanner: 'Scanner', target: 'Ziel', profile: 'Profil', preview: 'Vorschau', start: 'Scan starten', scanning: 'Scanner arbeitet …',
    captureTitle: 'Seiten prüfen', captureLead: 'Drehe, sortiere oder entferne Seiten, bevor du sie speicherst.',
    addPage: 'Weitere Seite', backsQuestion: 'Haben die Blätter Rückseiten?', backsLead: 'Du kannst sie jetzt als zweiten Stapel erfassen.',
    noBacks: 'Nein, weiter', addBacks: 'Rückseiten hinzufügen', flipTitle: 'Stapel wenden und neu einlegen',
    flipLead: 'Lege den Stapel so in den Einzug, dass die Rückseiten in umgekehrter Reihenfolge gescannt werden. Scan2Target sortiert sie automatisch ein.',
    scanBacks: 'Rückseiten scannen', page: 'Seite', rotate: 'Drehen', up: 'Nach vorne', down: 'Nach hinten', remove: 'Entfernen',
    continue: 'Weiter', back: 'Zurück', saveTitle: 'Dokument speichern', saveLead: 'Vergib einen eindeutigen Namen und prüfe das Ziel.',
    filename: 'Dateiname', filenameHint: 'Die Dateiendung wird automatisch ergänzt.', format: 'Format', save: 'Speichern', saving: 'Wird gespeichert …',
    required: 'Bitte einen Dateinamen eingeben.', saved: 'Scan wurde gespeichert und zugestellt.', noSetup: 'Richte zuerst mindestens einen Scanner und ein Ziel ein.',
    manage: 'Jetzt einrichten', empty: 'Noch keine Seite erfasst.', captured: '{n} Seiten erfasst', mismatch: 'Die Anzahl der Vorder- und Rückseiten ist unterschiedlich. Bitte prüfe die Reihenfolge.'
  } : {
    title: 'What would you like to scan?', lead: 'Choose the paper source – scanner, target and quality are already preselected.',
    flatbed: 'Flatbed', flatbedHint: 'Photos, receipts and single pages', adf: 'Document feeder', adfHint: 'Multiple pages as a stack',
    quality: 'Content', document: 'Document', color: 'Color', photo: 'Photo', advanced: 'More settings',
    scanner: 'Scanner', target: 'Target', profile: 'Profile', preview: 'Preview', start: 'Start scan', scanning: 'Scanner is working …',
    captureTitle: 'Review pages', captureLead: 'Rotate, reorder or remove pages before saving.',
    addPage: 'Add another page', backsQuestion: 'Do the sheets have backsides?', backsLead: 'You can capture them now as a second stack.',
    noBacks: 'No, continue', addBacks: 'Add backsides', flipTitle: 'Flip and reinsert the stack',
    flipLead: 'Insert the stack so the backsides scan in reverse order. Scan2Target will interleave them automatically.',
    scanBacks: 'Scan backsides', page: 'Page', rotate: 'Rotate', up: 'Move forward', down: 'Move back', remove: 'Remove',
    continue: 'Continue', back: 'Back', saveTitle: 'Save document', saveLead: 'Choose a clear filename and confirm the destination.',
    filename: 'Filename', filenameHint: 'The extension is added automatically.', format: 'Format', save: 'Save', saving: 'Saving …',
    required: 'Enter a filename.', saved: 'Scan was saved and delivered.', noSetup: 'Set up at least one scanner and one target first.',
    manage: 'Set up now', empty: 'No page captured yet.', captured: '{n} pages captured', mismatch: 'Front and back page counts differ. Please review the order.'
  };

  $: devices = data.devices || [];
  $: targets = (data.targets || []).filter((item) => item.enabled !== false);
  $: profiles = data.profiles || [];
  $: if (!deviceId && devices.length) deviceId = (devices.find((item) => item.is_favorite) || devices[0]).id;
  $: if (!targetId && targets.length) targetId = (targets.find((item) => item.is_favorite) || targets[0]).id;
  function profilesFor(value) {
    return profiles.filter((profile) => {
    const haystack = `${profile.id} ${profile.name} ${profile.description}`.toLowerCase();
    if (value === 'photo') return /photo|foto|jpeg|jpg/.test(haystack);
    if (value === 'color') return /color|colour|farbe/.test(haystack) && !/photo|foto/.test(haystack);
    return !/photo|foto/.test(haystack);
    });
  }
  $: matchingProfiles = profilesFor(category);
  $: if ((!profileId || !profiles.some((p) => p.id === profileId)) && profiles.length) profileId = (matchingProfiles[0] || profiles[0]).id;

  function chooseCategory(value) {
    category = value;
    profileId = (profilesFor(value)[0] || profiles[0])?.id || '';
  }

  async function capture(batch = source === 'ADF') {
    if (!deviceId || !profileId) return;
    busy = true;
    preview = '';
    try {
      const result = await api.capturePages({ device_id: deviceId, profile_id: profileId, source, batch });
      if (source === 'ADF' && adfState === 'backs') {
        const backs = [...result.pages].reverse();
        const interleaved = [];
        const count = Math.max(frontPages.length, backs.length);
        for (let index = 0; index < count; index += 1) {
          if (frontPages[index]) interleaved.push(frontPages[index]);
          if (backs[index]) interleaved.push(backs[index]);
        }
        pages = interleaved;
        adfState = 'done';
        if (frontPages.length !== backs.length) onNotify(copy.mismatch, 'warning');
      } else if (source === 'ADF') {
        pages = result.pages;
        frontPages = [...result.pages];
        adfState = 'question';
      } else {
        pages = [...pages, ...result.pages];
      }
      step = 2;
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      busy = false;
    }
  }

  async function scanPreview() {
    busy = true;
    try {
      const result = await api.scanPreview({ device_id: deviceId, profile_id: profileId });
      preview = result.image;
    } catch (error) { onNotify(error.message, 'error'); }
    finally { busy = false; }
  }

  function move(index, delta) {
    const next = index + delta;
    if (next < 0 || next >= pages.length) return;
    const reordered = [...pages];
    [reordered[index], reordered[next]] = [reordered[next], reordered[index]];
    pages = reordered;
  }

  function remove(index) { pages = pages.filter((_, i) => i !== index); }

  async function rotate(index) {
    const image = new Image();
    image.src = pages[index];
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = image.height;
    canvas.height = image.width;
    const context = canvas.getContext('2d');
    context.translate(canvas.width, 0);
    context.rotate(Math.PI / 2);
    context.drawImage(image, 0, 0);
    const updated = [...pages];
    updated[index] = canvas.toDataURL('image/jpeg', 0.92);
    pages = updated;
  }

  function openBacks() { adfState = 'backs'; }
  function proceed() { step = 3; outputFormat = pages.length > 1 ? 'pdf' : (category === 'photo' ? 'jpeg' : 'pdf'); }

  async function saveDocument() {
    if (!filename.trim()) { onNotify(copy.required, 'error'); return; }
    busy = true;
    try {
      await api.startBatchScan({
        device_id: deviceId, profile_id: profileId, target_id: targetId,
        filename_prefix: filename.trim().replace(/\.(pdf|jpe?g)$/i, ''),
        page_urls: pages, output_format: pages.length > 1 ? 'pdf' : outputFormat
      });
      onNotify(copy.saved, 'success');
      pages = []; frontPages = []; filename = ''; adfState = 'fronts'; step = 1;
      onNavigate('history');
    } catch (error) { onNotify(error.message, 'error'); }
    finally { busy = false; }
  }
</script>

<section class="scan-flow">
  <ol class="flow-steps" aria-label="Progress">
    {#each [1, 2, 3] as number}
      <li class:active={step === number} class:done={step > number}><span>{step > number ? '✓' : number}</span></li>
    {/each}
  </ol>

  {#if step === 1}
    <div class="flow-heading"><span class="eyebrow">1 / 3</span><h2>{copy.title}</h2><p>{copy.lead}</p></div>
    {#if !devices.length || !targets.length}
      <div class="empty-state"><Icon name="alert" size={28} /><strong>{copy.noSetup}</strong><button class="btn primary" on:click={() => onNavigate('manage')}>{copy.manage}</button></div>
    {:else}
      <div class="source-grid">
        <button class="source-card" class:selected={source === 'Flatbed'} on:click={() => source = 'Flatbed'}>
          <span class="source-visual"><Icon name="scan" size={30} /></span><strong>{copy.flatbed}</strong><small>{copy.flatbedHint}</small>
        </button>
        <button class="source-card" class:selected={source === 'ADF'} on:click={() => source = 'ADF'}>
          <span class="source-visual"><Icon name="page" size={30} /></span><strong>{copy.adf}</strong><small>{copy.adfHint}</small>
        </button>
      </div>
      <div class="flow-panel">
        <div class="field-label">{copy.quality}</div>
        <div class="choice-pills">
          {#each [['document', copy.document], ['color', copy.color], ['photo', copy.photo]] as choice}
            <button class:active={category === choice[0]} on:click={() => chooseCategory(choice[0])}>{choice[1]}</button>
          {/each}
        </div>
        <button class="disclosure" on:click={() => advanced = !advanced}>{copy.advanced}<span>{advanced ? '−' : '+'}</span></button>
        {#if advanced}
          <div class="form-grid">
            <label>{copy.scanner}<select bind:value={deviceId}>{#each devices as item}<option value={item.id}>{item.name}</option>{/each}</select></label>
            <label>{copy.target}<select bind:value={targetId}>{#each targets as item}<option value={item.id}>{item.name}</option>{/each}</select></label>
            <label>{copy.profile}<select bind:value={profileId}>{#each profiles as item}<option value={item.id}>{item.name}</option>{/each}</select></label>
          </div>
        {/if}
      </div>
      {#if preview}<div class="preview-frame"><img src={preview} alt={copy.preview} /></div>{/if}
      <div class="flow-actions">
        {#if source === 'Flatbed'}<button class="btn secondary" disabled={busy} on:click={scanPreview}>{copy.preview}</button>{/if}
        <button class="btn primary large" disabled={busy} on:click={() => capture(source === 'ADF')}><Icon name="scan" />{busy ? copy.scanning : copy.start}</button>
      </div>
    {/if}
  {:else if step === 2}
    <div class="flow-heading"><span class="eyebrow">2 / 3</span><h2>{copy.captureTitle}</h2><p>{copy.captureLead}</p></div>
    {#if adfState === 'question'}
      <div class="decision-card"><Icon name="page" size={32} /><h3>{copy.backsQuestion}</h3><p>{copy.backsLead}</p><div class="flow-actions"><button class="btn secondary" on:click={() => adfState = 'done'}>{copy.noBacks}</button><button class="btn primary" on:click={openBacks}>{copy.addBacks}</button></div></div>
    {:else if adfState === 'backs'}
      <div class="decision-card"><div class="flip-icon">↻</div><h3>{copy.flipTitle}</h3><p>{copy.flipLead}</p><button class="btn primary large" disabled={busy} on:click={() => capture(true)}>{busy ? copy.scanning : copy.scanBacks}</button></div>
    {/if}
    <div class="page-count">{copy.captured.replace('{n}', pages.length)}</div>
    {#if pages.length}
      <div class="page-grid">
        {#each pages as page, index (index)}
          <article class="page-card"><div class="page-image"><img src={page} alt={`${copy.page} ${index + 1}`} /><span>{index + 1}</span></div><div class="page-tools"><button title={copy.rotate} on:click={() => rotate(index)}>↻</button><button title={copy.up} disabled={index === 0} on:click={() => move(index, -1)}>←</button><button title={copy.down} disabled={index === pages.length - 1} on:click={() => move(index, 1)}>→</button><button title={copy.remove} on:click={() => remove(index)}><Icon name="trash" size={16} /></button></div></article>
        {/each}
      </div>
    {:else}<div class="empty-state">{copy.empty}</div>{/if}
    <div class="flow-actions between"><button class="btn secondary" on:click={() => step = 1}>{copy.back}</button><div>{#if source === 'Flatbed'}<button class="btn secondary" disabled={busy} on:click={() => capture(false)}>{copy.addPage}</button>{/if}<button class="btn primary" disabled={!pages.length || adfState === 'backs'} on:click={proceed}>{copy.continue}</button></div></div>
  {:else}
    <div class="flow-heading"><span class="eyebrow">3 / 3</span><h2>{copy.saveTitle}</h2><p>{copy.saveLead}</p></div>
    <div class="save-card">
      <label>{copy.filename}<div class="filename-field"><input bind:value={filename} placeholder={$lang === 'de' ? 'z. B. Rechnung Stadtwerke' : 'e.g. Utility invoice'} /><span>.{pages.length > 1 ? 'pdf' : (outputFormat === 'jpeg' ? 'jpg' : 'pdf')}</span></div><small>{copy.filenameHint}</small></label>
      {#if pages.length === 1}<label>{copy.format}<select bind:value={outputFormat}><option value="pdf">PDF</option><option value="jpeg">JPEG</option></select></label>{/if}
      <label>{copy.target}<select bind:value={targetId}>{#each targets as item}<option value={item.id}>{item.name}</option>{/each}</select></label>
      <div class="summary-row"><span>{pages.length} × {copy.page}</span><span>{source}</span></div>
    </div>
    <div class="flow-actions between"><button class="btn secondary" on:click={() => step = 2}>{copy.back}</button><button class="btn primary large" disabled={busy || !filename.trim()} on:click={saveDocument}><Icon name="upload" />{busy ? copy.saving : copy.save}</button></div>
  {/if}
</section>
