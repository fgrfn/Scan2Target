<script>
  export let name = 'dot';
  export let size = 18;
  export let filled = false;

  // Simple inline stroke icons (feather-style), kept deliberately minimal.
  const icons = {
    dashboard: 'M3 3h8v8H3zM13 3h8v5h-8zM13 12h8v9h-8zM3 15h8v6H3z',
    scan: 'M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M3 12h18',
    history: 'M3 12a9 9 0 1 0 3-6.7M3 4v5h5M12 7v5l3 3',
    settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
    devices: 'M4 6h16a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zM8 19h8M12 15v4',
    targets: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z',
    stats: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
    more: 'M5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z',
    refresh: 'M21 12a9 9 0 1 1-2.6-6.3M21 3v6h-6',
    star: 'M12 2.5l2.9 5.9 6.6 1-4.7 4.6 1.1 6.5-5.9-3.1-5.9 3.1 1.1-6.5L2.5 9.4l6.6-1z',
    trash: 'M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6',
    plus: 'M12 5v14M5 12h14',
    x: 'M6 6l12 12M18 6L6 18',
    check: 'M4 12.5l5 5L20 6.5',
    copy: 'M9 9h11v11H9zM5 15H4V4h11v1',
    page: 'M6 2h8l4 4v16H6zM14 2v4h4M9 13h6M9 17h6',
    edit: 'M17 3l4 4L8 20H4v-4zM14 6l4 4',
    upload: 'M12 16V4M6 10l6-6 6 6M4 20h16',
    play: 'M7 4l13 8-13 8z',
    alert: 'M12 3l10 17H2zM12 10v4M12 17.5v.5',
    logout: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
    bolt: 'M13 2L4 14h6l-1 8 9-12h-6z',
    camera: 'M3 8a2 2 0 0 1 2-2h2l2-2h6l2 2h2a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
    dot: 'M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z'
  };
</script>

<svg
  class="icon"
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill={filled ? 'currentColor' : 'none'}
  stroke="currentColor"
  stroke-width="1.8"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
>
  <path d={icons[name] || icons.dot} />
</svg>

<style>
  .icon {
    flex: 0 0 auto;
    display: block;
  }
</style>
