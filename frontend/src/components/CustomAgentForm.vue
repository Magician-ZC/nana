<template>
  <div class="custom-agent-form">
    <div class="form-overlay" @click="$emit('close')"></div>
    <div class="form-content">
      <h3>{{ props.editAgent ? '编辑角色' : '创建自定义角色' }}</h3>
      <div class="form-group">
        <label>角色名称</label>
        <input v-model="form.name" type="text" placeholder="请输入角色名称">
      </div>
      <div class="form-group">
        <label>角色特点</label>
        <textarea v-model="form.description" placeholder="请输入角色特点描述"></textarea>
      </div>
      <div class="form-group">
        <label>选择形象</label>
        <select v-model="form.model">
          <option value="nanaA">娜娜A - 傲娇猫娘</option>
          <option value="nanaB">娜娜B - 知性大姐姐</option>
          <option value="nanaC">娜娜C - 元气少女</option>
        </select>
      </div>
      <div class="form-group">
        <label>性格特征</label>
        <textarea v-model="form.personality" placeholder="请输入性格特征"></textarea>
      </div>
      <div class="form-group">
        <label>兴趣爱好</label>
        <textarea v-model="form.interests" placeholder="请输入兴趣爱好"></textarea>
      </div>
      <div class="form-group">
        <label>生活习惯</label>
        <textarea v-model="form.lifestyle" placeholder="请输入生活习惯"></textarea>
      </div>
      <div class="form-group">
        <label>价值观</label>
        <textarea v-model="form.values" placeholder="请输入价值观"></textarea>
      </div>
      <div class="form-actions">
        <button class="cancel-btn" @click="$emit('close')">取消</button>
        <button class="save-btn" @click="handleSave">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, onMounted } from 'vue'

const props = defineProps({
  editAgent: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'save'])

const form = ref({
  name: '',
  description: '',
  model: 'nanaA',
  personality: '',
  interests: '',
  lifestyle: '',
  values: ''
})

// 组件挂载时，如果是编辑模式，则填充表单数据
onMounted(() => {
  if (props.editAgent) {
    form.value = {
      name: props.editAgent.name || '',
      description: props.editAgent.description || '',
      model: props.editAgent.model || 'nanaA',
      personality: props.editAgent.personality || '',
      interests: props.editAgent.interests || '',
      lifestyle: props.editAgent.lifestyle || '',
      values: props.editAgent.values || ''
    }
  }
})

const handleSave = () => {
  if (!form.value.name || !form.value.description) {
    alert('请填写角色名称和特点')
    return
  }
  emit('save', { ...form.value })
}
</script>

<style scoped>
.custom-agent-form {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.form-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
}

.form-content {
  position: relative;
  background-color: #fff;
  padding: 20px;
  border-radius: 10px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

h3 {
  margin: 0 0 20px 0;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  color: #666;
}

input, textarea, select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

textarea {
  height: 100px;
  resize: vertical;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

button {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.cancel-btn {
  background-color: #f5f5f5;
  color: #666;
}

.save-btn {
  background-color: #4CAF50;
  color: white;
}

button:hover {
  opacity: 0.9;
}
</style> 