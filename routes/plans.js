const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');
const { body, validationResult } = require('express-validator');

function toSafeInt(val, defaultVal = null) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    return Math.floor(n);
}

// GET /api/plans?collegeCode=&majorId=&year=&page=&pageSize=
router.get('/', async (req, res) => {
    try {
        const { collegeCode, majorId, year } = req.query;
        const page = toSafeInt(req.query.page, 1) || 1;
        const pageSize = Math.min(200, Math.max(1, toSafeInt(req.query.pageSize, 20) || 20));
        const offset = (page - 1) * pageSize;

        const where = [];
        const params = [];
        if (collegeCode) { where.push('COLLEGE_CODE = ?'); params.push(parseInt(collegeCode)); }
        if (majorId) { where.push('MAJOR_ID = ?'); params.push(parseInt(majorId)); }
        if (year) { where.push('ADMISSION_YEAR = ?'); params.push(parseInt(year)); }
        const whereSql = where.length ? 'WHERE ' + where.join(' AND ') : '';

        const sql = `SELECT PLAN_ID, COLLEGE_CODE, MAJOR_ID, PROVINCE, ADMISSION_YEAR, PLAN_COUNT, DESCRIPTION
                FROM college_plan ${whereSql}
                ORDER BY ADMISSION_YEAR DESC
                LIMIT ${pageSize} OFFSET ${offset}`;
        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows, meta: { page, pageSize } });
    } catch (err) {
        console.error('plans.list error', err);
        return res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;
