<template>
  <div class="map-page">
    <!-- 侧边列表 -->
    <aside class="sidebar">
      <div class="side-header">
        <h2 class="title">地应力测点</h2>
        <el-button type="primary" size="small" @click="showDialog = true">新增测点</el-button>
      </div>
      <ul class="point-list">
        <li v-for="p in stressData" :key="p.id" class="point-item">
          <div class="point-info">
            <strong>{{ p.name }}</strong>
            <span>{{ p.value }} MPa</span>
          </div>
          <el-button type="text" size="small" @click="deletePoint(p.id)">删除</el-button>
        </li>
      </ul>
    </aside>

    <!-- 地图容器 -->
    <div class="map-container" id="map"></div>

    <!-- 新增测点对话框 -->
    <el-dialog v-model="showDialog" title="新增测点" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="测点名称" />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input v-model="form.lat" placeholder="如 39.90" />
        </el-form-item>
        <el-form-item label="经度">
          <el-input v-model="form.lng" placeholder="如 116.40" />
        </el-form-item>
        <el-form-item label="应力(MPa)">
          <el-input v-model="form.value" placeholder="数值" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="addPoint">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

// 静态地应力测试数据
const stressData = ref([
  { id: 1, name: '测量点 A', position: { lat: 39.9042, lng: 116.4074 }, value: 45 },
  { id: 2, name: '测量点 B', position: { lat: 39.9142, lng: 116.4274 }, value: 32 },
  { id: 3, name: '测量点 C', position: { lat: 39.8942, lng: 116.4174 }, value: 67 },
  { id: 4, name: '测量点 D', position: { lat: 39.9042, lng: 116.3974 }, value: 28 },
  { id: 5, name: '测量点 E', position: { lat: 39.9242, lng: 116.4074 }, value: 55 },
])

const showDialog = ref(false)
const form = ref({ name: '', lat: '', lng: '', value: '' })

const API_KEY = 'AIzaSyB0N03KkkrGTlKVD4sROuteZkmmTgbqu7o'

let gMaps = null
const mapInstance = ref(null)
const markers = new Map()

// 根据应力大小返回颜色
function getColor(value) {
  if (value > 70) return '#ef4444' // 高
  if (value > 30) return '#eab308' // 中
  return '#22c55e' // 低
}

function loadGoogleMaps() {
  return new Promise((resolve, reject) => {
    // 若已加载，直接返回
    if (window.google && window.google.maps) {
      resolve(window.google.maps)
      return
    }
    const script = document.createElement('script')
    script.src = `https://maps.googleapis.com/maps/api/js?key=${API_KEY}`
    script.async = true
    script.onerror = reject
    script.onload = () => resolve(window.google.maps)
    document.head.appendChild(script)
  })
}

function createMarker(point) {
  if (!gMaps || !mapInstance.value) return
  const marker = new gMaps.Marker({
    position: point.position,
    map: mapInstance.value,
    title: `${point.name}: ${point.value} MPa`,
    icon: {
      path: gMaps.SymbolPath.CIRCLE,
      scale: 8,
      fillColor: getColor(point.value),
      fillOpacity: 0.9,
      strokeWeight: 1,
      strokeColor: '#ffffff',
    },
  })
  markers.set(point.id, marker)
}

function addPoint() {
  const { name, lat, lng, value } = form.value
  if (!name || !lat || !lng || !value) return
  const point = {
    id: Date.now(),
    name,
    position: { lat: parseFloat(lat), lng: parseFloat(lng) },
    value: parseFloat(value),
  }
  stressData.value.push(point)
  createMarker(point)
  showDialog.value = false
  form.value = { name: '', lat: '', lng: '', value: '' }
}

function deletePoint(id) {
  const idx = stressData.value.findIndex((p) => p.id === id)
  if (idx !== -1) stressData.value.splice(idx, 1)
  const marker = markers.get(id)
  if (marker) {
    marker.setMap(null)
    markers.delete(id)
  }
}

onMounted(async () => {
  try {
    gMaps = await loadGoogleMaps()
    const map = new gMaps.Map(document.getElementById('map'), {
      center: { lat: 39.9042, lng: 116.4074 },
      zoom: 11,
      mapTypeId: gMaps.MapTypeId.SATELLITE,
      styles: [
        {
          featureType: 'all',
          elementType: 'labels',
          stylers: [{ visibility: 'off' }],
        },
      ],
    })
    mapInstance.value = map

    // 初始标记
    stressData.value.forEach((p) => createMarker(p))
  } catch (e) {
    console.error('Google Maps 加载失败', e)
  }
})
</script>

<style scoped>
.map-page {
  display: flex;
  height: calc(100vh - 48px); /* 减去顶部菜单栏高度，大约值，可根据实际调整 */
  gap: 16px;
}
.sidebar {
  width: 240px;
  background: #ffffff;
  border-radius: 8px;
  padding: 16px;
  overflow-y: auto;
}
.side-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 12px;
}
.point-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.point-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #f2f2f2;
  font-size: 14px;
}
.point-info {
  display: flex;
  flex-direction: column;
}
.map-container {
  flex: 1;
  height: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
</style> 