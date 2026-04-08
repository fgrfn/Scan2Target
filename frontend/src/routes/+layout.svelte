<script lang="ts">
  import { page } from '$app/stores';
  import { onMount, type Snippet } from 'svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { login as apiLogin, getMe } from '$lib/api/auth';
  import Toast from '$lib/components/ui/Toast.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import '../app.css';

  // Lucide icons
  import {
    ScanLine, Printer, Crosshair, Clock, BarChart3, Settings2,
    LogOut, Wifi, WifiOff, Loader2, User, Eye, EyeOff
  } from 'lucide-svelte';

  interface Props { children: Snippet; }
  let { children }: Props = $props();

  let loginUsername = $state('');
  let loginPassword = $state('');
  let loginLoading  = $state(false);
  let loginError    = $state('');
  let showPass      = $state(false);
  let bootstrapped  = $state(false);

  onMount(async () => {
    if (auth.token) {
      try {
        const user = await getMe();
        auth.setUser(user);
        wsStore.start();
      } catch { auth.logout(); }
    }
    bootstrapped = true;
  });

  async function handleLogin(e: SubmitEvent) {
    e.preventDefault();
    loginLoading = true;
    loginError = '';
    try {
      const resp = await apiLogin(loginUsername, loginPassword);
      auth.login(resp.user, resp.access_token);
      wsStore.start();
      loginUsername = '';
      loginPassword = '';
    } catch (err: unknown) {
      loginError = err instanceof Error ? err.message : 'Login failed';
    } finally {
      loginLoading = false;
    }
  }

  async function handleLogout() {
    wsStore.disconnect();
    auth.logout();
    showToast('Signed out', 'info');
  }

  const navLinks = [
    { href: '/',         label: 'Scan',     Icon: ScanLine  },
    { href: '/devices',  label: 'Devices',  Icon: Printer   },
    { href: '/targets',  label: 'Targets',  Icon: Crosshair },
    { href: '/history',  label: 'History',  Icon: Clock     },
    { href: '/stats',    label: 'Stats',    Icon: BarChart3 },
    { href: '/settings', label: 'Settings', Icon: Settings2 },
  ];

  function isActive(href: string): boolean {
    const path = $page.url.pathname;
    if (href === '/') return path === '/';
    return path.startsWith(href);
  }

  const wsStatus = $derived(wsStore.status);
</script>

