const express = require('express');
const router = express.Router();
const db = require('../db');

// 将值强制转换为安全的整数，并加上上/下限
function toSafeInt(val, defaultVal = 1, min = 1, max = 1000) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    const i = Math.floor(n);
    if (i < min) return min;
    if (i > max) return max;
    return i;
}

// 模糊查询或列表
router.get('/', async (req, res) => {
    try {
        const q = typeof req.query.q === 'string' ? req.query.q.trim() : '';
        const page = toSafeInt(req.query.page, 1, 1, 1000000);
        const pageSize = toSafeInt(req.query.pageSize, 30, 1, 200);
        const offset = (page - 1) * pageSize; // 计算偏移量

        const params = [];
        let where = '';
        if (q) {
            // 限制查询词最大长度为 100 防止过长查询
            const safeQ = q.length > 100 ? q.slice(0, 100) : q;
            where = 'WHERE MAJOR_NAME LIKE ?'; // 模糊查询 MAJOR_NAME
            params.push(`%${safeQ}%`);
        }

        const sql = `SELECT MAJOR_ID, MAJOR_NAME, MAJOR_TYPE, BASE_INTRO
                    FROM major_info
                    ${where}
                    ORDER BY MAJOR_NAME
                    LIMIT ${pageSize} OFFSET ${offset}`;

        const [rows] = await db.execute(sql, params);

        return res.json({ data: rows, meta: { page, pageSize, q: q || null } });
    } catch (err) {
        console.error('Error in /api/majors', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

// 估计用不到了，没数据
router.get('/:majorId', async (req, res) => {
    try {
        // 强制将 majorId 转为整数
        const majorId = parseInt(req.params.majorId, 10);
        if (!Number.isFinite(majorId)) return res.status(400).json({ error: 'Invalid majorId' });

        const [rows] = await db.execute(
            'SELECT MAJOR_ID, MAJOR_NAME, MAJOR_TYPE, BASE_INTRO FROM major_info WHERE MAJOR_ID = ?',
            [majorId]
        );

        if (rows.length === 0) return res.status(404).json({ error: 'Major not found' });

        return res.json({ data: rows[0] });
    } catch (err) {
        console.error('Error in GET /api/majors/:majorId', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

module.exports = router;
