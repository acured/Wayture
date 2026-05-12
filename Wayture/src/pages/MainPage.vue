<template>
  <section class="flex-col" aria-label="主页面">
    <div class="panel-card p-24">
      <div class="flex-row align-center justify-between wrap">
        <div>
          <h2 class="section-title">我的游览点</h2>
          <p>从地图和列表两种视角查看景点，添加到你的游览计划。</p>
        </div>
        <div class="tab-group">
          <button class="button-secondary" :class="{ active: activeTab === 'map' }" @click="setTab('map')">地图</button>
          <button class="button-secondary" :class="{ active: activeTab === 'list' }" @click="setTab('list')">列表</button>
        </div>
      </div>
      <div v-if="activeTab === 'map'" class="map-card p-24 mt-24">
        <div class="map-frame">
          <canvas ref="mapCanvas" class="map-canvas" @click="onCanvasClick"></canvas>
          <div v-if="selectedPoint" class="info-card-overlay">
            <div class="info-card-image" :style="{ backgroundImage: selectedPoint.images.length ? `url(${selectedPoint.images[0]})` : 'none' }"></div>
            <div class="info-card-body">
              <div class="info-card-top">
                <div>
                  <div class="small-tag">{{ selectedPoint.field }}</div>
                  <h3>{{ selectedPoint.name }}</h3>
                </div>
                <span class="info-duration">{{ selectedPoint.cost }}</span>
              </div>
              <p>{{ selectedPoint.description }}</p>
              <div class="popup-footer">
                <button class="button-primary" @click="addPoint(selectedPoint.id)" :disabled="selectedIds.includes(selectedPoint.id)">
                  {{ selectedIds.includes(selectedPoint.id) ? '已添加' : '加入游览' }}
                </button>
              </div>
            </div>
          </div>
          <div class="canvas-tip">点击地图上的圆点查看详情并添加到你的游览。</div>
        </div>
      </div>
      <div v-else class="list-panel mt-24">
        <div v-for="group in groupedPoints" :key="group.field" class="panel-card p-20 mb-16">
          <div class="flex-row justify-between align-center mb-14">
            <div>
              <div class="group-tag" :style="{ backgroundColor: group.color }">{{ group.field }}</div>
              <h3 class="section-title" style="margin: 8px 0 0;">{{ group.field }} 景点</h3>
            </div>
            <span>{{ group.points.length }} 个</span>
          </div>
          <div class="grid-list">
            <article v-for="point in group.points" :key="point.id" class="info-card p-18">
              <div class="flex-row justify-between align-start gap-12">
                <div class="flex-row gap-12 align-start flex-1">
                  <div class="point-id-badge" :style="{ backgroundColor: getFieldColor(point.field) }">{{ point.id }}</div>
                  <div>
                    <h4>{{ point.name }}</h4>
                    <p>{{ point.description }}</p>
                  </div>
                </div>
                <button class="button-primary" @click="addPoint(point.id)" :disabled="selectedIds.includes(point.id)">
                  {{ selectedIds.includes(point.id) ? '已添加' : '加入游览' }}
                </button>
              </div>
              <div class="mt-12 text-muted">推荐时长：{{ point.cost }}</div>
            </article>
          </div>
        </div>
      </div>
    </div>

    <div class="selected-popup" :class="{ collapsed: !selectedPopupOpen }">
      <div class="selected-popup-header">
        <div>
          <p class="popup-title">当前游览列表</p>
          <p class="popup-subtitle">已选 {{ selectedPoints.length }} 项</p>
        </div>
        <button class="button-secondary small" @click="toggleSelectedPopup">
          {{ selectedPopupOpen ? '收起' : '展开' }}
        </button>
      </div>
      <template v-if="selectedPopupOpen">
        <div v-if="selectedPoints.length === 0" class="popup-empty">暂无已选景点，点击地图或列表添加。</div>
        <ul class="selected-list">
          <li v-for="(point, index) in selectedPoints" :key="point.id" class="selected-item">
            <span class="item-index">{{ index + 1 }}</span>
            <span class="item-name">{{ point.name }}</span>
            <button class="button-secondary tiny" @click="removePoint(point.id)">删除</button>
          </li>
        </ul>
        <button class="button-primary full-width" :disabled="selectedPoints.length === 0" @click="generateTour">生成游览攻略</button>
      </template>
    </div>

    <!-- 导引对话框 -->
    <TourGuideModal
      :show="showGuideModal"
      @complete="onGuideComplete"
      @close="onGuideClose"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useTourStore } from '../composables/useTourStore';
