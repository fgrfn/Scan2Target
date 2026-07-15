<script>
  import { onMount } from 'svelte';
  import { t, lang } from '../lib/i18n';
  import { api, setToken } from '../lib/api';
  import { appStore } from '../stores/app';

  let username = '';
  let email = '';
  let password = '';
  let confirmPassword = '';
  let busy = false;
  let checking = true;
  let setupMode = false;
  let error = '';

  $: copy = $lang === 'de'
    ? {
        title: 'Ersteinrichtung',
        sub: 'Erstelle den ersten Administrator. Dieser Schritt ist nur einmal möglich.',
        email: 'E-Mail (optional)',
        confirm: 'Passwort bestätigen',
        submit: 'Administrator erstellen',
        working: 'Erstelle Konto…',
        mismatch: 'Die Passwörter stimmen nicht überein.',
        passwordHint: 'Mindestens 12 Zeichen mit Großbuchstabe, Kleinbuchstabe und Zahl.'
      }
    : {
        title: 'Initial setup',
        sub: 'Create the first administrator. This step is available only once.',
        email: 'Email (optional)',
        confirm: 'Confirm password',
        submit: 'Create administrator',
        working: 'Creating account…',
        mismatch: 'Passwords do not match.',
        passwordHint: 'At least 12 characters with uppercase, lowercase and a number.'
      };

  onMount(async () => {
    try {
      const status = await api.getSetupStatus();
      setupMode = status?.setup_required === true;
    } catch {
      setupMode = false;
    } finally {
      checking = false;
    }
  });

  async function submit() {
    if (busy || !username || !password) return;
    if (setupMode && password !== confirmPassword) {
      error = copy.mismatch;
      return;
    }

    busy = true;
    error = '';
    try {
      const result = setupMode
        ? await api.setup(username, password, email)
        : await api.login(username, password);
      setToken(result.access_token);
      appStore.setAuthRequired(false);
      appStore.reconnectWebSocket();
      appStore.notify(setupMode ? copy.submit : $t('loggedIn'), 'success');
      password = '';
      confirmPassword = '';
      await appStore.refreshAll();
    } catch (e) {
      error = e.message || $t('loginFailed');
    } finally {
      busy = false;
    }
  }
</script>

<div class="dialog-backdrop login-backdrop">
  <form class="dialog login-dialog" on:submit|preventDefault={submit}>
    <div class="logo-mark login-logo">S2</div>
    <h3>{setupMode ? copy.title : $t('loginTitle')}</h3>
    <p class="muted">{checking ? $t('loading') : (setupMode ? copy.sub : $t('loginSub'))}</p>

    <label>{$t('loginUser')}
      <input bind:value={username} autocomplete="username" minlength="3" maxlength="64" required />
    </label>

    {#if setupMode}
      <label>{copy.email}
        <input type="email" bind:value={email} autocomplete="email" maxlength="254" />
      </label>
    {/if}

    <label>{$t('loginPass')}
      <input
        type="password"
        bind:value={password}
        autocomplete={setupMode ? 'new-password' : 'current-password'}
        minlength={setupMode ? 12 : 1}
        maxlength="256"
        required
      />
    </label>

    {#if setupMode}
      <p class="muted small">{copy.passwordHint}</p>
      <label>{copy.confirm}
        <input
          type="password"
          bind:value={confirmPassword}
          autocomplete="new-password"
          minlength="12"
          maxlength="256"
          required
        />
      </label>
    {/if}

    {#if error}
      <p class="form-error" role="alert">{error}</p>
    {/if}

    <div class="row gap top-gap">
      <button
        class="btn primary"
        type="submit"
        disabled={checking || busy || !username || !password || (setupMode && !confirmPassword)}
      >
        {busy ? (setupMode ? copy.working : $t('loggingIn')) : (setupMode ? copy.submit : $t('loginBtn'))}
      </button>
    </div>
  </form>
</div>
