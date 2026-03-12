import { ref, onMounted } from 'vue'

export function useDmmsData(endpoint, fallback = null) {
  const data = ref(fallback)
  const loading = ref(false)
  const error = ref(null)
  const isLive = ref(false)

  async function load() {
    if (typeof window === 'undefined') return  // SSR guard
    loading.value = true
    try {
      const res = await fetch(`/_dmms/${endpoint}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      data.value = await res.json()
      isLive.value = true
    } catch (e) {
      error.value = e.message
      // data.value stays at fallback
    } finally {
      loading.value = false
    }
  }

  onMounted(load)
  return { data, loading, error, isLive, reload: load }
}
