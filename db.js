// 似乎必须把数据库连接单独提取出来以避免循环依赖问题

const mysql = require('mysql2');

const pool = mysql.createConnection({
    host: 'localhost',
    port: 3306,
    user: 'root',
    password: 'cosmo',
    database: 'Manager',
    charset: 'utf8'
});

pool.connect(err => {
    if (err) throw err;
    console.log('Database connected!');
});

module.exports = pool;
