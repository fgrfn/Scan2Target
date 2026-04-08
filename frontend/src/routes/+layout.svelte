<script lang="ts">
  import { page } from '$app/stores';
  import { onMount, type Snippet } from 'svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { login as apiLogin, getMe, getAuthConfig } from '$lib/api/auth';
  import { apiFetch } from '$lib/api/client';
  import Toast from '$lib/components/ui/Toast.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import {
    ScanLine, Printer, Crosshair, Clock, BarChart3,
    Settings2, LogOut, User, Wifi, WifiOff, Eye, EyeOff, Loader2
  } from 'lucide-svelte';
  import '../app.css';

  interface Props { children: Snippet; }
  let { children }: Props = $props();

  let loginUsername = $state('');
  let loginPassword = $state('');
  let loginLoading  = $state(false);
  let loginError    = $state('');
  let showPass      = $state(false);
  let bootstrapped  = $state(false);
  let requireAuth   = $state(true);
  let appVersion    = $state('');

  onMount(async () => {
    try {
      try { const cfg = await getAuthConfig(); requireAuth = cfg.require_auth; } catch { /* keep default */ }
      try { const v = await apiFetch<{ version: string }>('/version', { method: 'GET' }); appVersion = v.version; } catch { /* ignore */ }
      if (auth.token) {
        try { const u = await getMe(); auth.setUser(u); wsStore.start(); }
        catch { auth.logout(); }
      } else if (!requireAuth) {
        wsStore.start();
      }
    } finally {
      bootstrapped = true;
    }
  });

  async function handleLogin(e: SubmitEvent) {
    e.preventDefault();
    loginLoading = true; loginError = '';
    try {
      const resp = await apiLogin(loginUsername, loginPassword);
      auth.login(resp.user, resp.access_token);
      wsStore.start();
      loginUsername = ''; loginPassword = '';
    } catch (err: unknown) {
      loginError = err instanceof Error ? err.message : 'Login failed';
    } finally { loginLoading = false; }
  }

  function handleLogout() {
    wsStore.disconnect(); auth.logout();
    showToast('Signed out', 'info');
  }

  const navLinks = [
    { href: '/',         label: 'Scan',     Icon: ScanLine   },
    { href: '/devices',  label: 'Devices',  Icon: Printer    },
    { href: '/targets',  label: 'Targets',  Icon: Crosshair  },
    { href: '/history',  label: 'History',  Icon: Clock      },
    { href: '/stats',    label: 'Stats',    Icon: BarChart3  },
    { href: '/settings', label: 'Settings', Icon: Settings2  },
  ];

  function isActive(href: string) {
    const p = $page.url.pathname;
    return href === '/' ? p === '/' : p.startsWith(href);
  }
</script>

