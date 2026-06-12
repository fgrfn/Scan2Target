<script>
  import { t } from '../lib/i18n';
  import { api, setToken } from '../lib/api';
  import { appStore } from '../stores/app';

  let username = '';
  let password = '';
  let busy = false;
  let error = '';

  async function submit() {
    if (busy || !username || !password) return;
    busy = true;
    error = '';
    try {
      const result = await api.login(username, password);
      setToken(result.access_token);
      appStore.setAuthRequired(false);
      appStore.notify($t('loggedIn'), 'success');
      password = '';
      await appStore.refreshAll();
    } catch (e) {
      error = $t('loginFailed');
    } finally {
      busy = false;
    }
  }
</script>

<div class="dialog-backdrop login-backdrop">
  <form class="dialog login-dialog" on:submit|preventDefault={submit}>
    <div class="logo-mark login-logo">S2</div>
    <h3>{$t('loginTitle')}</h3>
    <p class="muted">{$t('loginSub')}</p>

    <label>{$t('loginUser')}
      <input bind:value={username} autocomplete="username" required />
    </label>
    <label>{$t('loginPass')}
      <input type="password" bind:value={password} autocomplete="current-password" required />
    </label>

    {#if error}
      <p class="form-error" role="alert">{error}</p>
    {/if}

    <div class="row gap top-gap">
      <button class="btn primary" type="submit" disabled={busy || !username || !password}>
        {busy ? $t('loggingIn') : $t('loginBtn')}
      </button>
    </div>
  </form>
</div>
