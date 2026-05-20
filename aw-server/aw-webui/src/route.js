import Vue from 'vue';
import VueRouter from 'vue-router';

const Chronio = () => import('./views/activity/Chronio.vue');

Vue.use(VueRouter);

const router = new VueRouter({
  routes: [
    { path: '/chronio', component: Chronio, meta: { fullContainer: true, noShell: true } },
    // Redirect all legacy ActivityWatch routes to Chronio
    { path: '/', redirect: '/chronio' },
    { path: '/home', redirect: '/chronio' },
    { path: '/activity/:host/:periodLength?/:date?', redirect: '/chronio' },
    { path: '/buckets', redirect: '/chronio' },
    { path: '/buckets/:id', redirect: '/chronio' },
    { path: '/timeline', redirect: '/chronio' },
    { path: '/trends', redirect: '/chronio' },
    { path: '/trends/:host', redirect: '/chronio' },
    { path: '/report', redirect: '/chronio' },
    { path: '/query', redirect: '/chronio' },
    { path: '/alerts', redirect: '/chronio' },
    { path: '/timespiral', redirect: '/chronio' },
    { path: '/settings', redirect: '/chronio' },
    { path: '/settings/category-builder', redirect: '/chronio' },
    { path: '/stopwatch', redirect: '/chronio' },
    { path: '/search', redirect: '/chronio' },
    { path: '/graph', redirect: '/chronio' },
    { path: '/dev', redirect: '/chronio' },
    { path: '*', redirect: '/chronio' },
  ],
});

export default router;
