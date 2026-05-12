<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click="closeOnOverlay">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ step === 1 ? '设置昵称' : '选择游览风格' }}</h3>
          <button class="close-btn" @click="close">&times;</button>
        </div>

        <div class="modal-body">
          <!-- 第一步：昵称输入 -->
          <div v-if="step === 1" class="step-content">
            <p>请为你的旅程设置一个昵称或标题：</p>
            <input
              v-model="nickname"
              type="text"
              placeholder="例如：北京五日游、浪漫巴黎行"
              class="nickname-input"
              @keyup.enter="nextStep"
            />
          </div>

          <!-- 第二步：风格选择 -->
          <div v-else-if="step === 2" class="step-content">
            <p>请选择你的游览风格：</p>
            <div class="style-options">
              <button
                v-for="style in tourStyles"
                :key="style.value"
                :class="['style-btn', { active: selectedStyle === style.value }]"
                @click="selectedStyle = style.value"
              >
                <span class="style-icon">{{ style.icon }}</span>
                <span class="style-name">{{ style.name }}</span>
                <span class="style-desc">{{ style.desc }}</span>
              </button>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button v-if="step > 1" class="btn-secondary" @click="prevStep">上一步</button>
          <button
            class="btn-primary"
            :disabled="!canProceed"
            @click="step === 2 ? complete() : nextStep()"
          >
            {{ step === 2 ? '完成' : '下一步' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useTourStore } from '../composables/useTourStore';

interface Props {
  show: boolean;
  onComplete: (settings: { nickname: string; tourStyle: string }) => void;
  onClose: () => void;
}

const props = defineProps<Props>();

const tour = useTourStore();

const step = ref(1);
const nickname = ref('');
const selectedStyle = ref('');

const tourStyles = [
  { value: 'family', name: '全家游', icon: '👨‍👩‍👧‍👦', desc: '适合家庭出游，轻松愉快' },
  { value: 'solo', name: '单身游', icon: '🧳', desc: '独自旅行，自由自在' },
  { value: 'couple', name: '情侣游', icon: '💑', desc: '浪漫二人世界' },
  { value: 'relaxed', name: '轻松游', icon: '🏖️', desc: '悠闲度假，享受生活' }
];

const canProceed = computed(() => {
  if (step.value === 1) {
    return nickname.value.trim().length > 0;
  } else if (step.value === 2) {
    return selectedStyle.value !== '';
  }
  return false;
});

// 初始化数据
watch(() => props.show, (newShow) => {
  if (newShow) {
    step.value = 1;
    nickname.value = tour.userSettings.value.nickname || '';
    selectedStyle.value = tour.userSettings.value.tourStyle || '';
  }
});

function nextStep() {
  if (canProceed.value && step.value < 2) {
    step.value++;
  }
}

function prevStep() {
  if (step.value > 1) {
    step.value--;
  }
}

function complete() {
  if (canProceed.value) {
    const settings = {
      nickname: nickname.value.trim(),
      tourStyle: selectedStyle.value
    };
    tour.setUserSettings(settings);
    props.onComplete(settings);
  }
}

function close() {
  props.onClose();
}

function closeOnOverlay() {
  // 如果是修改模式，允许点击遮罩关闭；如果是初始设置，不允许
  if (tour.hasUserSettings()) {
    close();
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: rgba(15, 23, 42, 0.95);
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 0;
  margin-bottom: 24px;
}

.modal-header h3 {
  margin: 0;
  color: #e2e8f0;
  font-size: 1.5rem;
}

.close-btn {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 24px;
  cursor: pointer;
  padding: 4px;
  border-radius: 8px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(148, 163, 184, 0.1);
  color: #e2e8f0;
}

.modal-body {
  padding: 0 24px;
}

.step-content {
  text-align: center;
}

.step-content p {
  color: #cbd5e1;
  margin-bottom: 20px;
  font-size: 1.1rem;
}

.nickname-input {
  width: 100%;
  padding: 16px;
  border: 2px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.8);
  color: #e2e8f0;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.nickname-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.style-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 20px;
}

.style-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 16px;
  border: 2px solid rgba(148, 163, 184, 0.2);
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.6);
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.style-btn:hover {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.style-btn.active {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.2);
  color: #e2e8f0;
}

.style-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}

.style-name {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 4px;
}

.style-desc {
  font-size: 0.9rem;
  opacity: 0.8;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 24px;
  margin-top: 24px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.btn-secondary,
.btn-primary {
  padding: 12px 24px;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-secondary {
  background: rgba(148, 163, 184, 0.2);
  color: #cbd5e1;
}

.btn-secondary:hover {
  background: rgba(148, 163, 184, 0.3);
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .style-options {
    grid-template-columns: 1fr;
  }

  .modal-content {
    margin: 20px;
    width: calc(100% - 40px);
  }
}
</style>