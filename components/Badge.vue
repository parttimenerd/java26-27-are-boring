<template>
  <div 
    :class="[
      'rounded text-white font-bold inline-block',
      sizeClasses,
      variantClasses
    ]" 
    style="vertical-align: middle"
  >
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'red',
    validator: (value) => ['green', 'blue', 'gray', 'red', 'zinc', 'purple', 'teal', 'orange'].includes(value)
  },
  size: {
    type: String,
    default: 'sm',
    validator: (value) => ['sm', 'lg'].includes(value)
  }
})

const sizeClasses = computed(() => {
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base'
  }
  return sizes[props.size]
})

const variantClasses = computed(() => {
  const variants = {
    green: 'bg-green-600 hover:bg-green-500',
    blue: 'bg-blue-600 hover:bg-blue-500',
    gray: 'bg-gray-600 hover:bg-gray-500',
    red: 'bg-red-600 hover:bg-red-500',
    zinc: 'bg-zinc-500 hover:bg-zinc-400',
    purple: 'bg-purple-600 hover:bg-purple-500',
    teal: 'bg-teal-600 hover:bg-teal-500',
    orange: 'bg-orange-500 hover:bg-orange-400',
  }
  return variants[props.variant]
})
</script>
