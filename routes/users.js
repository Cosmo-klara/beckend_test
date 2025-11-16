// routes/users.js
const express = require('express');
const router = express.Router();
const db = require('../db'); 
const { authRequired } = require('../middleware/auth');
const bcrypt = require('bcrypt');
const { body, validationResult } = require('express-validator');

const SALT_ROUNDS = parseInt(process.env.SALT_ROUNDS || '10', 10);

// ---------- 修改用户资料（用户名、所在高中、所在省份等） ----------
// PATCH /users/me
// body: { username?, schoolName?, province? }
router.patch('/me',
    authRequired,
    // 校验（如果字段存在则校验）
    body('username').optional().isLength({ min: 5, max: 50 }).matches(/^[A-Za-z0-9_]+$/).withMessage('用户名需为5-50位字母/数字/下划线'),
    body('schoolName').optional().isLength({ max: 255 }).withMessage('学校名称过长'),
    body('province').optional().isLength({ max: 48 }).withMessage('省份名称过长'),
    async (req, res) => {
        try {
            const errors = validationResult(req);
            if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

            const userId = req.user && req.user.userId;
            if (!userId) return res.status(401).json({ error: '未认证用户' });

            const { username, schoolName, province } = req.body;

            // 构造更新字段列表
            const updates = [];
            const params = [];

            if (username) {
                // 检查用户名是否被占用（除去当前用户）
                const [rows] = await db.execute('SELECT USER_ID FROM users WHERE USERNAME = ? AND USER_ID <> ?', [username, userId]);
                if (rows && rows.length > 0) {
                    return res.status(400).json({ error: '用户名已被占用' });
                }
                updates.push('USERNAME = ?');
                params.push(username);
            }

            if (typeof schoolName !== 'undefined') {
                updates.push('SCHOOL_NAME = ?');
                params.push(schoolName || null);
            }

            if (typeof province !== 'undefined') {
                updates.push('PROVINCE = ?');
                params.push(province || null);
            }

            if (updates.length === 0) {
                return res.status(400).json({ error: '没有可更新的字段' });
            }

            params.push(userId);
            const sql = `UPDATE users SET ${updates.join(', ')} WHERE USER_ID = ?`;
            await db.execute(sql, params);

            // 返回更新后的基本信息（不包含密码）
            const [newRows] = await db.execute('SELECT USER_ID, USERNAME, PROVINCE, SCHOOL_NAME, STATUS, CREATED_AT FROM users WHERE USER_ID = ?', [userId]);
            return res.json({ message: '更新成功', user: newRows[0] });
        } catch (err) {
            console.error('users.update error', err);
            // 捕获重复键（并发竞争）等
            if (err && err.code === 'ER_DUP_ENTRY') {
                return res.status(400).json({ error: '用户名冲突' });
            }
            return res.status(500).json({ error: '服务器错误', detail: err && err.message });
        }
    }
);

// ---------- 修改密码 ----------
// POST /users/change-password
// body: { oldPassword, newPassword }
router.post('/change-password',
    authRequired,
    body('oldPassword').isLength({ min: 1 }).withMessage('旧密码不能为空'),
    body('newPassword').isLength({ min: 6 }).withMessage('新密码至少6位'),
    async (req, res) => {
        try {
            const errors = validationResult(req);
            if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

            const userId = req.user && req.user.userId;
            if (!userId) return res.status(401).json({ error: '未认证用户' });

            const { oldPassword, newPassword } = req.body;

            // 读取当前哈希
            const [rows] = await db.execute('SELECT PASSWORD FROM users WHERE USER_ID = ?', [userId]);
            if (!rows || rows.length === 0) return res.status(404).json({ error: '用户不存在' });

            const currentHash = rows[0].PASSWORD;
            if (!currentHash) return res.status(400).json({ error: '未设置密码' });

            // 校验旧密码
            const match = await bcrypt.compare(oldPassword, currentHash);
            if (!match) return res.status(400).json({ error: '旧密码不正确' });

            // 生成新哈希并更新
            const newHash = await bcrypt.hash(newPassword, SALT_ROUNDS);

            await db.execute('UPDATE users SET PASSWORD = ? WHERE USER_ID = ?', [newHash, userId]);

            return res.json({ message: '密码修改成功' });
        } catch (err) {
            console.error('users.changePassword error', err);
            return res.status(500).json({ error: '服务器错误', detail: err && err.message });
        }
    }
);

module.exports = router;
