// 似乎必须把数据库连接单独提取出来以避免循环依赖问题

const mysql = require('mysql2/promise');
require('dotenv').config();

const pool = mysql.createPool({
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT ? parseInt(process.env.DB_PORT) : 3306,
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || 'cosmo',
    database: process.env.DB_NAME || 'Manager',
    charset: 'utf8mb4',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

// pool.connect(err => {
//     if (err) throw err;
//     console.log('Database connected!');
// });

module.exports = pool;
