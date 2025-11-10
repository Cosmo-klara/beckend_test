const express = require('express');
const cors = require('cors');
const path = require('path');
const bodyParser = require('body-parser');

// 注册路由
const authRouter = require('./routes/auth');
const collegesRouter = require('./routes/colleges');
const majorsRouter = require('./routes/majors');
const plansRouter = require('./routes/plans');
const schoolEnrollmentRouter = require('./routes/schoolEnrollment');
const studentScoreRouter = require('./routes/studentScore');
const devSamplesRouter = require('./routes/devsample');

const app = express();

app.use(express.json());
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.use('/auth', authRouter);
app.use('/colleges', collegesRouter);
app.use('/majors', majorsRouter);
app.use('/plans', plansRouter);
app.use('/school-enrollment', schoolEnrollmentRouter);
app.use('/student-score', studentScoreRouter);
app.use('/dev-samples', devSamplesRouter);

app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
});

app.use('/public', express.static(path.join(__dirname, 'public')));

app.get('/dev', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'dev-samples-ui.html'));
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
