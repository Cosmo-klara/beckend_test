const jwt = require('jsonwebtoken');
require('dotenv').config();

const jwtSecret = process.env.JWT_SECRET || 'change_this_secret';

/**
 * 认证中间件：校验 Authorization 中的 Bearer Token 并将载荷挂载到 req.user。
 *
 * 行为说明：
 * - 从请求头读取 `Authorization: Bearer <token>`。
 * - 使用 `jwt.verify(token, jwtSecret)` 验证签名和过期时间。
 * - 校验成功：将解析出的载荷赋给 `req.user` 并调用 `next()`。
 *
 * 返回状态：
 * - 401 No authorization header：缺少授权头
 * - 401 Invalid authorization format：格式不是 Bearer
 * - 401 Invalid or expired token：令牌无效或过期
 */
function authRequired(req, res, next) {
    const authHeader = req.headers.authorization;
    if (!authHeader) return res.status(401).json({ error: 'No authorization header' });
    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0] !== 'Bearer') return res.status(401).json({ error: 'Invalid authorization format' });
    const token = parts[1];
    try {
        const payload = jwt.verify(token, jwtSecret);
        req.user = payload;
        return next();
    } catch (err) {
        return res.status(401).json({ error: 'Invalid or expired token' });
    }
}

module.exports = { authRequired };