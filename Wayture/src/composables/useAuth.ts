import { PublicClientApplication, AccountInfo } from '@azure/msal-browser';
import { ref } from 'vue';

const msalConfig = {
  auth: {
    clientId: 'cedddd29-c747-4e81-82ab-d46ef4cf3c66',
    authority: 'https://login.microsoftonline.com/common',
    redirectUri: window.location.origin
  }
};

const loginRequest = {
  scopes: ['openid', 'profile']
};

const msalInstance = new PublicClientApplication(msalConfig);
const account = ref<AccountInfo | null>(null);
const isAuthenticated = ref(false);
const initialized = ref(false);
const clientInitialized = ref(false);

let authPromise: Promise<void> | null = null;

async function ensureClientInitialized() {
  if (!clientInitialized.value) {
    await msalInstance.initialize();
    clientInitialized.value = true;
  }
}

async function initAuth() {
  await ensureClientInitialized();
  if (initialized.value) {
    return;
  }
  if (!authPromise) {
    authPromise = (async () => {
      const response = await msalInstance.handleRedirectPromise();
      if (response?.account) {
        account.value = response.account;
      } else {
        const currentAccounts = msalInstance.getAllAccounts();
        if (currentAccounts.length > 0) {
          account.value = currentAccounts[0];
        }
      }
      isAuthenticated.value = !!account.value;
      initialized.value = true;
    })();
  }
  await authPromise;
}

async function login() {
  await ensureClientInitialized();
  await msalInstance.loginRedirect(loginRequest);
}

async function logout() {
  await ensureClientInitialized();
  await msalInstance.logoutRedirect();
}

export function useAuth() {
  return {
    account,
    isAuthenticated,
    initAuth,
    login,
    logout
  };
}
