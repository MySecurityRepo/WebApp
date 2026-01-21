import { createRouter, createWebHistory } from 'vue-router'



export const routes = [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/registration',
      component: () => import('@/views/Registration.vue'),
    },
    {
      path: '/confirmation',
      component: () => import('@/views/EmailConfirmation.vue'),
    },
    {
      path: '/resend-mail',
      component: () => import('@/views/ResendMail.vue'),
    },
    {
      path: '/login',
      component: () => import('@/views/Login.vue'),
    },
    {
      path: '/forgot-password',
      component: () => import('@/views/ForgotPassword.vue'),
    },
    {
      path: '/reset-password',
      component: () => import('@/views/ResetPassword.vue'),
    },
    {
      path: '/user/:id',
      component: () => import('@/views/UserProfile.vue'),
    },
    {
      path: '/post/:id',
      component: () => import('@/views/Post.vue'),
    },
    {
      path: '/post/:id/:slug',
      component: () => import('@/views/Post.vue'),
    },
    {
      path: '/post/:id/:slug/:commentId',
      component: () => import('@/views/Post.vue'),
    },
    {
      path: '/modify-password',
      component: () => import('@/views/ModifyPassword.vue'),
    },
    {
      path: '/search',
      name: 'Search',
      component: () => import('@/views/Search.vue'),
    },
    {
      path: '/delete-confirmation',
      component: () => import('@/views/DeleteConfirmation.vue'),
    },
    {
      path: '/favorites',
      component: () => import('@/views/FavoritesView.vue'),
    },
    {
      path: '/books',
      component: () => import('@/views/BooksView.vue'),
    },
    {
      path: '/art-music',
      component: () => import('@/views/ArtView.vue'),
    },
    {
      path: '/tech-science',
      component: () => import('@/views/TechView.vue'),
    },
    {
      path: '/movies-series',
      component: () => import('@/views/SerieView.vue'),
    },
    {
      path: '/sports',
      component: () => import('@/views/SportView.vue'),
    },
    {
      path: '/social',
      component: () => import('@/views/SocialView.vue'),
    },
    {
      path: '/info-contacts',
      component: () => import('@/views/Info.vue'),
    },
    {
      path: '/subscription_done',
      component: () => import('@/views/SubscriptionDone.vue'),
    },
    {
      path: '/subscription_cancellation_done',
      component: () => import('@/views/SubscriptionCancellationDone.vue'),
    },
    {
      path: '/en',
      component: () => import('@/views/LandingEnglish.vue'),
    },
    {
      path: '/it',
      component: () => import('@/views/LandingItalian.vue'),
    },
    {
      path: '/es',
      component: () => import('@/views/LandingSpanish.vue'),
    },
    {
      path: '/fr',
      component: () => import('@/views/LandingFrench.vue'),
    },
    {
      path: '/de',
      component: () => import('@/views/LandingGerman.vue'),
    },
    {
      path: '/pt',
      component: () => import('@/views/LandingPortuguese.vue'),
    },
    {
      path: '/ja',
      component: () => import('@/views/LandingJapanese.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      component: () => import('@/views/NotFound.vue'),
    },
  ]



export default routes
