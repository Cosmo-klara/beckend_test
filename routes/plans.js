const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');
const { body, validationResult } = require('express-validator');

// 将值转换为安全的整数
function toSafeInt(val, defaultVal = null) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    return Math.floor(n);
}

// GET /api/plans?collegeCode=&year=&page=&pageSize=
router.get('/', async (req, res) => {
    try {
        const { collegeCode, year } = req.query;
        const page = toSafeInt(req.query.page, 1) || 1;
        const pageSize = Math.min(200, Math.max(1, toSafeInt(req.query.pageSize, 20) || 20));
        const offset = (page - 1) * pageSize;

        const where = [];
        const params = [];

        // 处理院校编码过滤条件
        if (collegeCode) {
            where.push('COLLEGE_CODE = ?');
            params.push(parseInt(collegeCode));
        }

        // 处理招生年份过滤条件
        if (year) {
            where.push('ADMISSION_YEAR = ?');
            params.push(parseInt(year));
        }

        // 构建 WHERE SQL 语句
        const whereSql = where.length ? 'WHERE ' + where.join(' AND ') : '';

        // 查询 SQL 语句
        const sql = `SELECT PLAN_ID, COLLEGE_CODE, MAJOR_NAME, PROVINCE, ADMISSION_YEAR, PLAN_COUNT, DESCRIPTION
                    FROM college_plan ${whereSql}
                    ORDER BY ADMISSION_YEAR DESC
                    LIMIT ${pageSize} OFFSET ${offset}`;

        // 执行查询
        const [rows] = await db.execute(sql, params);

        // 返回结果
        return res.json({ data: rows, meta: { page, pageSize } });
    } catch (err) {
        console.error('plans.list error', err);
        return res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;
