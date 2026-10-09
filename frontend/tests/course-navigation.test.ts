import { beforeEach, expect, it, vi } from 'vitest'
vi.mock('vue-router', async (original) => {
  const actual = await original<typeof import('vue-router')>()
  return { ...actual, createWebHistory: actual.createMemoryHistory }
})
import { router } from '../src/router'
import { pinia } from '../src/stores'
import { useAuthStore } from '../src/stores/auth'
beforeEach(() => {
  const auth = useAuthStore(pinia)
  auth.$reset()
  vi.spyOn(auth, 'restore').mockResolvedValue(undefined)
})
it('课程路由注册、解析并加载真实课程学习页面', async () => {
  const route = router.getRoutes().find(r => r.name === 'course-learning')!
  expect(route.path).toBe('/resources/:id/learn')
  expect(route.meta.requiresAuth).toBe(true)
  expect(router.resolve({ name: 'course-learning', params: { id: 1068 } }).href).toBe('/resources/1068/learn')
  const load = route.components!.default as () => Promise<{ default: { __name: string } }>
  expect((await load()).default.__name).toBe('CourseLearningView')
}, 30000)
it('已登录用户从资源详情进入课程学习URL', async () => {
  const auth = useAuthStore(pinia)
  auth.token = 'test-only-token'
  auth.expiresAt = Date.now() + 60000
  auth.user = { id: 1, username: 'test', role: 'learner' } as typeof auth.user
  await router.push('/resources/1068')
  await router.push({ name: 'course-learning', params: { id: 1068 } })
  expect(router.currentRoute.value.path).toBe('/resources/1068/learn')
  expect(router.currentRoute.value.name).toBe('course-learning')
})
it('未登录用户访问课程学习仍被登录保护', async () => {
  await router.push('/resources/1069/learn')
  expect(router.currentRoute.value.name).toBe('login')
})

it('课程管理真实路由按管理员角色保护并加载正式页面', async () => {
  const route = router.getRoutes().find(r=>r.name==='admin-courses')!
  expect(route.path).toBe('/admin/courses');expect(route.meta.roles).toEqual(['admin'])
  const load=route.components!.default as ()=>Promise<{default:{__name:string}}>
  expect((await load()).default.__name).toBe('AdminCoursesView')
  const auth=useAuthStore(pinia);auth.token='test-only-token';auth.expiresAt=Date.now()+60000
  auth.user={id:1,username:'fixture',role:'learner'} as typeof auth.user
  await router.push('/admin/courses');expect(router.currentRoute.value.name).toBe('forbidden')
  auth.user.role='admin';await router.push('/admin/courses');expect(router.currentRoute.value.name).toBe('admin-courses')
  auth.$reset();await router.push('/');await router.push('/admin/courses');expect(router.currentRoute.value.name).toBe('login')
},30000)
it.each([
  ['admin-course-create','/admin/courses/new','AdminCourseEditView'],
  ['admin-course-edit','/admin/courses/1071/edit','AdminCourseEditView'],
  ['admin-course-chapters','/admin/courses/1071/chapters','AdminChapterListView'],
  ['admin-chapter-create','/admin/courses/1071/chapters/new','AdminChapterEditView'],
  ['admin-chapter-edit','/admin/courses/1071/chapters/54/edit','AdminChapterEditView'],
])('管理子页面%s注册真实组件并保持权限',async(name,path,component)=>{
  const route=router.getRoutes().find(r=>r.name===name)!
  expect(route.meta.requiresAuth).toBe(true);expect(route.meta.roles).toEqual(['admin'])
  expect(router.resolve(path).name).toBe(name)
  const load=route.components!.default as ()=>Promise<{default:{__name:string}}>
  expect((await load()).default.__name).toBe(component)
  const auth=useAuthStore(pinia);auth.token='test-only-token';auth.expiresAt=Date.now()+60000
  auth.user={id:1,username:'fixture',role:'learner'} as typeof auth.user
  await router.push(path);expect(router.currentRoute.value.name).toBe('forbidden')
  auth.user.role='admin';await router.push(path);expect(router.currentRoute.value.name).toBe(name)
  auth.$reset();await router.push('/');await router.push(path);expect(router.currentRoute.value.name).toBe('login')
},30000)
