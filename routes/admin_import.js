const express = require('express')
const { spawn } = require('child_process')
const path = require('path')

const router = express.Router()

// 建议把脚本复制到后端工程：scripts/information_search/import_data.py
// 也可以先用你现有路径，后续再迁移
const SCRIPT_PATH = path.join(__dirname, '..', 'scripts', 'information_search', 'import_data.py')
// 如果暂时未复制，可改为绝对路径：
// const SCRIPT_PATH = 'e:\\Extel\\work\\Class\\information_search\\import_data.py'

const state = {
    enabled: false,
    time: '02:00', // 每天 02:00 运行
    datasets: [], // 例如 ['majors','colleges','enrollment']
    running: false,
    lastRun: null,
    lastExitCode: null,
    lastError: null,
    lastLogs: []
}

function runImport(datasets = []) {
    if (state.running) return Promise.reject(new Error('job_running'))
    state.running = true
    state.lastError = null
    state.lastLogs = []
    return new Promise((resolve, reject) => {
        const args = [SCRIPT_PATH]
        // 如脚本支持参数，这里可加入：args.push('--datasets', datasets.join(','))
        const p = spawn('python', args, { env: { ...process.env } })
        p.stdout.on('data', (d) => state.lastLogs.push(d.toString()))
        p.stderr.on('data', (d) => state.lastLogs.push(d.toString()))
        p.on('error', (err) => {
            state.running = false
            state.lastRun = new Date().toISOString()
            state.lastExitCode = -1
            state.lastError = String(err)
            reject(err)
        })
        p.on('close', (code) => {
            state.running = false
            state.lastRun = new Date().toISOString()
            state.lastExitCode = code
            if (code === 0) resolve(code)
            else {
                state.lastError = `exit_code_${code}`
                reject(new Error(`exit_code_${code}`))
            }
        })
    })
}

// 简单调度：每 30 秒检查一次
setInterval(() => {
    if (!state.enabled || state.running) return
    const now = new Date()
    const hh = String(now.getHours()).padStart(2, '0')
    const mm = String(now.getMinutes()).padStart(2, '0')
    const nowStr = `${hh}:${mm}`
    // 只在第一次匹配这一分钟触发一次
    const last = state.lastRun ? new Date(state.lastRun) : null
    const sameDay = last && last.toDateString() === now.toDateString()
    if (!sameDay && nowStr === state.time) {
        runImport(state.datasets).catch(() => { })
    }
}, 30_000)

function requireAuth(req) {
    const auth = req.headers['authorization'] || ''
    return auth.startsWith('Bearer ')
}

router.get('/status', (req, res) => {
    res.json({
        enabled: state.enabled,
        time: state.time,
        datasets: state.datasets,
        running: state.running,
        lastRun: state.lastRun,
        lastExitCode: state.lastExitCode,
        lastError: state.lastError,
        logsTail: state.lastLogs.slice(-10)
    })
})

router.post('/run', async (req, res) => {
    if (!requireAuth(req)) return res.status(401).json({ error: 'unauthorized' })
    const datasets = Array.isArray(req.body?.datasets) ? req.body.datasets : []
    try {
        await runImport(datasets)
        res.json({ ok: true, lastRun: state.lastRun })
    } catch (e) {
        res.status(500).json({ error: 'run_failed', detail: String(e), lastRun: state.lastRun })
    }
})

router.post('/schedule', (req, res) => {
    if (!requireAuth(req)) return res.status(401).json({ error: 'unauthorized' })
    const time = (req.body?.time || '02:00').toString()
    const datasets = Array.isArray(req.body?.datasets) ? req.body.datasets : []
    if (!/^\d{2}:\d{2}$/.test(time)) return res.status(400).json({ error: 'invalid_time' })
    state.enabled = true
    state.time = time
    state.datasets = datasets
    res.json({ ok: true, enabled: state.enabled, time: state.time, datasets: state.datasets })
})

router.delete('/schedule', (req, res) => {
    if (!requireAuth(req)) return res.status(401).json({ error: 'unauthorized' })
    state.enabled = false
    res.json({ ok: true, enabled: false })
})

module.exports = router