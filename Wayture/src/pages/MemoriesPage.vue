<template>
  <section class="memories-page" aria-label="回忆页面">
    <div class="panel-card p-24">
      <div class="flex-row align-center justify-between wrap">
        <div>
          <h2 class="section-title">我的旅行回忆</h2>
          <p>上传照片，选择后生成回忆图册。</p>
        </div>
        <button class="button-secondary" @click="router.push('/memories-gallery')">
          查看回忆图册{{ tour.gallerySessions.value.length > 0 ? ` (${tour.gallerySessions.value.length})` : '' }}
        </button>
      </div>

      <!-- 加载中 -->
      <div v-if="isLoading" class="loading-section">
        <div class="spinner"></div>
        <p>加载照片中...</p>
      </div>

      <!-- 照片墙 -->
      <div v-else>
        <div class="photo-grid">
          <!-- 上传按钮 -->
          <div class="upload-slot" :class="{ disabled: isUploading }" @click="triggerFileInput">
            <div class="upload-content">
              <div v-if="isUploading" class="spinner small"></div>
              <div v-else class="upload-icon">+</div>
              <p>{{ isUploading ? '上传中...' : '点击上传照片' }}</p>
            </div>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept="image/*"
              @change="handleUpload"
              style="display: none"
            />
          </div>

          <!-- 服务器照片列表 -->
          <div
            v-for="photo in photos"
            :key="photo.index"
            class="photo-item"
            :class="{ selected: selectedIndices.has(photo.index) }"
            @click="toggleSelect(photo.index)"
          >
            <img :src="getPhotoUrl(photo)" :alt="photo.filename || '照片'" />
            <div class="select-overlay">
              <div class="checkbox" :class="{ checked: selectedIndices.has(photo.index) }"></div>
            </div>
          </div>
        </div>

        <!-- 操作区 -->
        <div class="action-section">
          <div class="action-bar">
            <span class="select-count">已选 {{ selectedIndices.size }} / {{ photos.length }} 张</span>
            <div class="action-buttons">
              <button v-if="photos.length > 0" class="button-secondary" @click="toggleSelectAll">
                {{ selectedIndices.size === photos.length ? '取消全选' : '全选' }}
              </button>
              <button
                class="button-primary"
                :disabled="selectedIndices.size === 0 || isGenerating"
                @click="generateGallery"
              >
                {{ isGenerating ? '生成中...' : '生成回忆' }}
              </button>
            </div>
          </div>
          <p v-if="photos.length === 0" class="hint-text">请先上传至少一张照片</p>
        </div>
      </div>
    </div>

    <!-- 照片查看模态框 -->
    <div v-if="viewingPhoto" class="photo-modal" @click="viewingPhoto = null">
      <div class="photo-modal-content" @click.stop>
        <img :src="viewingPhoto" alt="照片" />
        <button class="close-modal-btn" @click="viewingPhoto = null">&times;</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useTourStore } from '../composables/useTourStore';

const router = useRouter();
const tour = useTourStore();
const apiBase = tour.apiBase;

const fileInput = ref<HTMLInputElement | null>(null);
const photos = ref<any[]>([]);
const selectedIndices = reactive(new Set<number>());
const isLoading = ref(false);
const isUploading = ref(false);
const isGenerating = ref(false);
const viewingPhoto = ref<string | null>(null);

