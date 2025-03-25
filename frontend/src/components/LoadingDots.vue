<template>
  <span class="loading-dots">{{ dots }}</span>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const dots = ref('')
let interval = null

onMounted(() => {
  interval = setInterval(() => {
    dots.value = dots.value.length >= 3 ? '' : dots.value + '.'
  }, 500)
})

onBeforeUnmount(() => {
  if (interval) {
    clearInterval(interval)
  }
})
</script>

<style scoped>
.loading-dots {
  display: inline-block;
  min-width: 20px;
}
</style> 