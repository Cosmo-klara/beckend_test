// routes/studentScore.js
const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');
const { body, validationResult } = require('express-validator');

// 学生提交成绩（受保护，仅本人或管理员）
router.post('/', authRequired,
    body('studentId').notEmpty(),
    body('examYear').isInt(),
    body('province').notEmpty(),
    body('totalScore').isFloat(),
    async (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

        const { studentId, examYear, province, totalScore, rankInProvince } = req.body;
        // 简单授权：如果非管理员，studentId 必须等于登录用户 id
        if (req.user && req.user.userId && req.user.userId !== studentId) {
            return res.status(403).json({ error: 'Cannot submit score for other user' });
        }

        try {
            const sql = `INSERT INTO student_score (SCORE_ID, STUDENT_ID, EXAM_YEAR, PROVINCE, TOTAL_SCORE, RANK_IN_PROVINCE)
                VALUES (NULL, ?, ?, ?, ?, ?)`;
            const [result] = await db.execute(sql, [studentId, examYear, province, totalScore, rankInProvince || null]);
            return res.json({ message: 'Score submitted', insertId: result.insertId });
        } catch (err) {
            console.error(err);
            return res.status(500).json({ error: 'Server error' });
        }
    }
);

// 获取指定用户最近成绩
router.get('/mine', authRequired, async (req, res) => {
    try {
        const userId = req.user.userId;
        const [rows] = await db.execute('SELECT * FROM student_score WHERE STUDENT_ID = ? ORDER BY EXAM_YEAR DESC', [userId]);
        return res.json({ data: rows });
    } catch (err) {
        console.error(err);
        return res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;
