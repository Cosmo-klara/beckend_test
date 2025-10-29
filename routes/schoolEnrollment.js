const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');

// 获取某高中升学记录（按毕业年份过滤）
router.get('/', authRequired, async (req, res) => {
    try {
        const { schoolId, graduationYear } = req.query;
        if (!schoolId) return res.status(400).json({ error: 'schoolId required' });
        let sql = 'SELECT * FROM school_enrollment WHERE SCHOOL_ID = ?';
        const params = [schoolId];
        if (graduationYear) { sql += ' AND GRADUATION_YEAR = ?'; params.push(graduationYear); }
        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows });
    } catch (err) {
        console.error(err);
        return res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;
