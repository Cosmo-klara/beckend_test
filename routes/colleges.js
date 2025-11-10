const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');

function toSafeInt(val, defaultVal = 1, min = 1, max = 1000000) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    const i = Math.floor(n);
    if (i < min) return min;
    if (i > max) return max;
    return i;
}

// GET /api/colleges?page=&pageSize=&province=&is985=&q=
router.get('/', async (req, res) => {
    try {
        const { province, is985 } = req.query;
        const rawQ = (req.query.q || '').toString();

        const page = toSafeInt(req.query.page, 1);
        const pageSize = toSafeInt(req.query.pageSize, 20, 1, 200);
        const offset = (page - 1) * pageSize;

        const escapeLike = (s) => s.replace(/([%_\\])/g, '\\$1');

        const where = [];
        const params = [];
        if (province) { where.push('PROVINCE = ?'); params.push(province); }
        if (typeof is985 !== 'undefined') { where.push('IS_985 = ?'); params.push(Number(is985) ? 1 : 0); }
        if (rawQ.trim()) {
            const q = escapeLike(rawQ.trim());
            where.push('(COLLEGE_NAME LIKE ? ESCAPE \\\\)');
            params.push(`%${q}%`);
        }
        const whereSql = where.length ? ('WHERE ' + where.join(' AND ')) : '';

        const countSql = `SELECT COUNT(*) AS total FROM college_info ${whereSql}`;
        const [countRows] = await db.execute(countSql, params);
        const total = Number(countRows?.[0]?.total || 0);

        // LIMIT/OFFSET 直接使用安全整型内插，避免占位符导致的 mysqld_stmt_execute 错误
        const dataSql = `
            SELECT COLLEGE_CODE, COLLEGE_NAME, IS_985, IS_211, IS_DFC, PROVINCE, CITY_NAME
            FROM college_info
            ${whereSql}
            ORDER BY COLLEGE_CODE ASC
            LIMIT ${pageSize} OFFSET ${offset}
        `;
        const [rows] = await db.execute(dataSql, params);

        return res.json({
            data: rows,
            meta: {
                page,
                pageSize,
                total,
                totalPages: Math.max(1, Math.ceil(total / pageSize)),
                hasNext: offset + rows.length < total
            }
        });
    } catch (err) {
        console.error('colleges.list error', err);
        return res.status(500).json({ error: 'Server error' });
    }
});

router.get('/:collegeCode', async (req, res) => {
    try {
        const collegeCode = parseInt(req.params.collegeCode);
        if (!Number.isFinite(collegeCode)) return res.status(400).json({ error: 'Invalid collegeCode' });
        const [rows] = await db.execute('SELECT * FROM college_info WHERE COLLEGE_CODE = ?', [collegeCode]);
        if (rows.length === 0) return res.status(404).json({ error: 'College not found' });
        return res.json({ data: rows[0] });
    } catch (err) {
        console.error('colleges.get error', err);
        return res.status(500).json({ error: 'Server error' });
    }
});

// 受保护：获取院校历年录取（按省/年过滤）
router.get('/:collegeCode/admissions', authRequired, async (req, res) => {
    try {
        const collegeCode = parseInt(req.params.collegeCode);
        const { province, year } = req.query;
        if (!Number.isFinite(collegeCode)) return res.status(400).json({ error: 'Invalid collegeCode' });

        let where = 'WHERE COLLEGE_CODE = ?';
        const params = [collegeCode];
        if (province) { where += ' AND PROVINCE = ?'; params.push(province); }
        if (year) { where += ' AND ADMISSION_YEAR = ?'; params.push(year); }

        const sql = `SELECT ADMISSION_ID, MAJOR_NAME, TYPE, PROVINCE, ADMISSION_YEAR, MIN_SCORE, MIN_RANK
                FROM college_admission_score ${where} ORDER BY ADMISSION_YEAR DESC`;
        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows });
    } catch (err) {
        console.error('colleges.admissions error', err);
        return res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;