{#if !bootstrapped}
  <!-- Boot loader -->
  <div class="flex items-center justify-center min-h-dvh bg-zinc-950">
    <Spinner size="lg" />
  </div>

{:else if !auth.isAuthenticated}
  <!-- ── Login ─────────────────────────────────────────── -->
  <div class="min-h-dvh bg-zinc-950 flex items-center justify-center p-4"
       style="background: radial-gradient(ellipse at top, rgba(99,102,241,0.08) 0%, transparent 60%), #09090b;">
    <div class="w-full max-w-sm">

      <!-- Logo -->
      <div class="flex flex-col items-center mb-8 gap-2">
        <div class="w-12 h-12 rounded-xl flex items-center justify-center mb-1"
             style="background: linear-gradient(135deg, #6366f1, #8b5cf6); box-shadow: 0 4px 20px rgba(99,102,241,0.35);">
          <ScanLine size={24} color="white" />
        </div>
        <h1 class="text-2xl font-bold text-zinc-50 tracking-tight">Scan<span class="text-indigo-400">2</span>Target</h1>
        <p class="text-sm text-zinc-500">Self-hosted scanner delivery hub</p>
      </div>

      <!-- Card -->
      <div class="card p-6 shadow-2xl shadow-black/40">
        {#if loginError}
          <div class="mb-4 px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-2" role="alert">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            {loginError}
          </div>
        {/if}

        <form onsubmit={handleLogin} class="flex flex-col gap-4">
          <div class="form-group">
            <label class="form-label" for="l-user">Username</label>
            <input id="l-user" class="form-control" type="text"
                   bind:value={loginUsername} required autocomplete="username"
                   placeholder="admin" />
          </div>

          <div class="form-group">
            <label class="form-label" for="l-pass">Password</label>
            <div class="relative">
              <input id="l-pass" class="form-control pr-10"
                     type={showPass ? 'text' : 'password'}
                     bind:value={loginPassword} required
                     autocomplete="current-password" />
              <button type="button"
                      class="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                      onclick={() => (showPass = !showPass)} tabindex="-1">
                {#if showPass}<EyeOff size={16} />{:else}<Eye size={16} />{/if}
              </button>
            </div>
          </div>

          <button type="submit" class="btn btn-primary w-full justify-center mt-1" style="padding:10px;"
                  disabled={loginLoading}>
            {#if loginLoading}
              <Loader2 size={16} class="animate-spin" />
            {/if}
            Sign In
          </button>
        </form>
      </div>

      <p class="text-center text-xs text-zinc-700 mt-6">Scan2Target v2.0</p>
    </div>
  </div>

{:else}
  <!-- ── App shell ──────────────────────────────────────── -->
  <div class="shell">

    <!-- ── Desktop sidebar ──── -->
    <nav class="sidebar" aria-label="Main navigation">
      <!-- Brand -->
      <div class="sidebar-brand">
        <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
             style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">
          <ScanLine size={15} color="white" />
        </div>
        <span class="font-bold text-zinc-50 tracking-tight">Scan<span class="text-indigo-400">2</span>Target</span>
      </div>

      <!-- Nav links -->
      <div class="sidebar-nav">
        {#each navLinks as { href, label, Icon }}
          <a {href} class="nav-link" class:active={isActive(href)}>
            <Icon size={17} />
            {label}
          </a>
        {/each}
      </div>

      <!-- Footer -->
      <div class="sidebar-footer">
        <!-- WS status -->
        <div class="flex items-center gap-2 px-1">
          <span class="ws-dot {wsStatus}"></span>
          <span class="text-xs text-zinc-600">
            {wsStatus === 'connected' ? 'Live' : wsStatus === 'connecting' ? 'Connecting…' : 'Offline'}
          </span>
        </div>

        {#if auth.user}
          <!-- User row -->
          <div class="flex items-center justify-between gap-2 mt-1">
            <div class="flex items-center gap-2 min-w-0">
              <div class="w-7 h-7 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
                <User size={14} class="text-zinc-400" />
              </div>
              <div class="min-w-0">
                <p class="text-xs font-medium text-zinc-300 truncate">{auth.user.username}</p>
                {#if auth.user.is_admin}
                  <p class="text-zinc-600" style="font-size:0.625rem;">Admin</p>
                {/if}
              </div>
            </div>
            <button class="btn btn-ghost btn-icon btn-sm flex-shrink-0" onclick={handleLogout} title="Sign out">
              <LogOut size={14} />
            </button>
          </div>
        {/if}
      </div>
    </nav>

    <!-- ── Mobile header ──── -->
    <header class="mobile-header">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg flex items-center justify-center"
             style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">
          <ScanLine size={14} color="white" />
        </div>
        <span class="font-bold text-zinc-50">Scan<span class="text-indigo-400">2</span>Target</span>
      </div>
      <div class="flex items-center gap-2">
        <!-- WS indicator -->
        {#if wsStatus === 'connected'}
          <Wifi size={16} class="text-emerald-500" />
        {:else}
          <WifiOff size={16} class="text-zinc-600" />
        {/if}
        <button class="btn btn-ghost btn-icon btn-sm" onclick={handleLogout} title="Sign out">
          <LogOut size={16} />
        </button>
      </div>
    </header>

    <!-- ── Main content ──── -->
    <main class="main-content">
      {@render children()}
    </main>

    <!-- ── Mobile bottom nav ──── -->
    <nav class="bottom-nav" aria-label="Mobile navigation">
      <div class="bottom-nav-inner">
        {#each navLinks as { href, label, Icon }}
          <a {href} class="bn-link" class:active={isActive(href)}>
            <Icon size={20} strokeWidth={isActive(href) ? 2.5 : 1.75} />
            <span>{label}</span>
          </a>
        {/each}
      </div>
    </nav>

  </div>
{/if}

<Toast />

<style>
  :global(.animate-spin) { animation: spin 0.75s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
