// routes/colleges.js
const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');

// 安全整数转换
function toSafeInt(val, defaultVal = 1, min = 1, max = 1000000) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    const i = Math.floor(n);
    if (i < min) return min;
    if (i > max) return max;
    return i;
}

// 列表接口：支持 q(province/name模糊)，province, is985, is211, page, pageSize
router.get('/', async (req, res) => {
    try {
        const q = typeof req.query.q === 'string' ? req.query.q.trim() : '';
        const province = typeof req.query.province === 'string' && req.query.province.trim() ? req.query.province.trim() : null;
        const is985 = req.query.is985 != null ? (req.query.is985 === '1' || req.query.is985 === 'true' || req.query.is985 === 1) : null;
        const is211 = req.query.is211 != null ? (req.query.is211 === '1' || req.query.is211 === 'true' || req.query.is211 === 1) : null;

        const page = toSafeInt(req.query.page, 1, 1, 1000000);
        const pageSize = toSafeInt(req.query.pageSize, 20, 1, 200);
        const offset = (page - 1) * pageSize;

        const whereParts = [];
        const params = [];

        if (province) {
            whereParts.push('PROVINCE = ?');
            params.push(province);
        }
        if (is985 !== null) {
            // 表里用 TINYINT(1) 存 0/1
            whereParts.push('IS_985 = ?');
            params.push(is985 ? 1 : 0);
        }
        if (is211 !== null) {
            whereParts.push('IS_211 = ?');
            params.push(is211 ? 1 : 0);
        }
        if (q) {
            // 限制 q 长度以防超长参数
            const safeQ = q.length > 200 ? q.slice(0, 200) : q;
            // 这里直接使用 LIKE，不使用 ESCAPE（更简单、兼容）
            whereParts.push('(COLLEGE_NAME LIKE ? OR BASE_INTRO LIKE ?)');
            params.push(`%${safeQ}%`, `%${safeQ}%`);
        }

        const whereSql = whereParts.length ? ('WHERE ' + whereParts.join(' AND ')) : '';

        // 先取总数（注意：COUNT 使用同样的 params）
        const countSql = `SELECT COUNT(*) AS total FROM college_info ${whereSql}`;
        // SELECT 主体（把 LIMIT/OFFSET 的整数直接拼入 SQL）
        const selectSql = `SELECT COLLEGE_CODE, COLLEGE_NAME, IS_985, IS_211, IS_DFC, PROVINCE, CITY_NAME, BASE_INTRO
                    FROM college_info
                    ${whereSql}
                    ORDER BY COLLEGE_NAME
                    LIMIT ${pageSize} OFFSET ${offset}`;


        const [countRows] = await db.execute(countSql, params);
        const total = Array.isArray(countRows) && countRows.length ? Number(countRows[0].total) : 0;

        const [rows] = await db.execute(selectSql, params);
        return res.json({ data: rows, meta: { page, pageSize, total } });
    } catch (err) {
        console.error('colleges.list error', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

router.get('/:collegeCode', async (req, res) => {
    try {
        const code = req.params.collegeCode;
        // basic validation
        if (!/^\d+$/.test(String(code))) return res.status(400).json({ error: 'Invalid college code' });
        const [rows] = await db.execute('SELECT * FROM college_info WHERE COLLEGE_CODE = ?', [code]);
        if (!rows || rows.length === 0) return res.status(404).json({ error: 'College not found' });
        return res.json({ data: rows[0] });
    } catch (err) {
        console.error('colleges.get error', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});


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
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

module.exports = router;
