import { createRouter, createWebHistory } from 'vue-router';
import HomePage from '../pages/HomePage.vue';
import MainPage from '../pages/MainPage.vue';
import TourDetailsPage from '../pages/TourDetailsPage.vue';
import PostcardPage from '../pages/PostcardPage.vue';
import MemoriesPage from '../pages/MemoriesPage.vue';
import MemoriesGalleryPage from '../pages/MemoriesGalleryPage.vue';
import { useAuth } from '../composables/useAuth';

const routes = [
  { path: '/', name: 'Home', component: HomePage },
  { path: '/main', name: 'Main', component: MainPage, meta: { requiresAuth: true } },
  { path: '/tour', name: 'TourDetails', component: TourDetailsPage, meta: { requiresAuth: true } },
  { path: '/postcard', name: 'Postcard', component: PostcardPage, meta: { requiresAuth: true } },
  { path: '/memories', name: 'Memories', component: MemoriesPage, meta: { requiresAuth: true } },
  { path: '/memories-gallery', name: 'MemoriesGallery', component: MemoriesGalleryPage, meta: { requiresAuth: true } }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

let authInitialized = false;
router.beforeEach(async (to) => {
  const auth = useAuth();
  if (!authInitialized) {
    await auth.initAuth();
    authInitialized = true;
  }
  if (to.meta.requiresAuth && !auth.isAuthenticated.value) {
    auth.login();
    return false;
  }
  return true;
});

export default router;