import TourGuideModal from '../components/TourGuideModal.vue';

const router = useRouter();
const tour = useTourStore();

const points = tour.points;
const activeTab = tour.activeTab;
const selectedIds = tour.selectedIds;
const selectedPoints = tour.selectedPoints;
const selectedPointId = ref<number | null>(null);
const selectedPoint = computed(() => points.value.find((item) => item.id === selectedPointId.value) ?? null);
const selectedPopupOpen = ref(true);
const mapCanvas = ref<HTMLCanvasElement | null>(null);
const mapImageElement = new Image();
const showGuideModal = ref(false);

mapImageElement.src = tour.mapImageUrl;

// 按 field 定义颜色
const fieldColorMap: Record<string, string> = {
  '山景区': '#F59E0B',
  '市集区': '#10B981',
  '湖区': '#3B82F6'
};

function getFieldColor(field: string): string {
  return fieldColorMap[field] || '#64748B';
}

function setTab(tab: 'map' | 'list') {
  tour.setTab(tab);
}

function addPoint(id: number) {
  tour.addPoint(id);
  if (selectedPointId.value === id) {
    selectedPointId.value = null;
  }
}

function removePoint(id: number) {
  tour.removePoint(id);
}

function generateTour() {
  if (selectedPoints.value.length === 0) {
    return;
  }
  router.push('/tour');
}

function onGuideComplete(settings: { nickname: string; tourStyle: string }) {
  console.log('导引完成:', settings);
  showGuideModal.value = false;
}

function onGuideClose() {
  showGuideModal.value = false;
}

function toggleSelectedPopup() {
  selectedPopupOpen.value = !selectedPopupOpen.value;
}

const groupedPoints = computed(() => {
  const groups = new Map<string, { color: string; points: typeof points.value }>();
  points.value.forEach((point) => {
    const existing = groups.get(point.field);
    if (existing) {
      existing.points.push(point);
    } else {
      groups.set(point.field, { color: getFieldColor(point.field), points: [point] });
    }
  });
  return Array.from(groups.entries()).map(([field, group]) => ({ field, color: group.color, points: group.points }));
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

  points.value.forEach((point) => {
    const x = (point.location[0] / 100) * rect.width;
    const y = (point.location[1] / 100) * rect.height;
    const isSelected = point.id === selectedPointId.value;
    ctx.beginPath();
    ctx.arc(x, y, isSelected ? 12 : 10, 0, Math.PI * 2);
    ctx.fillStyle = getFieldColor(point.field);
    ctx.fill();
    ctx.lineWidth = isSelected ? 3 : 2;
    ctx.strokeStyle = isSelected ? '#ffffff' : 'rgba(255,255,255,0.85)';
    ctx.stroke();
    
    ctx.fillStyle = '#ffffff';
    ctx.font = '600 11px Inter, ui-sans-serif, system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(point.id), x, y);
  });
}

function resizeCanvas() {
  drawMap();
}

watch(activeTab, async (tab) => {
  if (tab === 'map') {
    await nextTick();
    drawMap();
  }
});

function onCanvasClick(event: MouseEvent) {
  const canvas = mapCanvas.value;
  if (!canvas) {
    return;
  }

  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const hit = points.value.find((point) => {
    const px = (point.location[0] / 100) * rect.width;
    const py = (point.location[1] / 100) * rect.height;
    return Math.hypot(px - x, py - y) <= 14;
  });

  selectedPointId.value = hit ? hit.id : null;
}

onMounted(async () => {
  await tour.loadTourPoints();

  if (mapImageElement.complete) {
    drawMap();
  } else {
    mapImageElement.onload = drawMap;
  }
  window.addEventListener('resize', resizeCanvas);

  // 检查是否需要显示导引对话框
  if (!tour.hasUserSettings()) {
    showGuideModal.value = true;
  }

  // 监听打开导引对话框的事件
  window.addEventListener('openTourGuide', () => {
    showGuideModal.value = true;
  });
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas);
});

watch([selectedPointId, points], drawMap, { deep: true });
</script>

