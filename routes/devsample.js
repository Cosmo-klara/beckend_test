// routes/devSamples.js
const express = require('express');
const router = express.Router();
const db = require('../db');

// 把值强转为安全的正整数，带上上/下限
function toSafeInt(val, defaultVal = 3, min = 1, max = 50) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    const i = Math.floor(n);
    if (i < min) return min;
    if (i > max) return max;
    return i;
}

// 列表：要返回的表名（按你新 schema 定义）
const DEFAULT_TABLES = [
    'college_info',
    'major_info',
    'college_admission_score',
    'college_plan',
    'school_enrollment',
    'users',
    'student_score'
];

router.get('/', async (req, res) => {
    try {
        const { tables, sampleSize } = req.query;
        const limit = toSafeInt(sampleSize, 5, 1, 50);

        // 解析 requested tables
        let tableList = DEFAULT_TABLES;
        if (typeof tables === 'string' && tables.trim().length) {
            tableList = tables.split(',').map(s => s.trim()).filter(Boolean);
            // 过滤掉不在默认白名单中的表，防止任意表暴露
            tableList = tableList.filter(t => DEFAULT_TABLES.includes(t));
            if (tableList.length === 0) {
                return res.status(400).json({ error: 'No valid tables requested' });
            }
        }

        // 为每个表执行两个只读查询：
        // 1) SELECT * FROM <table> LIMIT <limit>;
        // 2) SELECT COUNT(*) as cnt FROM <table>;
        // 注意：我们把 limit 拼接进 SQL（经过 toSafeInt 校验），params 为空，从而避免驱动对 LIMIT 占位符的问题
        const results = {};
        for (const table of tableList) {
            try {
                const sampleSql = `SELECT * FROM \`${table}\` LIMIT ${limit}`;
                const countSql = `SELECT COUNT(*) AS cnt FROM \`${table}\``;
                // 查询样本
                const [rows] = await db.execute(sampleSql); // rows: array
                // 查询行数（可选）
                const [countRows] = await db.execute(countSql);
                const rowCount = Array.isArray(countRows) && countRows.length ? Number(countRows[0].cnt) : null;

                // 得到列名（如果没有行，则尝试 DESCRIBE）
                let columns = [];
                if (rows && rows.length > 0) {
                    columns = Object.keys(rows[0]);
                } else {
                    // 当没有数据时，使用 DESCRIBE 获取列名
                    try {
                        const [descRows] = await db.execute(`DESCRIBE \`${table}\``);
                        columns = Array.isArray(descRows) ? descRows.map(r => r.Field) : [];
                    } catch (e) {
                        columns = [];
                    }
                }

                // 转换样本值：把 Buffer 转为字符串、Date 转 ISO 字符串 等，避免序列化问题
                const normalize = r => {
                    const out = {};
                    for (const c of columns) {
                        let v = r[c];
                        if (Buffer.isBuffer(v)) v = v.toString('utf8');
                        else if (v instanceof Date) v = v.toISOString();
                        out[c] = v;
                    }
                    return out;
                };

                results[table] = {
                    columns,
                    samples: (rows || []).map(normalize),
                    rowCount
                };
            } catch (tableErr) {
                // 单表出错不要影响其它表，记录错误信息
                results[table] = { error: tableErr && tableErr.message ? tableErr.message : String(tableErr) };
                console.error(`[devSamples] error for table ${table}:`, tableErr);
            }
        }

        return res.json({ data: results, meta: { requestedTables: tableList, sampleSize: limit } });
    } catch (err) {
        console.error('devSamples error', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

module.exports = router;
