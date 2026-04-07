import type { User } from '$lib/api/auth';

function createAuthStore() {
  let user = $state<User | null>(null);
  let token = $state<string | null>(
    typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null
  );

  return {
    get user() {
      return user;
    },
    get token() {
      return token;
    },
    get isAuthenticated() {
      return token !== null;
    },
    login(u: User, t: string) {
      user = u;
      token = t;
      localStorage.setItem('token', t);
    },
    logout() {
      user = null;
      token = null;
      localStorage.removeItem('token');
    },
    setUser(u: User) {
      user = u;
    }
  };
}

export const auth = createAuthStore();
