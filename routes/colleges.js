const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');

// 把值强转为安全的正整数，带上上/下限
function toSafeInt(val, defaultVal, min = 1, max = 1000) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    const i = Math.floor(n);
    if (i < min) return min;
    if (i > max) return max;
    return i;
}

// 获取院校列表（支持分页与简单过滤）
router.get('/', async (req, res) => {
    try {
        const { province, level, q } = req.query;
        // page 和 pageSize 做严格校验后用于计算 offset
        const page = toSafeInt(req.query.page ?? 1, 1, 1, 1000000);
        const pageSize = toSafeInt(req.query.pageSize ?? 20, 20, 1, 200); // 限制最大 pageSize 为 200
        const offset = (page - 1) * pageSize;

        // 构建 WHERE 子句与参数（只放可用于 WHERE 的占位符）
        const whereClauses = [];
        const params = [];
        if (province) { whereClauses.push('PROVINCE = ?'); params.push(province); }
        if (level) { whereClauses.push('COLLEGE_LEVEL = ?'); params.push(level); }
        if (q) { whereClauses.push('COLLEGE_NAME LIKE ?'); params.push(`%${q}%`); }

        const where = whereClauses.length ? `WHERE ${whereClauses.join(' AND ')}` : '';

        const sql = `SELECT COLLEGE_ID, COLLEGE_CODE, COLLEGE_NAME, COLLEGE_LEVEL, PROVINCE, CITY_NAME, COLLEGE_TYPE, WEBSITE
                FROM college_info ${where} ORDER BY COLLEGE_NAME LIMIT ${pageSize} OFFSET ${offset}`;

        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows, meta: { page, pageSize } });
    } catch (err) {
        console.error('Error in /api/colleges', err);
        return res.status(500).json({ error: 'Server error' });
    }
});

router.get('/:collegeId', async (req, res) => {
    const collegeId = req.params.collegeId;
    try {
        const [rows] = await db.execute('SELECT * FROM college_info WHERE COLLEGE_ID = ?', [collegeId]);
        if (rows.length === 0) return res.status(404).json({ error: 'College not found' });
        return res.json({ data: rows[0] });
    } catch (err) {
        console.error(err);
        return res.status(500).json({ error: 'Server error' });
    }
});

/**
 * GET /:collegeId/admissions （需要认证）
 * 获取指定院校的招生分数/位次等历史记录，支持省份与年份过滤。
 *
 * 中间件：
 * - authRequired 保护该路由，未认证访问将被拒绝
 * Path 参数：
 * - collegeId {string|number} 院校唯一标识。
 * Query 参数（可选）：
 * - province {string} 按省份过滤（精确匹配）。
 * - year {number} 按招生年份过滤（精确匹配）。
 *
 * 返回：
 * - 200 OK: { data: AdmissionRow[] }，按 ADMISSION_YEAR 倒序排列。
 * - 500 Server Error: { error: 'Server error' }
 */
router.get('/:collegeId/admissions', authRequired, async (req, res) => {
    const collegeId = req.params.collegeId;
    const { province, year } = req.query;
    try {
        let where = 'WHERE COLLEGE_ID = ?';
        const params = [collegeId];
        if (province) { where += ' AND PROVINCE = ?'; params.push(province); }
        if (year) { where += ' AND ADMISSION_YEAR = ?'; params.push(year); }

        const sql = `SELECT ADMISSION_ID, MAJOR_ID, PROVINCE, ADMISSION_YEAR, MIN_SCORE, MIN_RANK, ENROLLMENT_COUNT
                FROM college_admission_score ${where} ORDER BY ADMISSION_YEAR DESC`;
        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows });
    } catch (err) {
        console.error(err);
        return res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;