{#if !bootstrapped}
  <div style="display:flex;align-items:center;justify-content:center;min-height:100dvh;">
    <Spinner size="lg" />
  </div>

{:else if !auth.isAuthenticated && requireAuth}
  <!-- ── Login ───────────────────────────────────────── -->
  <div style="min-height:100dvh;display:flex;align-items:center;justify-content:center;padding:24px;background:var(--c-bg);">
    <div style="width:100%;max-width:360px;">

      <!-- Wordmark -->
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:32px;">
        <div class="sidebar-brand-icon"><ScanLine size={14} color="white" /></div>
        <span style="font-size:1.125rem;font-weight:700;color:var(--c-text);letter-spacing:-0.01em;">
          Scan<span style="color:var(--c-accent);">2</span>Target
        </span>
      </div>

      <div class="card" style="padding:24px;">
        <h1 style="font-size:1rem;font-weight:600;color:var(--c-text);margin-bottom:4px;">Sign in</h1>
        <p style="font-size:0.8125rem;color:var(--c-text-2);margin-bottom:20px;">Self-hosted scanner delivery hub</p>

        {#if loginError}
          <div style="margin-bottom:16px;padding:10px 12px;border-radius:6px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);color:#f87171;font-size:0.8125rem;display:flex;align-items:center;gap:8px;" role="alert">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            {loginError}
          </div>
        {/if}

        <form onsubmit={handleLogin} style="display:flex;flex-direction:column;gap:14px;">
          <div class="form-group">
            <label class="form-label" for="l-user">Username</label>
            <input id="l-user" class="form-control" type="text"
                   bind:value={loginUsername} required autocomplete="username" placeholder="admin" />
          </div>

          <div class="form-group">
            <label class="form-label" for="l-pass">Password</label>
            <div style="position:relative;">
              <input id="l-pass" class="form-control" style="padding-right:36px;"
                     type={showPass ? 'text' : 'password'}
                     bind:value={loginPassword} required autocomplete="current-password" />
              <button type="button" tabindex="-1"
                      style="position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--c-text-3);cursor:pointer;display:flex;"
                      onclick={() => (showPass = !showPass)}>
                {#if showPass}<EyeOff size={15} />{:else}<Eye size={15} />{/if}
              </button>
            </div>
          </div>

          <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;padding:9px;" disabled={loginLoading}>
            {#if loginLoading}<Loader2 size={14} class="spin" />{/if}
            Sign In
          </button>
        </form>
      </div>

      <p style="text-align:center;font-size:0.75rem;color:var(--c-text-3);margin-top:16px;">
        <a href="https://github.com/fgrfn/Scan2Target" target="_blank" rel="noopener"
           style="color:var(--c-text-3);text-decoration:none;">
          Scan2Target on GitHub
        </a>
      </p>
    </div>
  </div>

{:else}
  <!-- ── App shell ──────────────────────────────────── -->
  <div class="shell">

    <!-- Sidebar -->
    <nav class="sidebar" aria-label="Navigation">
      <div class="sidebar-brand">
        <div class="sidebar-brand-icon"><ScanLine size={13} color="white" /></div>
        <span class="sidebar-brand-name">Scan<span>2</span>Target</span>
      </div>

      <div class="sidebar-nav">
        {#each navLinks as { href, label, Icon }}
          <a {href} class="nav-link" class:active={isActive(href)}>
            <Icon size={15} strokeWidth={isActive(href) ? 2.25 : 1.75} />
            {label}
            {#if isActive(href)}
              <span class="nav-dot" style="width:4px;height:4px;border-radius:50%;background:var(--c-accent);margin-left:auto;"></span>
            {/if}
          </a>
        {/each}
      </div>

      <div class="sidebar-footer">
        <!-- WS status -->
        <div style="display:flex;align-items:center;gap:6px;">
          <span class="ws-dot {wsStore.status}"></span>
          <span style="font-size:0.75rem;color:var(--c-text-3);">
            {wsStore.status === 'connected' ? 'Live' : wsStore.status === 'connecting' ? 'Connecting…' : 'Offline'}
          </span>
          {#if appVersion}
            <span style="font-size:0.7rem;margin-left:auto;">
              <a href="https://github.com/fgrfn/Scan2Target" target="_blank" rel="noopener"
                 style="color:var(--c-accent);text-decoration:none;opacity:0.85;" title="View on GitHub">
                v{appVersion}
              </a>
            </span>
          {/if}
        </div>
        {#if auth.user}
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
            <div style="display:flex;align-items:center;gap:8px;min-width:0;">
              <div style="width:24px;height:24px;border-radius:4px;background:var(--c-surface-2);border:1px solid var(--c-border);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                <User size={12} style="color:var(--c-text-2);" />
              </div>
              <div style="min-width:0;">
                <p style="font-size:0.8125rem;font-weight:500;color:var(--c-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{auth.user.username}</p>
                {#if auth.user.is_admin}
                  <p style="font-size:0.625rem;color:var(--c-text-3);">Admin</p>
                {/if}
              </div>
            </div>
            <button class="btn btn-ghost btn-icon btn-sm" onclick={handleLogout} title="Sign out" style="flex-shrink:0;">
              <LogOut size={13} />
            </button>
          </div>
        {/if}
      </div>
    </nav>

    <!-- Mobile header -->
    <header class="mobile-header">
      <div style="display:flex;align-items:center;gap:8px;">
        <div class="sidebar-brand-icon" style="width:22px;height:22px;border-radius:4px;"><ScanLine size={12} color="white" /></div>
        <span style="font-size:0.875rem;font-weight:700;color:var(--c-text);">Scan<span style="color:var(--c-accent);">2</span>Target</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        {#if wsStore.status === 'connected'}
          <Wifi size={15} style="color:var(--c-ok);" />
        {:else}
          <WifiOff size={15} style="color:var(--c-text-3);" />
        {/if}
        <button class="btn btn-ghost btn-icon btn-sm" onclick={handleLogout} title="Sign out">
          <LogOut size={15} />
        </button>
      </div>
    </header>

    <!-- Content -->
    <main class="main-content">
      {@render children()}
    </main>

    <!-- Mobile bottom nav -->
    <nav class="bottom-nav" aria-label="Mobile navigation">
      <div class="bottom-nav-inner">
        {#each navLinks as { href, label, Icon }}
          <a {href} class="bn-link" class:active={isActive(href)}>
            <Icon size={19} strokeWidth={isActive(href) ? 2.25 : 1.75} />
            <span>{label}</span>
          </a>
        {/each}
      </div>
    </nav>

  </div>
{/if}

<Toast />

<style>
  :global(.spin) { animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
