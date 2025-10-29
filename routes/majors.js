const express = require('express');
const router = express.Router();
const db = require('../db');

// 把值强转为安全的正整数，带上上/下限
function toSafeInt(val, defaultVal = 1, min = 1, max = 1000) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    const i = Math.floor(n);
    if (i < min) return min;
    if (i > max) return max;
    return i;
}

// 列表或模糊搜索
router.get('/', async (req, res) => {
    try {
        const q = typeof req.query.q === 'string' ? req.query.q.trim() : '';
        const page = toSafeInt(req.query.page, 1, 1, 1000000);
        const pageSize = toSafeInt(req.query.pageSize, 30, 1, 200); // 限制 pageSize 最大 200
        const offset = (page - 1) * pageSize;

        // 构建 WHERE 子句与参数（只对 WHERE 使用占位符）
        const params = [];
        let where = '';
        if (q) {
            // 为防止过长的查询词，截断（例如 100 字符）
            const safeQ = q.length > 100 ? q.slice(0, 100) : q;
            where = 'WHERE MAJOR_NAME LIKE ? OR MAJOR_CODE LIKE ?';
            params.push(`%${safeQ}%`, `%${safeQ}%`);
        }

        // 某些 MySQL 驱动/服务器在预处理语句中对 LIMIT/ OFFSET 的占位符支持不稳定
        // LIMIT 与 OFFSET ：把经过 toSafeInt 校验后的整数直接拼接进 SQL
        // 防止某些环境下的占位符问题，有可能引起数据库报错，反正我这边是这样，所以得配合一个toSafeInt
        const sql = `SELECT MAJOR_ID, MAJOR_CODE, MAJOR_NAME, MAJOR_TYPE, BASE_INTRO
                FROM major_info
                ${where}
                ORDER BY MAJOR_CODE
                LIMIT ${pageSize} OFFSET ${offset}`;


        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows, meta: { page, pageSize, q: q || null } });
    } catch (err) {
        console.error('Error in /api/majors', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

router.get('/:majorId', async (req, res) => {
    try {
        const majorId = req.params.majorId;
        const [rows] = await db.execute('SELECT MAJOR_ID, MAJOR_CODE, MAJOR_NAME, MAJOR_TYPE, BASE_INTRO FROM major_info WHERE MAJOR_ID = ?', [majorId]);
        if (rows.length === 0) return res.status(404).json({ error: 'Major not found' });
        return res.json({ data: rows[0] });
    } catch (err) {
        console.error('Error in GET /api/majors/:majorId', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

module.exports = router;
