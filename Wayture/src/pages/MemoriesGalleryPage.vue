<template>
  <section class="gallery-page flex-row">
    <aside class="panel-card p-24 session-sidebar">
      <h2 class="section-title">回忆图册</h2>
      <p class="subtitle">选择一次回忆查看详情。</p>

      <div v-if="isLoadingSessions" class="loading-section">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>
      <div v-else class="session-list">
        <button
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: activeSessionId === session.id }"
          @click="activeSessionId = session.id"
        >
          <strong>{{ session.title }}</strong>
          <span class="session-meta">{{ formatDate(session.created_at) }} · {{ session.generated_image_count }} 张</span>
        </button>
      </div>
      <button class="button-secondary mt-24" @click="router.push('/memories')">返回上传照片</button>
    </aside>

    <section class="panel-card p-24 gallery-main">
      <template v-if="activeSession">
        <div class="flex-row align-center justify-between mb-20">
          <div>
            <h2 class="section-title">{{ activeSession.title }}</h2>
            <p class="subtitle">{{ formatDate(activeSession.created_at) }} · 共 {{ activeSession.generated_image_count }} 张</p>
          </div>
        </div>
        <div class="gallery-grid">
          <div
            v-for="img in activeSession.images"
            :key="img.index"
            class="gallery-item"
            @click="viewingPhoto = normalizeUrl(img.generated_url)"
          >
            <img :src="normalizeUrl(img.generated_url)" :alt="img.description || '回忆'" />
            <p v-if="img.description" class="gallery-desc">{{ img.description }}</p>
          </div>
        </div>
      </template>
      <div v-else-if="!isLoadingSessions && sessions.length === 0" class="empty-state">
        <p>暂无回忆图册，请先上传照片并生成回忆。</p>
        <button class="button-primary" @click="router.push('/memories')">去上传照片</button>
      </div>
      <div v-else-if="!activeSession" class="empty-state">
        <p>请从左侧选择一次回忆。</p>
      </div>
    </section>

    <div v-if="viewingPhoto" class="photo-modal" @click="viewingPhoto = null">
      <div class="photo-modal-content" @click.stop>
        <img :src="viewingPhoto" alt="照片" />
        <button class="close-modal-btn" @click="viewingPhoto = null">&times;</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useTourStore, type GallerySession } from '../composables/useTourStore';

const router = useRouter();
const tour = useTourStore();
const isLoadingSessions = ref(false);

const sessions = computed(() => tour.gallerySessions.value);
const activeSessionId = ref<string | null>(sessions.value[0]?.id ?? null);
const activeSession = computed<GallerySession | undefined>(
  () => sessions.value.find((s) => s.id === activeSessionId.value)
);
const viewingPhoto = ref<string | null>(null);

function normalizeUrl(url: string): string {
  return tour.normalizeImageUrl(url);
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

onMounted(async () => {
  isLoadingSessions.value = true;
  await tour.loadGallerySessions();
  isLoadingSessions.value = false;
  if (!activeSessionId.value && sessions.value.length > 0) {
    activeSessionId.value = sessions.value[0].id;
  }
});
</script>

<style scoped>
.gallery-page {
  gap: 24px;
}

.session-sidebar {
  flex: 0 0 320px;
  min-width: 260px;
}

.gallery-main {
  flex: 1;
}

.subtitle {
  color: #94a3b8;
  margin-top: 4px;
}

.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 0;
  gap: 12px;
  color: #94a3b8;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.session-list {
  display: grid;
  gap: 10px;
  margin-top: 20px;
  max-height: 520px;
  overflow-y: auto;
}

.session-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  padding: 16px 18px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.94);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s, background 0.18s;
}

.session-item:hover,
.session-item.active {
  border-color: rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.12);
}

.session-meta {
  font-size: 0.85rem;
  color: #94a3b8;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

.gallery-item {
  border-radius: 16px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.12);
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s;
}

.gallery-item:hover {
  transform: translateY(-2px);
  border-color: rgba(59, 130, 246, 0.3);
}

.gallery-item img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
}

.gallery-desc {
  margin: 0;
  padding: 14px 16px;
  color: #cbd5e1;
  font-size: 0.92rem;
  line-height: 1.6;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  gap: 20px;
  color: #94a3b8;
  text-align: center;
}

/* --- Photo modal --- */
.photo-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.photo-modal-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}

.photo-modal-content img {
  max-width: 100%;
  max-height: 90vh;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.close-modal-btn {
  position: absolute;
  top: -40px;
  right: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: background 0.2s;
}

.close-modal-btn:hover {
  background: rgba(239, 68, 68, 0.8);
}

@media (max-width: 980px) {
  .gallery-page {
    flex-direction: column;
  }
  .session-sidebar {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .gallery-grid {
    grid-template-columns: 1fr;
  }
}
</style>
