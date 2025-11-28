const express = require('express');
const https = require('https');

const router = express.Router();

function fetchJSON(url, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, (resp) => {
            let data = '';
            resp.on('data', (chunk) => (data += chunk));
            resp.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(e);
                }
            });
        });
        req.on('error', reject);
        req.setTimeout(timeoutMs, () => {
            req.destroy(new Error('timeout'));
        });
    });
}

router.get('/', async (req, res) => {
    const province = (req.query.province || '四川').toString();
    const year = (req.query.year || '2021').toString();
    const category = (req.query.category || '理科').toString();

    const target =
        'https://opendata.baidu.com/api.php'
        + '?fromCard=1'
        + '&resource_id=50266'
        + `&province=${encodeURIComponent(province)}`
        + `&year=${encodeURIComponent(year)}`
        + `&category=${encodeURIComponent(category)}`
        + `&query=${encodeURIComponent('一分一段')}`;

    try {
        const json = await fetchJSON(target, 20000);
        res.status(200).json(json);
    } catch (e) {
        res.status(502).json({ error: 'proxy_upstream_error', detail: String(e) });
    }
});

module.exports = router;