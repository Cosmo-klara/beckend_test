// routes/colleges.js
const express = require('express');
const router = express.Router();
const db = require('../db');
const { authRequired } = require('../middleware/auth');

// 安全整数转换
function toSafeInt(val, defaultVal = 1, min = 1, max = 1000000) {
    const n = Number(val);
    if (!Number.isFinite(n) || Number.isNaN(n)) return defaultVal;
    const i = Math.floor(n);
    if (i < min) return min;
    if (i > max) return max;
    return i;
}

// 省份规范化（去除 “省/市/自治区/特别行政区” 后缀）
function normalizeProvince(name) {
    if (!name) return null;
    let s = String(name).trim();
    const suffixes = ['特别行政区','维吾尔自治区','壮族自治区','回族自治区','自治区','省','市'];
    for (const suf of suffixes) {
        if (s.endsWith(suf)) { s = s.slice(0, -suf.length); break; }
    }
    return s;
}

// 列表接口：支持 q(province/name模糊)，province, is985, is211, page, pageSize
router.get('/', async (req, res) => {
    try {
        const q = typeof req.query.q === 'string' ? req.query.q.trim() : '';
        const province = typeof req.query.province === 'string' && req.query.province.trim() ? req.query.province.trim() : null;
        const is985 = req.query.is985 != null ? (req.query.is985 === '1' || req.query.is985 === 'true' || req.query.is985 === 1) : null;
        const is211 = req.query.is211 != null ? (req.query.is211 === '1' || req.query.is211 === 'true' || req.query.is211 === 1) : null;

        const page = toSafeInt(req.query.page, 1, 1, 1000000);
        const pageSize = toSafeInt(req.query.pageSize, 20, 1, 200);
        const offset = (page - 1) * pageSize;

        const whereParts = [];
        const params = [];

        if (province) {
            whereParts.push('PROVINCE = ?');
            params.push(province);
        }
        if (is985 !== null) {
            // 表里用 TINYINT(1) 存 0/1
            whereParts.push('IS_985 = ?');
            params.push(is985 ? 1 : 0);
        }
        if (is211 !== null) {
            whereParts.push('IS_211 = ?');
            params.push(is211 ? 1 : 0);
        }
        if (q) {
            // 限制 q 长度以防超长参数
            const safeQ = q.length > 200 ? q.slice(0, 200) : q;
            // 这里直接使用 LIKE，不使用 ESCAPE（更简单、兼容）
            whereParts.push('(COLLEGE_NAME LIKE ? OR BASE_INTRO LIKE ?)');
            params.push(`%${safeQ}%`, `%${safeQ}%`);
        }

        const whereSql = whereParts.length ? ('WHERE ' + whereParts.join(' AND ')) : '';

        // 先取总数（注意：COUNT 使用同样的 params）
        const countSql = `SELECT COUNT(*) AS total FROM college_info ${whereSql}`;
        // SELECT 主体（把 LIMIT/OFFSET 的整数直接拼入 SQL）
        const selectSql = `SELECT COLLEGE_CODE, COLLEGE_NAME, IS_985, IS_211, IS_DFC, PROVINCE, CITY_NAME, BASE_INTRO
                    FROM college_info
                    ${whereSql}
                    ORDER BY COLLEGE_NAME
                    LIMIT ${pageSize} OFFSET ${offset}`;


        const [countRows] = await db.execute(countSql, params);
        const total = Array.isArray(countRows) && countRows.length ? Number(countRows[0].total) : 0;

        const [rows] = await db.execute(selectSql, params);
        return res.json({ data: rows, meta: { page, pageSize, total } });
    } catch (err) {
        console.error('colleges.list error', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

router.get('/recommend', async (req, res) => {
    try {
        const objectiveWeight = Math.max(0, Math.min(1, Number(req.query.objectiveWeight ?? 0.8)));
        let swRegion = Number(req.query.sw_region ?? 0.4);
        let swLevel = Number(req.query.sw_level ?? 0.35);
        let swMajor = Number(req.query.sw_major ?? 0.25);
        const subjectSum = swRegion + swLevel + swMajor;
        if (!Number.isFinite(subjectSum) || subjectSum <= 0) { swRegion = 0.4; swLevel = 0.35; swMajor = 0.25; }

        const regions = typeof req.query.regions === 'string' ? req.query.regions.split(',').map(s => s.trim()).filter(Boolean) : [];
        const prefer985 = req.query.is985 === '1' || req.query.is985 === 'true';
        const prefer211 = req.query.is211 === '1' || req.query.is211 === 'true';
        const preferDFC = req.query.isDFC === '1' || req.query.isDFC === 'true';
        const majorPattern = typeof req.query.majorPattern === 'string' ? req.query.majorPattern.trim() : '';

        const rRaw = Number(req.query.rank);
        const userRank = Number.isFinite(rRaw) ? Math.floor(rRaw) : (req.user && Number.isFinite(Number(req.user.rank)) ? Math.floor(Number(req.user.rank)) : null);
        const sourceProvinceRaw = (typeof req.query.province === 'string' && req.query.province.trim()) ? req.query.province.trim() : (req.user && req.user.province ? String(req.user.province) : null);
        const sourceProvince = normalizeProvince(sourceProvinceRaw);
        if (userRank == null || !sourceProvince) return res.status(400).json({ error: 'Missing rank or province' });

        const margin = userRank < 300 ? 60 : userRank < 1000 ? 200 : userRank < 5000 ? 300 : userRank < 20000 ? 1200 : 2000;

        const params = [sourceProvince, 2017, 2020];
        let whereMajor = '';
        if (majorPattern) { whereMajor = ' AND a.MAJOR_NAME LIKE ?'; params.push('%' + majorPattern + '%'); }
        const sql = `SELECT a.COLLEGE_CODE, i.COLLEGE_NAME, i.PROVINCE AS COLLEGE_PROVINCE, i.IS_985, i.IS_211, i.IS_DFC,
                            a.ADMISSION_YEAR, a.MIN_RANK, a.MIN_SCORE, a.MAJOR_NAME
                     FROM college_admission_score a
                     JOIN college_info i ON i.COLLEGE_CODE = a.COLLEGE_CODE
                     WHERE a.PROVINCE = ? AND a.ADMISSION_YEAR BETWEEN ? AND ?${whereMajor}`;
        const [rows] = await db.execute(sql, params);

        const byCollege = new Map();
        for (const r of rows) {
            const code = r.COLLEGE_CODE;
            let arr = byCollege.get(code);
            if (!arr) { arr = []; byCollege.set(code, arr); }
            if (Number.isFinite(Number(r.MIN_RANK))) arr.push(r);
        }

        const results = [];
        for (const [code, arr] of byCollege.entries()) {
            if (arr.length === 0) continue;
            arr.sort((a, b) => b.ADMISSION_YEAR - a.ADMISSION_YEAR);
            const lastYears = arr.slice(0, 3);
            const avgRank = lastYears.reduce((s, x) => s + Number(x.MIN_RANK), 0) / lastYears.length;
            const diff = userRank - avgRank;
            let prob;
            if (diff < 0) {
                const t = (-diff) / margin;
                prob = 0.70 + t * (0.80 - 0.70);
            } else {
                const t = diff / margin;
                prob = 0.70 - t * (0.70 - 0.35);
            }
            prob = Number(Math.max(0, Math.min(1, prob)).toFixed(4));

            const college = lastYears[0];
            const regionMatch = regions.length ? regions.includes(String(college.COLLEGE_PROVINCE)) : false;
            const levelMatch = (prefer985 && college.IS_985 == 1) || (prefer211 && college.IS_211 == 1) || (preferDFC && college.IS_DFC == 1);
            const majorMatch = !!majorPattern;
            const subjRaw = (regionMatch ? swRegion : 0) + (levelMatch ? swLevel : 0) + (majorMatch ? swMajor : 0);
            const subjScore = subjectSum > 0 ? (subjRaw / subjectSum) : 0;
            const totalScore = objectiveWeight * prob + (1 - objectiveWeight) * subjScore;

            results.push({
                COLLEGE_CODE: code,
                COLLEGE_NAME: college.COLLEGE_NAME,
                PROVINCE: college.COLLEGE_PROVINCE,
                IS_985: college.IS_985,
                IS_211: college.IS_211,
                IS_DFC: college.IS_DFC,
                probability: prob,
                matchScore: Number(totalScore.toFixed(4)),
                admissions: lastYears.map(x => ({ year: x.ADMISSION_YEAR, minScore: x.MIN_SCORE, minRank: x.MIN_RANK, major: x.MAJOR_NAME }))
            });
        }
        const ref = [], rush = [], stable = [], safe = [];
        for (const r of results) {
            const p = Number(r.probability) || 0;
            if (p >= 0.75) { r.category = '保'; safe.push(r); }
            else if (p >= 0.4) { r.category = '稳'; stable.push(r); }
            else if (p >= 0.2) { r.category = '冲'; rush.push(r); }
            else { r.category = '参考'; ref.push(r); }
        }
        ref.sort((a, b) => b.matchScore - a.matchScore);
        rush.sort((a, b) => b.matchScore - a.matchScore);
        stable.sort((a, b) => b.matchScore - a.matchScore);
        safe.sort((a, b) => b.matchScore - a.matchScore);
        const finalResults = [
            ...ref.slice(0, 5),
            ...rush.slice(0, 5),
            ...stable.slice(0, 5),
            ...safe.slice(0, 5)
        ];
        return res.json({ data: finalResults });
    } catch (err) {
        console.error('colleges.recommend error', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

router.get('/:collegeCode', async (req, res) => {
    try {
        const code = req.params.collegeCode;
        // basic validation
        if (!/^\d+$/.test(String(code))) return res.status(400).json({ error: 'Invalid college code' });
        const [rows] = await db.execute('SELECT * FROM college_info WHERE COLLEGE_CODE = ?', [code]);
        if (!rows || rows.length === 0) return res.status(404).json({ error: 'College not found' });
        return res.json({ data: rows[0] });
    } catch (err) {
        console.error('colleges.get error', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});


router.get('/:collegeCode/admissions', authRequired, async (req, res) => {
    try {
        const collegeCode = parseInt(req.params.collegeCode);
        const { province, year } = req.query;
        if (!Number.isFinite(collegeCode)) return res.status(400).json({ error: 'Invalid collegeCode' });

        let where = 'WHERE COLLEGE_CODE = ?';
        const params = [collegeCode];
        if (province) { where += ' AND PROVINCE = ?'; params.push(province); }
        if (year) { where += ' AND ADMISSION_YEAR = ?'; params.push(year); }

        const sql = `SELECT ADMISSION_ID, MAJOR_NAME, TYPE, PROVINCE, ADMISSION_YEAR, MIN_SCORE, MIN_RANK
                FROM college_admission_score ${where} ORDER BY ADMISSION_YEAR DESC`;
        const [rows] = await db.execute(sql, params);
        return res.json({ data: rows });
    } catch (err) {
        console.error('colleges.admissions error', err);
        return res.status(500).json({ error: 'Server error', detail: err && err.message });
    }
});

// 推荐接口：


module.exports = router;
