<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { statusTone, statusKey } from '../lib/status';

  export let data;
  export let onNotify = () => {};
  export let onNavigate = () => {};

  const steps = [
    { key: 'stepScanner', hint: 'stepScannerHint' },
    { key: 'stepProfile', hint: 'stepProfileHint' },
    { key: 'stepTarget', hint: 'stepTargetHint' },
    { key: 'stepFilename', hint: 'stepFilenameHint' },
    { key: 'stepReview', hint: 'stepReviewHint' }
  ];

  let step = 0;
  let starting = false;
  let scanMode = 'direct'; // 'direct' | 'multi'
  let sourceOverride = ''; // '' = use profile default
  let form = { device_id: '', profile_id: '', target_id: '', filename_prefix: '' };

  // Multi-page state
  let pages = []; // dataURLs
  let scanningPage = false;
  let uploadingBatch = false;

  // Preview state
  let previewImage = null;
  let previewing = false;

  $: if (!form.device_id && data.devices.length) {
    form.device_id = data.devices.find((d) => d.is_favorite)?.id || data.devices[0].id;
  }
  $: if (!form.profile_id && data.profiles.length) form.profile_id = data.profiles[0].id;
  $: if (!form.target_id && data.targets.length) {
    form.target_id = data.targets.find((tg) => tg.is_favorite)?.id || data.targets[0].id;
  }
  $: selectedDevice = data.devices.find((d) => d.id === form.device_id);
  $: selectedProfile = data.profiles.find((p) => p.id === form.profile_id);
  $: selectedTarget = data.targets.find((tg) => tg.id === form.target_id);
  $: effectiveSource = sourceOverride || selectedProfile?.source || 'Flatbed';
  $: busy = starting || scanningPage || uploadingBatch;

  function reset() {
    step = 0;
    pages = [];
    previewImage = null;
    form.filename_prefix = '';
    scanMode = 'direct';
    sourceOverride = '';
  }

  async function startDirectScan() {
    starting = true;
    try {
      await api.startScan({
        device_id: form.device_id,
        profile_id: form.profile_id,
        target_id: form.target_id,
        source: sourceOverride || null,
        filename_prefix: form.filename_prefix || null
      });
      onNotify($t('scanStarted'), 'success');
      reset();
      onNavigate('dashboard');
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      starting = false;
    }
  }

  async function scanNextPage() {
    scanningPage = true;
    try {
      const result = await api.scanPage({
        device_id: form.device_id,
        profile_id: form.profile_id,
        source: sourceOverride || null
      });
      pages = [...pages, result.image];
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      scanningPage = false;
    }
  }

  function removePage(index) {
    pages = pages.filter((_, i) => i !== index);
  }

  async function finishBatch() {
    if (!pages.length) return;
    uploadingBatch = true;
    try {
      await api.startBatchScan({
        device_id: form.device_id,
        profile_id: form.profile_id,
        target_id: form.target_id,
        filename_prefix: form.filename_prefix || null,
        page_urls: pages
      });
      onNotify($t('batchUploaded', { n: pages.length }), 'success');
      reset();
      onNavigate('dashboard');
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      uploadingBatch = false;
    }
  }

  async function runPreview() {
    previewing = true;
    previewImage = null;
    try {
      const result = await api.scanPreview({ device_id: form.device_id, profile_id: form.profile_id });
      previewImage = result.image;
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      previewing = false;
    }
  }
</script>

