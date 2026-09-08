<script>
  import Icon from '../ui/Icon.svelte';
  import { lang } from '../../lib/i18n';

  export let version = '';
  export let wsConnected = false;

  const repo = 'https://github.com/fgrfn/Scan2Target';

  $: labels = $lang === 'de'
    ? { project: 'Scan-Server für Netzwerkscanner', source: 'Quellcode', docs: 'Dokumentation', live: 'Live verbunden', polling: 'Polling', version: 'Version' }
    : { project: 'Scan server for network scanners', source: 'Source code', docs: 'Documentation', live: 'Live connected', polling: 'Polling', version: 'Version' };
</script>

<footer class="app-footer">
  <div class="row gap wrap center">
    <span class="app-version">Scan2Target {version ? `v${version}` : ''}</span>
    <span>· {labels.project}</span>
  </div>
  <nav>
    <a href={repo} target="_blank" rel="noopener noreferrer">
      <Icon name="github" size={15} /> {labels.source}
    </a>
    <a href={`${repo}#readme`} target="_blank" rel="noopener noreferrer">
      <Icon name="book" size={15} /> {labels.docs}
    </a>
    <span>{wsConnected ? labels.live : labels.polling}</span>
  </nav>
</footer>
