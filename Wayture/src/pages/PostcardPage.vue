<template>
  <section class="postcard-shell flex-row">
    <aside class="panel-card left-panel p-24">
      <div class="flex-row justify-between align-center mb-20">
        <div>
          <h2 class="section-title">明信片助手</h2>
          <p>通过对话调整封面文字与风格。</p>
        </div>
        <span>{{ messages.length }} 条对话</span>
      </div>
      <div class="chat-panel">
        <div v-for="(message, index) in messages" :key="index" class="chat-bubble" :class="message.role">
          <strong>{{ message.role === 'user' ? '你' : 'AI' }}</strong>
          <p>{{ message.text }}</p>
        </div>
      </div>
      <form class="chat-form" @submit.prevent="sendMessage">
        <textarea v-model="draft" placeholder="输入额外的风格要求，例如：请加入中国水墨画风格元素..." rows="4" :disabled="isGenerating"></textarea>
        <button class="button-primary" type="submit" :disabled="isGenerating || !draft.trim()">{{ isGenerating ? '生成中...' : '发送' }}</button>
      </form>
    </aside>
    <section class="postcard-panel panel-card p-24">
      <div class="flex-row justify-between align-center mb-20">
        <div>
          <h2 class="section-title">明信片预览</h2>
          <p>你当前明信片内容会在这里自动生成。</p>
        </div>
      </div>
      <article class="postcard-card p-24">
        <div v-if="isGenerating" class="postcard-hero loading-state">
          <div class="loading-spinner">正在生成明信片...</div>
        </div>
        <div v-else-if="postcardImageUrl" class="postcard-hero" :style="{ backgroundImage: `url(${postcardImageUrl})` }"></div>
        <div v-else class="postcard-hero"></div>
        <div class="postcard-content">
          <h3>旅行记忆</h3>
          <p>{{ postcardText }}</p>
        </div>
      </article>
      <button class="button-primary mt-24" @click="submitPostcard">提交</button>
    </section>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useTourStore } from '../composables/useTourStore';

const router = useRouter();
const tour = useTourStore();
const draft = ref('');
const isGenerating = ref(false);
const postcardImageUrl = ref<string | null>(null);
const promptParts = ref<string[]>([]);
const messages = ref([
  { role: 'assistant', text: '欢迎使用明信片生成器。正在根据你的游览路线自动生成明信片，你也可以输入额外的风格要求来重新生成。' }
]);

const styleMap: Record<string, string> = {
  family: '全家游',
  solo: '单身游',
  couple: '情侣游',
  relaxed: '轻松游',
};

const postcardText = computed(() => {
  const highlight = tour.selectedPoints.value.map((item) => `· ${item.name}（${item.cost}）`).join('\n');
  const message = messages.value.filter((item) => item.role === 'assistant').pop()?.text ?? '期待你的旅行故事。';
  return `${message}\n\n游览路线：\n${highlight}`;
});

function normalizeImageUrl(url: string): string {
  if (!url || url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  return `${tour.apiBase}${url.startsWith('/') ? '' : '/'}${url}`;
}

async function generatePostcard(additionPrompt: string = '') {
  isGenerating.value = true;
  try {
    const resp = await fetch(`${tour.apiBase}/api/generate-postcard`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: tour.currentUsername.value,
        route_plan: tour.routePlan.value,
        attractions: tour.selectedPoints.value,
        addition_prompt: additionPrompt,
      }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    const imageUrl = data.image_url || null;
    postcardImageUrl.value = imageUrl ? normalizeImageUrl(imageUrl) : null;

    if (postcardImageUrl.value) {
      messages.value.push({ role: 'assistant', text: additionPrompt ? `已根据你的要求重新生成明信片。` : '明信片已生成完成。' });
    }
  } catch (error) {
    console.error('生成明信片出错:', error);
    messages.value.push({ role: 'assistant', text: '生成失败，请稍后重试。' });
  } finally {
    isGenerating.value = false;
  }
}

function sendMessage() {
  if (!draft.value.trim()) return;
  const userText = draft.value.trim();
  messages.value.push({ role: 'user', text: userText });
  promptParts.value.push(userText);
  draft.value = '';
  generatePostcard(promptParts.value.join('\n'));
}

function submitPostcard() {
  alert('明信片已提交，流程结束。祝你旅途愉快！');
  router.push('/');
}

onMounted(() => {
  const nickname = tour.userSettings.value.nickname;
  const tourStyle = tour.userSettings.value.tourStyle;
  const parts: string[] = [];
  if (nickname) parts.push(`昵称/标题: ${nickname}`);
  if (tourStyle) parts.push(`游览风格: ${styleMap[tourStyle] || tourStyle}`);
  const initial = parts.join(', ');
  if (initial) promptParts.value.push(initial);
  generatePostcard(promptParts.value.join('\n'));
});
</script>

<style scoped>
.postcard-shell {
  position: relative;
  gap: 24px;
}
.left-panel {
  flex: 0 0 400px;
  min-width: 300px;
}
.postcard-panel {
  flex: 1;
}
.chat-panel {
  display: grid;
  gap: 14px;
  max-height: 520px;
  overflow-y: auto;
  margin-bottom: 20px;
}
.chat-bubble {
  padding: 16px;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(15, 23, 42, 0.9);
}
.chat-bubble.user {
  background: rgba(59, 130, 246, 0.14);
}
.chat-bubble.assistant {
  background: rgba(75, 85, 99, 0.9);
}
.chat-bubble strong {
  display: block;
  margin-bottom: 8px;
}
.chat-form {
  display: grid;
  gap: 12px;
}
.chat-form textarea {
  width: 100%;
  resize: vertical;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.95);
  color: #e2e8f0;
  padding: 14px;
}
.postcard-card {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.postcard-hero {
  height: 280px;
  border-radius: 24px;
  background-image: url('https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80');
  background-size: cover;
  background-position: center;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05);
}
.postcard-hero.loading-state {
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.6);
}
.loading-spinner {
  color: #e2e8f0;
  font-size: 1rem;
  text-align: center;
}
.postcard-content h3 {
  margin: 0;
}
.postcard-content p {
  margin: 12px 0 0;
  white-space: pre-wrap;
  line-height: 1.75;
  color: #cbd5e1;
}
@media (max-width: 980px) {
  .postcard-shell {
    flex-direction: column;
  }
  .left-panel {
    width: 100%;
  }
}
</style>
