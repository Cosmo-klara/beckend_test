// routes/auth.js
const express = require('express');
const router = express.Router();
const db = require('../db');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { body, validationResult } = require('express-validator');
require('dotenv').config();

const JWT_SECRET = process.env.JWT_SECRET || 'change_this_secret';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';
const SALT_ROUNDS = 10;

// 生成唯一的用户ID（BIGINT）
// 规则：YYYY + 6位随机数，碰撞则重试；多次碰撞后回退为 MAX(USER_ID)+1
async function generateUniqueUserId() {
    const year = new Date().getFullYear();
    for (let attempt = 0; attempt < 10; attempt++) {
        const candidate = Number(`${year}${Math.floor(100000 + Math.random() * 900000)}`);
        const [rows] = await db.execute('SELECT 1 FROM users WHERE USER_ID = ?', [candidate]);
        if (rows.length === 0) return candidate;
    }
    const base = Number(`${year}000000`);
    const [maxRows] = await db.execute('SELECT IFNULL(MAX(USER_ID), ?) AS maxId FROM users', [base]);
    const maxId = Number(maxRows[0].maxId);
    return maxId + 1;
}

// 注册（使用 username + password，USER_ID 后端自动生成）
// 注意：users 表的 USERNAME 最大 20 字符
router.post('/register',
    body('username').isLength({ min: 5, max: 20 }).matches(/^[A-Za-z0-9_]+$/),
    body('password').isLength({ min: 6 }),
    body('province').isLength({ min: 1 }).withMessage('province required'),
    body('schoolName').isLength({ min: 1 }).withMessage('schoolName required'),
    async (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

        const { username, password, province, schoolName } = req.body;

        try {
            const [exists] = await db.execute('SELECT 1 FROM users WHERE USERNAME = ?', [username]);
            if (exists.length > 0) return res.status(400).json({ error: 'Username already exists' });

            const userId = await generateUniqueUserId();
            const hash = await bcrypt.hash(password, SALT_ROUNDS);

            // 注意：users 表现在使用 SCHOOL_NAME 而非 SCHOOL_ID，且 PROVINCE 为 NOT NULL
            const sql = `INSERT INTO users (USER_ID, USERNAME, PASSWORD, PROVINCE, SCHOOL_NAME, STATUS, CREATED_AT)
                VALUES (?, ?, ?, ?, ?, 1, NOW())`;
            const [result] = await db.execute(sql, [userId, username, hash, province, schoolName]);

            return res.json({ message: 'Register successful', userId });
        } catch (err) {
            if (err && err.code === 'ER_DUP_ENTRY') {
                return res.status(400).json({ error: 'Username or ID already exists' });
            }
            console.error('auth.register error', err);
            return res.status(500).json({ error: 'Server error' });
        }
    }
);

// 登录：username + password（返回 JWT）
// 返回的 payload 包含 userId, username, province, schoolName
router.post('/login',
    body('username').isLength({ min: 5, max: 20 }).matches(/^[A-Za-z0-9_]+$/),
    body('password').isLength({ min: 1 }),
    async (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

        const { username, password } = req.body;
        try {
            const [rows] = await db.execute('SELECT USER_ID, USERNAME, PASSWORD, STATUS, PROVINCE, SCHOOL_NAME FROM users WHERE USERNAME = ?', [username]);
            if (rows.length === 0) return res.status(400).json({ error: 'User not found' });
            const user = rows[0];
            if (user.STATUS === 0) return res.status(403).json({ error: 'Account disabled' });

            const match = await bcrypt.compare(password, user.PASSWORD);
            if (!match) return res.status(400).json({ error: 'Incorrect password' });

            const payload = {
                userId: user.USER_ID,
                username: user.USERNAME,
                province: user.PROVINCE,
                schoolName: user.SCHOOL_NAME
            };
            const token = jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });

            return res.json({ message: 'Login successful', token, user: payload });
        } catch (err) {
            console.error('auth.login error', err);
            return res.status(500).json({ error: 'Server error' });
        }
    }
);

module.exports = router;
