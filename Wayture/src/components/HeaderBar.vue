<template>
  <header class="header-bar">
    <div class="brand" @click="goHome">Wayture</div>
    <div class="header-actions">
      <template v-if="isAuthenticated">
        <span class="user-badge">{{ account?.name || '游客' }}</span>
        <button class="button-secondary" @click="openSettings" title="修改游览设置">⚙️</button>
        <button class="button-secondary" @click="logout">退出</button>
      </template>
      <template v-else>
        <button class="button-primary" @click="login">登录</button>
      </template>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '../composables/useAuth';
import { useTourStore } from '../composables/useTourStore';

const auth = useAuth();
const router = useRouter();
const tour = useTourStore();

onMounted(async () => {
  await auth.initAuth();
});

const isAuthenticated = computed(() => auth.isAuthenticated.value);
const account = computed(() => auth.account.value);

function login() {
  auth.login();
}

function logout() {
  auth.logout();
}

function goHome() {
  router.push('/');
}

function openSettings() {
  // 触发MainPage的导引对话框
  if (router.currentRoute.value.path === '/main') {
    // 通过自定义事件通知MainPage打开设置
    window.dispatchEvent(new CustomEvent('openTourGuide'));
  } else {
    // 如果不在主页面，跳转到主页面并打开设置
    router.push('/main').then(() => {
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('openTourGuide'));
      }, 100);
    });
  }
}
</script>

<style scoped>
.header-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  background: rgba(15, 23, 42, 0.88);
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  z-index: 20;
}

.brand {
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #eff6ff;
  cursor: pointer;
}

.header-actions {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.user-badge {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
}
</style>
