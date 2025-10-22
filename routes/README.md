## 接口文档

> 用于展示

[接口文档](../doc/Interface.md)

## 接口测试及详细数据格式查看

[Interface_test.ipynb](../doc/Interface_test.ipynb)

## 接口对接说明

> 需要增加接口功能请整理成文档在 GitHub 上提交 issue，我会尽快处理。

### 使用范例：

> vue有一个uni的请求库应该是，我没用，前端对接的可以用AI或者自己研究一下，应该是可以用 `vite.config.js` 来做代理配置这样接口就能省略掉前面的网址了

+ 后端

    ```js
    router.post('/login', (req, res) => {
        const { id, password } = req.body;

        let tableName;
        if (id.length === 9)
            tableName = 'users';
        else if (id.length === 6)
            tableName = 'station_managers';
        else
            return res.status(400).send('Invalid ID');

        const sql = `SELECT * FROM ${tableName} WHERE id = ?`;

        db.query(sql, [id], (err, result) => {
            if (err) throw err;
            if (result.length === 0)
                return res.status(400).send('User not found');
            const user = result[0];
            if (user.password !== password)
                return res.status(400).send('Incorrect password');

            res.send({ message: 'Login successful', user, role: tableName });
        });
    });
    ```

+ 前端

    ```js
        // 登录接口
    fetch('http://127.0.0.1:3000/auth/login', { // auth 是后端路由，/login 相当于后端路由下的子路由
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: form.value.id, password: form.value.password }) // 传递用户名和密码(请求参数)
    })
        .then(response => response.json()) // 解析响应为JSON格式
        .then(data => {
        if (data.message === 'Login successful') { // 这里就是用后端返回的数据来判断登录是否成功
            loginMessage.value = '登录成功';
            loginMessageColor.value = 'green';

            // 获取登录者角色 （user or station_manager）
            const role = data.role;
            let redirectUrl;
            if (role === 'users') {
            redirectUrl = '/pages/index/index';
            } else if (role === 'station_managers') {
            redirectUrl = '/pages/index/index';
            }
            setTimeout(() => {
            uni.redirectTo({ url: redirectUrl });
            }, 1000); // 1秒后跳转

        } else {
            loginMessage.value = data.message || '登录失败，请重试';
            loginMessageColor.value = 'red';
        }
        })
        .catch(error => {
        loginMessage.value = '请求出错，请稍后重试';
        loginMessageColor.value = 'red';
        console.error('Error:', error);
        });
    ```
