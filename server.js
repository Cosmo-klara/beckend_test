const express = require('express');
const cors = require('cors');
const path = require('path');
const bodyParser = require('body-parser');

// 注册路由
const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/user');

const app = express();
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.use('/auth', authRoutes);
app.use('/user', userRoutes);

app.use(express.static(path.join(__dirname, 'doc')));
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'doc', 'api.html'));
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
