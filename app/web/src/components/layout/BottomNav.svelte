<script>
  import Icon from '../ui/Icon.svelte';
  import { lang } from '../../lib/i18n';
  export let current = 'scan';
  export let onNavigate = () => {};
  $: items = $lang === 'de' ? [['scan','scan','Scan'],['history','history','Verlauf'],['manage','devices','Verwalten'],['settings','settings','Einstellungen']] : [['scan','scan','Scan'],['history','history','History'],['manage','devices','Manage'],['settings','settings','Settings']];
</script>
<nav class="bottom-nav" aria-label="Mobile navigation">{#each items as item}<button class:active={current === item[0]} on:click={() => onNavigate(item[0])}><Icon name={item[1]} size={20} /><span>{item[2]}</span></button>{/each}</nav>
