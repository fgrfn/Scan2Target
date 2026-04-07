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

  interface Props {
    children: Snippet;
  }
  let { children }: Props = $props();

  // Login form state
  let loginUsername = $state('');
  let loginPassword = $state('');
  let loginLoading = $state(false);
  let loginError = $state('');

  // Sidebar open on mobile
  let sidebarOpen = $state(false);

  // Bootstrap: check existing token
  let bootstrapped = $state(false);

  onMount(async () => {
    if (auth.token) {
      try {
        const user = await getMe();
        auth.setUser(user);
        wsStore.start();
      } catch {
        auth.logout();
      }
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
    try {
      wsStore.disconnect();
      auth.logout();
    } catch {
      auth.logout();
    }
    showToast('Logged out', 'info');
  }

  function closeSidebar() {
    sidebarOpen = false;
  }

  const navLinks = [
    { href: '/', label: 'Scan', icon: '🖨' },
    { href: '/devices', label: 'Devices', icon: '📡' },
    { href: '/targets', label: 'Targets', icon: '🎯' },
    { href: '/history', label: 'History', icon: '📋' },
    { href: '/stats', label: 'Stats', icon: '📊' },
    { href: '/settings', label: 'Settings', icon: '⚙' }
  ];

  function isActive(href: string): boolean {
    const path = $page.url.pathname;
    if (href === '/') return path === '/';
    return path.startsWith(href);
  }

  const wsStatusLabel = $derived(
    wsStore.status === 'connected'
      ? 'Connected'
      : wsStore.status === 'connecting'
      ? 'Connecting…'
      : 'Disconnected'
  );
</script>

{#if !bootstrapped}
  <div class="boot-loader">
    <Spinner size="lg" />
  </div>
{:else if !auth.isAuthenticated}
  <!-- Login screen -->
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">
        <span class="logo-icon">🖨</span>
        <span class="logo-text">Scan<span class="text-primary">2</span>Target</span>
      </div>
      <p class="login-sub">Self-hosted scanner-to-cloud delivery hub</p>

      {#if loginError}
        <div class="login-error">{loginError}</div>
      {/if}

      <form onsubmit={handleLogin}>
        <div class="form-group">
          <label class="form-label" for="login-user">Username</label>
          <input
            id="login-user"
            class="form-control"
            type="text"
            bind:value={loginUsername}
            required
            autocomplete="username"
            placeholder="admin"
          />
        </div>
        <div class="form-group">
          <label class="form-label" for="login-pass">Password</label>
          <input
            id="login-pass"
            class="form-control"
            type="password"
            bind:value={loginPassword}
            required
            autocomplete="current-password"
          />
        </div>
        <button type="submit" class="btn btn-primary w-full btn-lg" disabled={loginLoading}>
          {#if loginLoading}<Spinner size="sm" />{/if}
          Sign In
        </button>
      </form>
    </div>
  </div>
{:else}
  <!-- App shell -->
  <div class="app-shell">
    <!-- Mobile header -->
    <header class="mobile-header">
      <button class="hamburger" onclick={() => (sidebarOpen = !sidebarOpen)} aria-label="Menu">
        ☰
      </button>
      <span class="mobile-logo">Scan<span class="text-primary">2</span>Target</span>
      <div style="width:32px"></div>
    </header>

    <!-- Overlay -->
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions a11y_no_noninteractive_element_interactions -->
    <div class="overlay" class:open={sidebarOpen} role="presentation" onclick={closeSidebar}></div>

    <!-- Sidebar -->
    <nav class="sidebar" class:open={sidebarOpen} aria-label="Main navigation">
      <a href="/" class="sidebar-logo" onclick={closeSidebar}>
        <span class="logo-icon">🖨</span>
        <span>Scan<span>2</span>Target</span>
      </a>

      <div class="sidebar-nav">
        {#each navLinks as link}
          <a
            href={link.href}
            class="nav-link"
            class:active={isActive(link.href)}
            onclick={closeSidebar}
          >
            <span class="nav-icon">{link.icon}</span>
            {link.label}
          </a>
        {/each}
      </div>

      <!-- WS status -->
      <div class="ws-indicator">
        <span class="ws-dot {wsStore.status}"></span>
        {wsStatusLabel}
      </div>

      <div class="sidebar-footer">
        {#if auth.user}
          <div class="user-info">
            <span class="user-name">👤 {auth.user.username}</span>
            {#if auth.user.is_admin}
              <span class="badge badge-primary" style="font-size:0.65rem;margin-left:4px">admin</span>
            {/if}
          </div>
          <button class="btn btn-ghost btn-sm" style="margin-top:8px;width:100%;" onclick={handleLogout}>
            Sign Out
          </button>
        {/if}
      </div>
    </nav>

    <!-- Main content -->
    <main class="main-content">
      {@render children()}
    </main>
  </div>
{/if}

<Toast />

<style>
  .boot-loader {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
  }

  /* Login page */
  .login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: var(--color-bg);
  }

  .login-card {
    width: 100%;
    max-width: 380px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 32px 28px;
    box-shadow: var(--shadow-lg);
  }

  .login-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 6px;
  }

  .logo-icon {
    font-size: 1.8rem;
  }

  .logo-text {
    font-size: 1.4rem;
    font-weight: 700;
  }

  .login-sub {
    color: var(--color-text-muted);
    font-size: 0.85rem;
    margin-bottom: 24px;
  }

  .login-error {
    background: var(--color-error-dim);
    border: 1px solid var(--color-error);
    color: var(--color-error);
    border-radius: var(--radius-md);
    padding: 10px 14px;
    font-size: 0.875rem;
    margin-bottom: 16px;
  }

  .mobile-logo {
    font-weight: 700;
    font-size: 1rem;
  }

  .user-info {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
  }

  .user-name {
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .sidebar-logo span {
    color: var(--color-primary);
  }
</style>
