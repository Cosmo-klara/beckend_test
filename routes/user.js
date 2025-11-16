const express = require('express');
const router = express.Router();
const { body, validationResult } = require('express-validator');
const db = require('../db');
const { authRequired } = require('../middleware/auth');

const usernameValidator = body('username')
    .optional()
    .trim()
    .isLength({ min: 5, max: 20 }).withMessage('username length must be 5-20 characters')
    .matches(/^[A-Za-z0-9_]+$/).withMessage('username must be alphanumeric with underscore');

const provinceValidator = body('province')
    .optional()
    .trim()
    .isLength({ min: 1, max: 48 }).withMessage('province length must be 1-48 characters');

const schoolValidator = body('schoolName')
    .optional()
    .trim()
    .isLength({ min: 1, max: 255 }).withMessage('schoolName length must be 1-255 characters');

router.post('/profile', authRequired, [usernameValidator, provinceValidator, schoolValidator], async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
    }

    const userId = Number(req.user.userId);
    if (!Number.isFinite(userId)) {
        return res.status(400).json({ error: 'Invalid user in token' });
    }

    const { username, province, schoolName } = req.body;
    const updates = {};
    if (typeof username === 'string') updates.USERNAME = username;
    if (typeof province === 'string') updates.PROVINCE = province;
    if (typeof schoolName === 'string') updates.SCHOOL_NAME = schoolName;

    if (Object.keys(updates).length === 0) {
        return res.status(400).json({ error: 'No fields to update' });
    }

    try {
        if (updates.USERNAME) {
            const [exists] = await db.execute('SELECT USER_ID FROM users WHERE USERNAME = ? AND USER_ID <> ?', [updates.USERNAME, userId]);
            if (exists.length > 0) {
                return res.status(400).json({ error: 'Username already exists' });
            }
        }

        const setClauses = [];
        const params = [];
        for (const [column, value] of Object.entries(updates)) {
            setClauses.push(`${column} = ?`);
            params.push(value);
        }
        params.push(userId);

        const sql = `UPDATE users SET ${setClauses.join(', ')} WHERE USER_ID = ?`;
        const [result] = await db.execute(sql, params);
        if (result.affectedRows === 0) {
            return res.status(404).json({ error: 'User not found' });
        }

        const [rows] = await db.execute('SELECT USER_ID, USERNAME, PROVINCE, SCHOOL_NAME FROM users WHERE USER_ID = ?', [userId]);
        if (!rows || rows.length === 0) {
            return res.status(404).json({ error: 'User not found' });
        }

        const user = rows[0];
        return res.json({
            message: 'Profile updated successfully',
            user: {
                userId: user.USER_ID,
                username: user.USERNAME,
                province: user.PROVINCE,
                schoolName: user.SCHOOL_NAME
            }
        });
    } catch (err) {
        console.error('user.profile error', err);
        return res.status(500).json({ error: 'Server error' });
    }
});

module.exports = router;
