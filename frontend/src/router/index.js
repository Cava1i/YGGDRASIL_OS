import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import CompetitionList from '../views/CompetitionList.vue'
import CompetitionDetail from '../views/CompetitionDetail.vue'
import SubmitTask from '../views/SubmitTask.vue'
import AdminConsole from '../views/AdminConsole.vue'
import TaskDetail from '../views/TaskDetail.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/competitions', name: 'CompetitionList', component: CompetitionList },
  { path: '/competitions/:id', name: 'CompetitionDetail', component: CompetitionDetail },
  { path: '/tasks/:id', name: 'TaskDetail', component: TaskDetail },
  { path: '/submit', name: 'SubmitTask', component: SubmitTask },
  { path: '/admin', name: 'AdminConsole', component: AdminConsole }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
