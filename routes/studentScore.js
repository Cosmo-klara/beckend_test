// routes/studentScore.js
const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');
const { body, validationResult } = require('express-validator');

// 提交成绩（受保护，仅本人或管理员）
// 注意：表中 TOTAL_SCORE 为 DECIMAL(3,0)，我们使用整数校验 isInt
router.post('/',
    authRequired,
    body('studentId').isInt().withMessage('studentId must be integer'),
    body('examYear').isInt().withMessage('examYear must be integer'),
    body('province').isLength({ min: 1 }).withMessage('province required'),
    body('totalScore').isInt().withMessage('totalScore must be integer'),
    body('rankInProvince').optional().isInt().withMessage('rankInProvince must be integer'),
    async (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

        const studentId = Number(req.body.studentId);
        const { examYear, province, totalScore } = req.body;
        const rankInProvince = req.body.rankInProvince ? Number(req.body.rankInProvince) : null;

        if (req.user && req.user.userId && Number(req.user.userId) !== studentId) {
            return res.status(403).json({ error: 'Cannot submit score for other user' });
        }

        try {
            const sql = `INSERT INTO student_score (STUDENT_ID, EXAM_YEAR, PROVINCE, TOTAL_SCORE, RANK_IN_PROVINCE)
                    VALUES (?, ?, ?, ?, ?)`;
            const [result] = await db.execute(sql, [studentId, examYear, province, totalScore, rankInProvince]);
            return res.json({ message: 'Score submitted', insertId: result.insertId });
        } catch (err) {
            console.error('studentScore.post error', err);
            return res.status(500).json({ error: 'Server error' });
        }
    }
);

// 获取登录用户的成绩：/api/student-score/mine
router.get('/mine', authRequired, async (req, res) => {
    try {
        const userId = Number(req.user.userId);
        if (!Number.isFinite(userId)) return res.status(400).json({ error: 'Invalid user in token' });

        const [rows] = await db.execute('SELECT SCORE_ID, STUDENT_ID, EXAM_YEAR, PROVINCE, TOTAL_SCORE, RANK_IN_PROVINCE, CREATED_AT FROM student_score WHERE STUDENT_ID = ? ORDER BY EXAM_YEAR DESC', [userId]);
        return res.json({ data: rows });
    } catch (err) {
        console.error('studentScore.mine error', err);
        return res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;

