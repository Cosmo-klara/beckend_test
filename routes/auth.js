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

// 注册
router.post('/register',
    body('id').isLength({ min: 1 }),
    body('password').isLength({ min: 6 }),
    async (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

        const { id, password, username, province, school_id } = req.body;
        // 这里假设用户id长度固定（如你之前的逻辑），但不要通过拼表名处理
        // 统一使用 users 表
        try {
            const hash = await bcrypt.hash(password, SALT_ROUNDS);
            const sql = `INSERT INTO users (USER_ID, USERNAME, PASSWORD, PROVINCE, SCHOOL_ID, STATUS, CREATED_AT)
                VALUES (?, ?, ?, ?, ?, 1, NOW())`;
            const [result] = await db.execute(sql, [id, username || id, hash, province || null, school_id || null]);
            return res.json({ message: 'Register successful', insertId: result.insertId });
        } catch (err) {
            if (err && err.code === 'ER_DUP_ENTRY') return res.status(400).json({ error: 'ID already exists' });
            console.error(err);
            return res.status(500).json({ error: 'Server error' });
        }
    }
);

// 登录
router.post('/login',
    body('id').isLength({ min: 1 }),
    body('password').isLength({ min: 1 }),
    async (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

        const { id, password } = req.body;
        try {
            const [rows] = await db.execute('SELECT USER_ID, USERNAME, PASSWORD, STATUS, PROVINCE, SCHOOL_ID FROM users WHERE USER_ID = ?', [id]);
            if (rows.length === 0) return res.status(400).json({ error: 'User not found' });
            const user = rows[0];
            if (user.STATUS === 0) return res.status(403).json({ error: 'Account disabled' });

            const match = await bcrypt.compare(password, user.PASSWORD);
            if (!match) return res.status(400).json({ error: 'Incorrect password' });

            // 生成 JWT，payload 可包含常用信息，供后续请求使用（注意不要放敏感信息）
            const payload = {
                userId: user.USER_ID,
                username: user.USERNAME,
                province: user.PROVINCE,
                schoolId: user.SCHOOL_ID
            };
            const token = jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });

            // 将登录后的用户信息返回给前端（同时前端保留 token）
            return res.json({ message: 'Login successful', token, user: payload });
        } catch (err) {
            console.error(err);
            return res.status(500).json({ error: 'Server error' });
        }
    }
);

module.exports = router;