<style scoped>
.p-24 {
  padding: 24px;
}
.mt-24 {
  margin-top: 24px;
}
.mb-16 {
  margin-bottom: 16px;
}
.mb-14 {
  margin-bottom: 14px;
}
.p-20 {
  padding: 20px;
}
.p-18 {
  padding: 18px;
}
.align-center {
  align-items: center;
}
.justify-between {
  justify-content: space-between;
}
.wrap {
  flex-wrap: wrap;
}

.tab-group {
  display: inline-flex;
  gap: 10px;
}

.tab-group button.active {
  color: white;
  background: rgba(59, 130, 246, 0.16);
}

.group-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 700;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.18);
}

.point-id-badge {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #fff;
  font-size: 0.9rem;
  font-weight: 700;
  flex-shrink: 0;
}

.flex-col {
  position: relative;
}

.map-frame {
  position: relative;
  min-height: 520px;
  border-radius: 26px;
  overflow: hidden;
}

.map-canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.canvas-tip {
  position: absolute;
  top: 16px;
  left: 24px;
  padding: 10px 14px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.88);
  color: #e2e8f0;
  font-size: 0.92rem;
  z-index: 5;
}

.selected-popup {
  position: fixed;
  right: 22px;
  bottom: 22px;
  width: min(360px, calc(100% - 32px));
  max-width: 360px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.92));
  border: 1px solid rgba(96, 165, 250, 0.35);
  border-radius: 24px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35), 0 10px 24px rgba(59, 130, 246, 0.08);
  backdrop-filter: blur(20px);
  z-index: 40;
  overflow: hidden;
}

.selected-popup.collapsed {
  width: min(220px, calc(100% - 32px));
}

.selected-popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: rgba(30, 41, 59, 0.98);
  border-bottom: 1px solid rgba(96, 165, 250, 0.18);
}

.popup-title {
  margin: 0;
  font-size: 0.98rem;
  color: #e2e8f0;
  font-weight: 700;
}

.popup-subtitle {
  margin: 4px 0 0;
  font-size: 0.82rem;
  color: #94a3b8;
}

.selected-list {
  list-style: none;
  margin: 0;
  padding: 12px 18px 0;
  display: grid;
  gap: 10px;
  max-height: 220px;
  overflow-y: auto;
}

.selected-item {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(96, 165, 250, 0.14);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 8px 18px rgba(15, 23, 42, 0.18);
}

.item-index {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.22);
  color: #dbeafe;
  font-size: 0.86rem;
  font-weight: 700;
}

.item-name {
  color: #e2e8f0;
  font-size: 0.95rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.popup-empty {
  padding: 18px;
  color: #94a3b8;
}

.full-width {
  width: 100%;
  border-radius: 0 0 24px 24px;
  margin-top: 12px;
}

.info-card-overlay {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: min(420px, calc(100% - 48px));
  max-width: 420px;
  min-height: 460px;
  max-height: min(600px, calc(100% - 48px));
  display: flex;
  flex-direction: column;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 36px 80px rgba(12, 30, 50, 0.35);
  backdrop-filter: blur(18px);
  z-index: 10;
}

.info-card-image {
  height: 210px;
  background-size: cover;
  background-position: center;
  background-color: #1e293b;
}

.info-card-body {
  padding: 22px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.popup-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: auto;
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

.popup-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.info-duration {
  color: #bae6fd;
  font-weight: 700;
  white-space: nowrap;
}

.info-card-body p {
  margin: 0;
  color: #cbd5e1;
  line-height: 1.8;
}

.list-panel {
  display: grid;
  gap: 16px;
}

.grid-list {
  display: grid;
  gap: 16px;
}

.info-card h4 {
  margin: 0;
  font-size: 1.1rem;
}

.info-card p {
  margin: 8px 0 0;
  color: #cbd5e1;
}

.text-muted {
  color: #94a3b8;
  font-size: 0.92rem;
}

.tour-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 14px;
}

.tour-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 20px;
}

.tour-item-left {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  min-width: 0;
}

.tour-thumbnail {
  width: 84px;
  height: 84px;
  border-radius: 18px;
  background-color: rgba(148, 163, 184, 0.12);
  background-position: center;
  background-size: cover;
  flex-shrink: 0;
}

.tour-description {
  margin: 8px 0 0;
  color: #cbd5e1;
  line-height: 1.5;
  max-width: 420px;
}

.empty-state {
  padding: 24px;
  border-radius: 20px;
  border: 1px dashed rgba(148, 163, 184, 0.22);
  text-align: center;
  color: #9ca3af;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
