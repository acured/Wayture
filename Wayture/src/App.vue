<template>
  <div id="app">
    <HeaderBar />
    <main class="page-shell">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import HeaderBar from './components/HeaderBar.vue';
</script>
