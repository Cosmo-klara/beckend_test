## 咕咕嘎嘎

### 数据库建立

在 ZYGC 那个项目中找到 create.sql 文件, 以此建立测试数据库即可

随后在本项目中，找到 `db.js` 文件，可以看到连接池配置，直接修改为你的数据库配置即可，当然最好还是在同级目录下面创建一个 `.env` 文件，示例内容如下

```js
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=cosmo
DB_NAME=Manager
JWT_SECRET='change_this_secret'(你的强随机密钥) // 这个是中间层用的，不配置也行
JWT_EXPIRES_IN=7d
```

### 后端服务部署

应该终端直接一个 `npm install` 安装完就可以了

如果有缺少模块的问题, 装一下下面的模块

```bash
npm install express mysql2 bcrypt jsonwebtoken dotenv express-validator
```

然后终端 `node server.js` 就能把后端服务启动了

#### ngrok 公网访问

> 这块不用管

```bash
ngrok http --url=marlyn-unalleviative-annabel.ngrok-free.dev 3000
```

### 关于前端技术栈

#### Web

Vue3

#### PC 端

Electron

#### 移动端

Flutter/React Native
