const express = require('express');
const router = express.Router();
const db = require('../db.js');

router.post('/rename', (req, res) => {
    const { userId, user_name } = req.body;
    if (!userId || !user_name)
        return res.status(400).send({ message: '缺少 userId 或 user_name 参数' });
    const sql = `UPDATE users SET user_name =? WHERE id =?`;

    db.query(sql, [user_name, userId], (err, result) => {
        if (err) throw err;
        if (result.affectedRows === 0) {
            return res.status(404).send({ message: '用户不存在或更新失败' });
        }
        res.send({ message: '用户名更新成功' });
    })
})

router.post('/reset_password', (req, res) => {
    const { userId, new_password } = req.body;
    if (!userId || !new_password)
        return res.status(400).send({ message: '缺少 userId 或 new_password 参数' });

    const checkSql = `SELECT * FROM users WHERE id = ?`;
    db.query(checkSql, [userId], (err, result) => {
        if (err) return res.status(500).send({ message: '数据库错误' });
        if (result.length === 0)
            return res.status(404).send({ message: '用户不存在' });

        const updateSql = `UPDATE users SET password = ? WHERE id = ?`;
        db.query(updateSql, [new_password, userId], (err, result) => {
            if (err) return res.status(500).send({ message: '密码更新失败' });
            res.send({ message: '密码重置成功' });
        });
    });
});


module.exports = router;
