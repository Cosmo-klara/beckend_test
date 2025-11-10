// routes/schoolEnrollment.js
const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');

// 安全整数转换
function toSafeInt(val, defaultVal = null) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    return Math.floor(n);
}

// GET /api/school-enrollment?schoolName=xxx&graduationYear=2024&page=1&pageSize=20
// 或 GET /api/school-enrollment?schoolEnrollmentId=123
router.get('/', authRequired, async (req, res) => {
    try {
        const { schoolEnrollmentId, schoolName, graduationYear } = req.query;
        const page = toSafeInt(req.query.page, 1) || 1;
        const pageSize = Math.min(200, Math.max(1, toSafeInt(req.query.pageSize, 20) || 20));
        const offset = (page - 1) * pageSize;

        // 优先按 schoolEnrollmentId（主键）查询
        if (schoolEnrollmentId) {
            const id = toSafeInt(schoolEnrollmentId);
            if (!id) return res.status(400).json({ error: 'Invalid schoolEnrollmentId' });
            const [rows] = await db.execute(
                'SELECT * FROM school_enrollment WHERE SCHOOL_ENROLLMENT_ID = ?',
                [id]
            );
            if (rows.length === 0) return res.status(404).json({ error: 'Record not found' });
            return res.json({ data: rows[0] });
        }

        // 否则按学校名（COLLEGE_NAME）与可选的 graduationYear 查询，支持分页
        if (!schoolName) {
            return res.status(400).json({ error: 'Either schoolEnrollmentId or schoolName is required' });
        }

        // 限制长度并防止超长字符串
        const safeSchoolName = String(schoolName).trim().slice(0, 200);
        const params = [safeSchoolName];
        let where = 'WHERE COLLEGE_NAME = ?';

        if (graduationYear) {
            const y = toSafeInt(graduationYear);
            if (!y) return res.status(400).json({ error: 'Invalid graduationYear' });
            where += ' AND GRADUATION_YEAR = ?';
            params.push(y);
        }

        // 带分页
        const sql = `SELECT SCHOOL_ENROLLMENT_ID, COLLEGE_NAME, GRADUATION_YEAR, ADMISSION_COUNT, MIN_SCORE, MIN_RANK
                FROM school_enrollment
                ${where}
                ORDER BY GRADUATION_YEAR DESC
                LIMIT ${pageSize} OFFSET ${offset}`;
        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows, meta: { page, pageSize } });
    } catch (err) {
        console.error('schoolEnrollment.list error', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

module.exports = router;
