<template>
  <section class="hero-card" aria-label="首页">
    <div class="hero-background"></div>
    <div class="hero-content">
      <h1>Wayture 游览导览</h1>
      <p>从地图、列表到明信片，一站式规划你的旅程。</p>
      <div class="hero-actions">
        <button class="button-primary hero-button" @click="explore">探索</button>
        <button class="button-secondary hero-button" @click="memories">回忆</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '../composables/useAuth';

const router = useRouter();
const auth = useAuth();

onMounted(async () => {
  await auth.initAuth();
});

function explore() {
  if (!auth.isAuthenticated.value) {
    auth.login();
  } else {
    router.push('/main');
  }
}

function memories() {
  if (!auth.isAuthenticated.value) {
    auth.login();
  } else {
    router.push('/memories');
  }
}
</script>

<style scoped>
.hero-card {
  position: relative;
  min-height: calc(100vh - 96px);
  overflow: hidden;
  display: grid;
  place-items: center;
  border-radius: 32px;
  padding: 56px 100px;
}

.hero-background {
  position: absolute;
  inset: 0;
  background-image: url('https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1350&q=80');
  background-size: cover;
  background-position: center;
  opacity: 0.35;
  filter: grayscale(0.2) contrast(1.05);
}

.hero-content {
  position: relative;
  text-align: center;
  max-width: min(620px, calc(100vw - 220px));
  color: white;
}

.hero-content h1 {
  font-size: clamp(3rem, 5vw, 5rem);
  line-height: 1;
  margin-bottom: 16px;
}

.hero-content p {
  margin-bottom: 28px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 1.1rem;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.hero-button {
  min-width: 160px;
}
</style>
