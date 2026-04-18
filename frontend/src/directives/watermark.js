/** V5.3隐形水印指令 - v-watermark
 *
 *  设计原理:
 *    1. 用Canvas绘制包含当前用户工号的文字，透明度极低(rgba 0,0,0,0.005)
 *    2. 将Canvas转为dataURL，创建全屏覆盖的<div>作为body子元素
 *    3. CSS: pointer-events:none + z-index:9999 + position:fixed + 100vw/100vh
 *    4. 水印层平铺背景图，肉眼几乎不可见
 *    5. 截图后用PS调整色阶/对比度即可溯源到具体工号
 *
 *  安全加固(V5.3):
 *    - MutationObserver监控水印DOM，防止被手动删除或属性篡改
 *    - 用户切换时自动重绘水印
 *
 *  用法: 在App.vue根元素上添加 v-watermark，指令自动读取Pinia store的emp_id
 */

let watermarkEl = null   // 水印覆盖层DOM
let observer = null       // MutationObserver实例
let currentText = ''      // 当前水印文字

/** 用Canvas生成隐形水印图 */
function generateWatermarkUrl(text) {
  const canvas = document.createElement('canvas')
  // 单个水印单元尺寸 — 旋转后需要足够空间
  canvas.width = 320
  canvas.height = 200

  const ctx = canvas.getContext('2d')

  // ── 极低透明度绘制，肉眼不可见，PS调色阶可显 ────────────
  // FIXED in V5.3: 旧版透明度0.01太明显，现降至0.005
  ctx.fillStyle = 'rgba(0, 0, 0, 0.005)'
  ctx.font = '14px monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  // ── 旋转-25度，防止截图后文字被直接OCR拼接 ────────────────
  ctx.translate(160, 100)
  ctx.rotate((-25 * Math.PI) / 180)

  // ── 主水印: 工号 ────────────────────────────────────────────
  ctx.fillText(text, 0, -8)

  // ── 辅助水印: 时间戳+工号组合，增加溯源信息密度 ────────────
  const ts = new Date().toISOString().slice(0, 10)
  ctx.fillText(`${text} | ${ts}`, 0, 10)

  return canvas.toDataURL('image/png')
}

/** 创建水印覆盖层DOM */
function createWatermarkOverlay(text) {
  const url = generateWatermarkUrl(text)

  const el = document.createElement('div')
  el.id = '__v_watermark__'
  el.style.cssText = [
    'position: fixed',
    'top: 0',
    'left: 0',
    'width: 100vw',
    'height: 100vh',
    'z-index: 9999',
    'pointer-events: none',
    `background-image: url(${url})`,
    'background-repeat: repeat',
    'background-size: 320px 200px',
  ].join(';')

  return el
}

/** 启动MutationObserver，防止水印DOM被删除或篡改 */
function startGuard() {
  // V5.3安全加固: 监控水印元素，一旦被移除/修改立即重建
  if (observer) observer.disconnect()

  observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      // 水印元素被删除 — 立即重建
      if (m.type === 'childList' && m.removedNodes.length) {
        for (const node of m.removedNodes) {
          if (node === watermarkEl || node.id === '__v_watermark__') {
            rebuildWatermark(currentText)
            return
          }
        }
      }
      // 水印元素属性被篡改(如z-index改为-1、display:none) — 立即重建
      if (m.type === 'attributes' && m.target === watermarkEl) {
        rebuildWatermark(currentText)
        return
      }
    }
  })

  // 同时监控body的childList(防止整层被remove)和水印自身的attributes
  observer.observe(document.body, { childList: true })
  if (watermarkEl) {
    observer.observe(watermarkEl, { attributes: true })
  }
}

/** 重建水印(防篡改或更新文字时调用) */
function rebuildWatermark(text) {
  // 移除旧水印
  const old = document.getElementById('__v_watermark__') || watermarkEl
  if (old && old.parentNode) old.parentNode.removeChild(old)

  // 重建
  watermarkEl = createWatermarkOverlay(text)
  document.body.appendChild(watermarkEl)
  currentText = text

  // 重新启动监控
  startGuard()
}

/** Vue自定义指令 */
export const vWatermark = {
  mounted(el, binding) {
    const text = binding.value || ''
    if (!text) return
    rebuildWatermark(text)
  },

  updated(el, binding) {
    const text = binding.value || ''
    if (text === currentText) return  // 文字未变，无需重绘
    rebuildWatermark(text)
  },

  unmounted() {
    // 清理
    if (observer) observer.disconnect()
    observer = null
    const el = document.getElementById('__v_watermark__') || watermarkEl
    if (el && el.parentNode) el.parentNode.removeChild(el)
    watermarkEl = null
    currentText = ''
  },
}

/** 全局函数: 可在任意位置手动触发水印更新(如用户切换后) */
export function updateWatermark(text) {
  if (!text) return
  rebuildWatermark(text)
}