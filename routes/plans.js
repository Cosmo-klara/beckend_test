// routes/plans.js
const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');
const { body, validationResult } = require('express-validator');

// 列出计划（按院校/专业/年份过滤）
router.get('/', async (req, res) => {
    try {
        const { collegeId, majorId, year } = req.query;
        let where = [];
        let params = [];
        if (collegeId) { where.push('COLLEGE_ID = ?'); params.push(collegeId); }
        if (majorId) { where.push('MAJOR_ID = ?'); params.push(majorId); }
        if (year) { where.push('ADMISSION_YEAR = ?'); params.push(year); }
        const whereSql = where.length ? 'WHERE ' + where.join(' AND ') : '';
        const sql = `SELECT * FROM college_plan ${whereSql} ORDER BY ADMISSION_YEAR DESC`;
        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows });
    } catch (err) {
        console.error(err);
        return res.status(500).json({ error: 'Server error' });
    }
});

// 创建计划（示例，需登录）
router.post('/',
    authRequired,
    body('collegeId').notEmpty(),
    body('majorId').notEmpty(),
    body('admissionYear').isInt(),
    body('planCount').isInt(),
    async (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
        try {
            const { collegeId, majorId, admissionYear, planCount, description } = req.body;
            const sql = `INSERT INTO college_plan (COLLEGE_ID, MAJOR_ID, PROVINCE, ADMISSION_YEAR, PLAN_COUNT, DESCRIPTION)
                VALUES (?, ?, ?, ?, ?, ?)`;
            // PROVINCE 这里示例用用户省份或需要前端传入
            const province = req.user && req.user.province ? req.user.province : null;
            const [result] = await db.execute(sql, [collegeId, majorId, province, admissionYear, planCount, description || null]);
            return res.json({ message: 'Plan created', insertId: result.insertId });
        } catch (err) {
            console.error(err);
            return res.status(500).json({ error: 'Server error' });
        }
    }
);

module.exports = router;