function normalizeUrl(url: string): string {
  if (!url || url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  return `${apiBase}${url.startsWith('/') ? '' : '/'}${url}`;
}

function getPhotoUrl(photo: any): string {
  const raw = photo.url || photo.image_url || photo.thumbnail_url || '';
  return normalizeUrl(raw);
}

// --- 加载照片列表 ---
async function fetchPhotos() {
  isLoading.value = true;
  try {
    const resp = await fetch(`${apiBase}/api/images/${encodeURIComponent(tour.currentUsername.value)}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    photos.value = await resp.json();
  } catch (e) {
    console.warn('获取照片列表失败:', e);
    photos.value = [];
  } finally {
    isLoading.value = false;
  }
}

// --- 上传照片 ---
function triggerFileInput() {
  if (isUploading.value) return;
  fileInput.value?.click();
}

async function handleUpload(event: Event) {
  const target = event.target as HTMLInputElement;
  const files = target.files;
  if (!files || files.length === 0) return;

  isUploading.value = true;
  try {
    for (const file of Array.from(files)) {
      if (!file.type.startsWith('image/')) continue;
      const formData = new FormData();
      formData.append('username', tour.currentUsername.value);
      formData.append('file', file, file.name);
      await fetch(`${apiBase}/api/upload-image`, {
        method: 'POST',
        body: formData,
      });
    }
    await fetchPhotos();
  } catch (e) {
    console.error('上传失败:', e);
  } finally {
    isUploading.value = false;
    target.value = '';
  }
}

// --- 选择操作 ---
function toggleSelect(index: number) {
  if (selectedIndices.has(index)) {
    selectedIndices.delete(index);
  } else {
    selectedIndices.add(index);
  }
}

function toggleSelectAll() {
  if (selectedIndices.size === photos.value.length) {
    selectedIndices.clear();
  } else {
    photos.value.forEach(p => selectedIndices.add(p.index));
  }
}

// --- 生成回忆 ---
async function generateGallery() {
  if (selectedIndices.size === 0) return;

  isGenerating.value = true;
  try {
    const resp = await fetch(`${apiBase}/api/generate-gallery`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: tour.currentUsername.value,
        selected_indices: Array.from(selectedIndices),
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const memory = data.memory || {};

    const session = {
      id: memory.id || Date.now().toString(),
      title: memory.title || `回忆 ${new Date().toLocaleDateString('zh-CN')}`,
      created_at: new Date().toISOString(),
      images: (data.images || []).map((img: any) =>
        typeof img === 'string'
          ? { index: 0, generated_url: img, description: '' }
          : { index: img.index ?? 0, generated_url: img.generated_url || img.url || '', description: img.description || '' , source_photo: img.source_photo }
      ),
      source_photo_count: memory.source_photo_count || 0,
      generated_image_count: memory.generated_image_count || 0,
    };
    tour.addGallerySession(session);
    selectedIndices.clear();
    router.push('/memories-gallery');
  } catch (e) {
    console.error('生成回忆失败:', e);
  } finally {
    isGenerating.value = false;
  }
}

onMounted(() => {
  fetchPhotos();
});
</script>

<style scoped>
.memories-page {
  padding: 24px;
}

/* --- Loading --- */
.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 0;
  gap: 14px;
  color: #94a3b8;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner.small {
  width: 24px;
  height: 24px;
  border-width: 2.5px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* --- Photo grid --- */
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin: 24px 0;
}

.upload-slot {
  aspect-ratio: 1;
  border: 2px dashed rgba(148, 163, 184, 0.3);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(15, 23, 42, 0.3);
}

.upload-slot:hover:not(.disabled) {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.upload-slot.disabled {
  cursor: wait;
  opacity: 0.7;
}

.upload-content {
  text-align: center;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 3rem;
  font-weight: 300;
  color: #64748b;
  line-height: 1;
}

.upload-content p {
  margin: 0;
  font-size: 0.9rem;
}

/* --- Photo item with selection --- */
.photo-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border: 3px solid transparent;
}

.photo-item:hover {
  transform: scale(1.02);
}

.photo-item.selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.select-overlay {
  position: absolute;
  top: 10px;
  left: 10px;
}

.checkbox {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  border: 2px solid rgba(255, 255, 255, 0.7);
  background: rgba(0, 0, 0, 0.3);
  transition: all 0.15s;
  position: relative;
}

.checkbox.checked {
  background: #3b82f6;
  border-color: #3b82f6;
}

.checkbox.checked::after {
  content: '';
  position: absolute;
  left: 7px;
  top: 3px;
  width: 6px;
  height: 11px;
  border: solid #fff;
  border-width: 0 2.5px 2.5px 0;
  transform: rotate(45deg);
}

/* --- Action section --- */
.action-section {
  margin-top: 8px;
}

.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.select-count {
  color: #94a3b8;
  font-size: 0.95rem;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.hint-text {
  margin: 16px 0 0;
  color: #94a3b8;
  font-size: 0.9rem;
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

@media (max-width: 640px) {
  .photo-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }

  .memories-page {
    padding: 16px;
  }

  .action-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .action-buttons {
    justify-content: flex-end;
  }
}
</style>
