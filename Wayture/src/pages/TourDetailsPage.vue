<template>
  <section class="flex-row tour-details-shell">
    <aside class="panel-card p-24 side-panel">
      <div class="flex-row justify-between align-center mb-20">
        <div>
          <h2 class="section-title">游览详情</h2>
          <p class="subtitle">AI 已为你规划最佳游览路线，左侧节点与右侧地图保持同步。</p>
        </div>
        <span class="station-count">{{ orderedPoints.length }} 站</span>
      </div>

      <!-- 加载状态 -->
      <div v-if="tour.routeLoading.value" class="route-loading">
        <div class="loading-spinner"></div>
        <p>正在规划最佳路线...</p>
      </div>

      <!-- 路线列表 -->
      <div v-else class="progress-list">
        <button v-for="(point, index) in orderedPoints" :key="point.id" class="progress-item"
          :class="{ active: highlightId === point.id }"
          @click="setHighlight(point.id)">
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-content">
            <strong>{{ point.name }}</strong>
            <p>{{ point.field }} · {{ point.cost }}</p>
            <p class="step-description">{{ point.description }}</p>
            <p v-if="tipsMap.get(point.id)" class="step-tips">{{ tipsMap.get(point.id) }}</p>
          </div>
        </button>
      </div>
      <button class="button-primary mt-24" @click="toPostcard" :disabled="tour.routeLoading.value">去生成明信片</button>
    </aside>
    <section class="map-panel panel-card p-24">
      <div class="flex-row justify-between align-center mb-20">
        <div>
          <h2 class="section-title">地图同步高亮</h2>
          <p class="subtitle">只显示当前游览列表中的景点，无法编辑位置。</p>
        </div>
        <span class="current-label">高亮：{{ currentHighlight?.name ?? '请选择景点' }}</span>
      </div>
      <div class="map-frame tour-map">
        <canvas ref="mapCanvas" class="map-canvas"></canvas>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useTourStore } from '../composables/useTourStore';

const router = useRouter();
const tour = useTourStore();
const selectedPoints = tour.selectedPoints;
const highlightId = tour.highlightId;
const mapCanvas = ref<HTMLCanvasElement | null>(null);
const mapImageElement = new Image();
mapImageElement.src = tour.mapImageUrl;

const orderedPoints = computed(() => {
  return tour.selectedIds.value
    .map((id) => selectedPoints.value.find((item) => item.id === id))
    .filter((item): item is typeof selectedPoints.value[number] => Boolean(item));
});

const currentHighlight = computed(
  () => orderedPoints.value.find((item) => item.id === highlightId.value) ?? orderedPoints.value[0] ?? null
);

const tipsMap = computed(() => {
  const map = new Map<number, string>();
  tour.routePlan.value.forEach((entry: any) => {
    const id = entry.attraction?.id;
    if (id != null && entry.tips) {
      map.set(id, entry.tips);
    }
  });
  return map;
});

function drawMap() {
  const canvas = mapCanvas.value;
  if (!canvas || !mapImageElement.complete) {
    return;
  }

  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    return;
  }

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.drawImage(mapImageElement, 0, 0, rect.width, rect.height);

  orderedPoints.value.forEach((point, index) => {
    const x = (point.location[0] / 100) * rect.width;
    const y = (point.location[1] / 100) * rect.height;
    const isSelected = point.id === highlightId.value;

    ctx.beginPath();
    ctx.arc(x, y, isSelected ? 14 : 11, 0, Math.PI * 2);
    ctx.fillStyle = point.color;
    ctx.fill();
    ctx.lineWidth = isSelected ? 3 : 2;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = '600 12px Inter, ui-sans-serif, system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(index + 1), x, y);
  });
}

function setHighlight(id: number) {
  tour.setHighlight(id);
}

function toPostcard() {
  router.push('/postcard');
}

function resizeCanvas() {
  drawMap();
}

onMounted(async () => {
  if (selectedPoints.value.length === 0) {
    router.replace('/main');
    return;
  }

  // 调用 API 规划路线
  tour.planRoute();

  if (!highlightId.value) {
    tour.setHighlight(orderedPoints.value[0]?.id ?? null);
  }
  if (mapImageElement.complete) {
    await nextTick();
    drawMap();
  } else {
    mapImageElement.onload = async () => {
      await nextTick();
      drawMap();
    };
  }
  window.addEventListener('resize', resizeCanvas);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas);
});

watch([orderedPoints, highlightId], async () => {
  await nextTick();
  drawMap();
});
</script>

<style scoped>
.tour-details-shell {
  position: relative;
  gap: 24px;
}
.side-panel {
  flex: 0 0 380px;
  min-width: 300px;
}
.map-panel {
  flex: 1;
}

.route-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  gap: 16px;
  color: #94a3b8;
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-list {
  display: grid;
  gap: 14px;
}
.progress-item {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 14px;
  width: 100%;
  padding: 18px 18px 18px 20px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 24px;
  background: rgba(15, 23, 42, 0.94);
  color: inherit;
  text-align: left;
  transition: transform 0.18s ease, border-color 0.18s ease, background-color 0.18s ease;
}
.progress-item:hover,
.progress-item.active {
  transform: translateX(2px);
  border-color: rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.12);
}

.step-number {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: rgba(59, 130, 246, 0.14);
  color: #eff6ff;
  font-weight: 700;
}

.step-content strong {
  display: block;
  font-size: 1rem;
  margin-bottom: 6px;
}

.step-content p {
  margin: 4px 0;
  color: #cbd5e1;
  line-height: 1.5;
}

.step-description {
  margin-top: 8px;
  color: #94a3b8;
}

.step-tips {
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.08);
  border-left: 3px solid rgba(59, 130, 246, 0.4);
  color: #bae6fd;
  font-size: 0.9rem;
  line-height: 1.6;
}

.subtitle {
  color: #cbd5e1;
  margin-top: 4px;
}

.station-count,
.current-label {
  color: #cbd5e1;
  font-size: 0.95rem;
}

.map-frame {
  position: relative;
  min-height: 560px;
  border-radius: 28px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.96);
}

.map-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.info-card-overlay {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: min(520px, calc(100% - 40px));
  background: rgba(15, 23, 42, 0.97);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 36px 80px rgba(12, 30, 50, 0.35);
  backdrop-filter: blur(18px);
  z-index: 10;
}

.info-card-image {
  height: 220px;
  background-size: cover;
  background-position: center;
  background-color: #1e293b;
}

.info-card-body {
  padding: 22px 24px 24px;
}

.info-card-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.info-card-top h3 {
  margin: 0;
  font-size: 1.25rem;
  line-height: 1.2;
}

.info-card-body p {
  margin: 0;
  color: #cbd5e1;
  line-height: 1.8;
}

.info-duration {
  color: #e0f2fe;
  font-weight: 700;
  white-space: nowrap;
}

@media (max-width: 980px) {
  .tour-details-shell {
    flex-direction: column;
  }
  .side-panel {
    width: 100%;
  }
}
</style>