<div class="scan-layout">
  <Card title={$t('scanFlow')} subtitle={$t('scanFlowSub')}>
    <div class="step-rail">
      {#each steps as item, i}
        <button class="step-item" class:active={i === step} class:done={i < step} on:click={() => !busy && i < step && (step = i)}>
          <div class="step-index">{#if i < step}<Icon name="check" size={14} />{:else}{i + 1}{/if}</div>
          <div class="step-label"><strong>{$t(item.key)}</strong><span>{$t(item.hint)}</span></div>
        </button>
      {/each}
    </div>
  </Card>

  <Card title={$t(steps[step].key)} subtitle={$t(steps[step].hint)}>
    {#if step === 0}
      <!-- Scanner -->
      {#if data.devices.length === 0}
        <div class="empty-state">
          <Icon name="devices" size={28} />
          <strong>{$t('noScannersWizard')}</strong>
          <p class="muted small">{$t('noScannersWizardHint')}</p>
          <button class="btn primary" on:click={() => onNavigate('devices')}>{$t('goDevices')}</button>
        </div>
      {:else}
        <div class="choice-grid">
          {#each data.devices as d (d.id)}
            <button class="choice-card" class:selected={form.device_id === d.id} on:click={() => (form.device_id = d.id)}>
              <div class="choice-head-row">
                <div class="choice-icon"><Icon name="devices" /></div>
                {#if d.is_favorite}<span class="fav-star"><Icon name="star" size={14} filled /></span>{/if}
              </div>
              <h4>{d.name}</h4>
              <p>{d.connection_type || $t('unknown')}</p>
              <Badge tone={statusTone(d.status)} text={$t(statusKey(d.status || 'unknown'))} />
            </button>
          {/each}
        </div>
      {/if}
    {:else if step === 1}
      <!-- Profile + source -->
      {#if data.profiles.length === 0}
        <p class="muted">{$t('noProfilesWizard')}</p>
      {:else}
        <div class="choice-grid">
          {#each data.profiles as p (p.id)}
            <button class="choice-card" class:selected={form.profile_id === p.id} on:click={() => { form.profile_id = p.id; sourceOverride = ''; }}>
              <div class="choice-icon"><Icon name={p.batch_scan ? 'copy' : 'page'} /></div>
              <h4>{p.name}</h4>
              <p>{p.dpi} DPI · {(p.format || '').toUpperCase()} · {p.color_mode}</p>
              {#if p.description}<p class="muted small">{p.description}</p>{/if}
            </button>
          {/each}
        </div>

        <div class="top-gap">
          <div class="field-label">{$t('sourceLabel')}</div>
          <p class="muted small">{$t('sourceFromProfile', { source: selectedProfile?.source || 'Flatbed' })}</p>
          <div class="choice-grid two">
            {#each ['Flatbed', 'ADF'] as src}
              <button
                class="choice-card slim"
                class:selected={effectiveSource === src}
                on:click={() => (sourceOverride = src === (selectedProfile?.source || 'Flatbed') ? '' : src)}
              >
                <h4>{src === 'ADF' ? $t('sourceADF') : $t('sourceFlatbed')}</h4>
                <p>{src === 'ADF' ? $t('sourceADFHint') : $t('sourceFlatbedHint')}</p>
              </button>
            {/each}
          </div>
        </div>
      {/if}
    {:else if step === 2}
      <!-- Target -->
      {#if data.targets.length === 0}
        <div class="empty-state">
          <Icon name="targets" size={28} />
          <strong>{$t('noTargetsWizard')}</strong>
          <p class="muted small">{$t('noTargetsWizardHint')}</p>
          <button class="btn primary" on:click={() => onNavigate('targets')}>{$t('goTargets')}</button>
        </div>
      {:else}
        <div class="choice-grid">
          {#each data.targets.filter((tg) => tg.enabled !== false) as tg (tg.id)}
            <button class="choice-card" class:selected={form.target_id === tg.id} on:click={() => (form.target_id = tg.id)}>
              <div class="choice-head-row">
                <div class="choice-icon"><Icon name="targets" /></div>
                {#if tg.is_favorite}<span class="fav-star"><Icon name="star" size={14} filled /></span>{/if}
              </div>
              <h4>{tg.name}</h4>
              <p>{(tg.type || '').toUpperCase()}{#if tg.description} · {tg.description}{/if}</p>
            </button>
          {/each}
        </div>
      {/if}
    {:else if step === 3}
      <!-- Filename -->
      <label>{$t('filenameLabel')}
        <input bind:value={form.filename_prefix} placeholder={$t('filenamePlaceholder')} />
      </label>
      <p class="muted small">{$t('filenameHint')}</p>
    {:else}
      <!-- Review + mode + launch -->
      <div class="review-grid">
        <div class="review-item"><span>{$t('reviewScanner')}</span><strong>{selectedDevice?.name || '—'}</strong></div>
        <div class="review-item"><span>{$t('reviewProfile')}</span><strong>{selectedProfile?.name || '—'}</strong></div>
        <div class="review-item"><span>{$t('reviewSource')}</span><strong>{effectiveSource}</strong></div>
        <div class="review-item"><span>{$t('reviewTarget')}</span><strong>{selectedTarget?.name || '—'}</strong></div>
        <div class="review-item"><span>{$t('reviewFilename')}</span><strong>{form.filename_prefix || $t('autoGenerated')}</strong></div>
      </div>

      <div class="top-gap">
        <div class="field-label">{$t('scanModeTitle')}</div>
        <div class="choice-grid two">
          <button class="choice-card slim" class:selected={scanMode === 'direct'} on:click={() => (scanMode = 'direct')} disabled={busy}>
            <h4>{$t('scanModeDirect')}</h4>
            <p>{$t('scanModeDirectHint')}</p>
          </button>
          <button class="choice-card slim" class:selected={scanMode === 'multi'} on:click={() => (scanMode = 'multi')} disabled={busy}>
            <h4>{$t('scanModeMulti')}</h4>
            <p>{$t('scanModeMultiHint')}</p>
          </button>
        </div>
      </div>

      {#if scanMode === 'multi'}
        <div class="multi-panel top-gap">
          <div class="row gap center spread">
            <div>
              <strong>{$t('multiPageTitle')}</strong>
              <p class="muted small">{$t('multiPageSub')}</p>
            </div>
            <Badge tone={pages.length ? 'success' : 'neutral'} text={$t('pagesScanned', { n: pages.length })} />
          </div>

          {#if pages.length === 0}
            <p class="muted small top-gap">{$t('noPagesYet')}</p>
          {:else}
            <div class="page-strip top-gap">
              {#each pages as page, i (i)}
                <div class="page-thumb-wrap">
                  <img class="page-thumb" src={page} alt={$t('pageLabel', { n: i + 1 })} />
                  <span class="page-num">{i + 1}</span>
                  <button class="page-remove" title={$t('removePage')} disabled={busy} on:click={() => removePage(i)}>
                    <Icon name="x" size={12} />
                  </button>
                </div>
              {/each}
            </div>
          {/if}

          <div class="row gap top-gap wrap">
            <button class="btn primary" disabled={busy || !form.device_id} on:click={scanNextPage}>
              <Icon name="scan" size={16} />
              {scanningPage ? $t('scanningPage') : pages.length ? $t('scanNextPage') : $t('scanFirstPage')}
            </button>
            <button class="btn success" disabled={busy || !pages.length || !form.target_id} on:click={finishBatch}>
              <Icon name="upload" size={16} />
              {uploadingBatch ? $t('uploadingPages') : $t('finishUpload')}
            </button>
            {#if pages.length}
              <button class="btn ghost" disabled={busy} on:click={() => (pages = [])}>{$t('cancelMulti')}</button>
            {/if}
          </div>
        </div>
      {/if}

      {#if previewImage}
        <div class="preview-panel top-gap">
          <div class="row gap center spread">
            <strong>{$t('previewTitle')}</strong>
            <button class="btn ghost small-btn" on:click={() => (previewImage = null)}><Icon name="x" size={14} /></button>
          </div>
          <p class="muted small">{$t('previewHint')}</p>
          <img class="preview-image" src={previewImage} alt={$t('previewTitle')} />
        </div>
      {/if}
    {/if}

    <div class="row gap top-gap wrap">
      <button class="btn ghost" disabled={step === 0 || busy} on:click={() => (step -= 1)}>{$t('back')}</button>
      {#if step < steps.length - 1}
        <button class="btn primary" disabled={busy} on:click={() => (step += 1)}>{$t('continue')}</button>
      {:else}
        {#if scanMode === 'direct'}
          <button
            class="btn primary"
            disabled={busy || !form.device_id || !form.profile_id || !form.target_id}
            on:click={startDirectScan}
          >
            <Icon name="play" size={16} />
            {starting ? $t('starting') : $t('startScanBtn')}
          </button>
        {/if}
        <button class="btn ghost" disabled={busy || !form.device_id} on:click={runPreview}>
          <Icon name="camera" size={16} />
          {previewing ? $t('previewing') : $t('previewBtn')}
        </button>
      {/if}
    </div>
  </Card>
</div>
