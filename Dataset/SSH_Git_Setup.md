# Git SSH配置说明

## 修改说明

Dataset评估框架已将所有git clone操作从HTTPS改为SSH方式，以避免用户名密码认证问题。

## 修改内容

### 1. SWE-bench数据集
- 原地址：`https://github.com/princeton-nlp/SWE-bench.git`
- 新地址：`git@github.com:princeton-nlp/SWE-bench.git`

### 2. BugsInPy数据集
- 原地址：`https://github.com/wenmin-wu/BugsInPy.git`
- 新地址：`git@github.com:wenmin-wu/BugsInPy.git`

## 使用前准备

使用SSH方式克隆GitHub仓库需要配置SSH密钥：

### 1. 生成SSH密钥（如果还没有）
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 2. 添加SSH密钥到ssh-agent
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### 3. 添加SSH公钥到GitHub
1. 复制公钥：
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

2. 登录GitHub，进入 Settings > SSH and GPG keys
3. 点击"New SSH key"，粘贴公钥内容

### 4. 测试SSH连接
```bash
ssh -T git@github.com
```

如果看到"Hi username! You've successfully authenticated"，说明配置成功。

## 优势

使用SSH方式的优势：
- 无需输入用户名密码
- 更安全，使用公私钥认证
- 支持更方便的自动化脚本

## 故障排除

如果遇到问题，请检查：
1. SSH密钥是否正确配置
2. 是否能成功连接GitHub
3. 网络连接是否正常

## 回退方案

如果确实需要使用HTTPS方式，可以修改回原地址：
- SWE-bench: `https://github.com/princeton-nlp/SWE-bench.git`
- BugsInPy: `https://github.com/wenmin-wu/BugsInPy.git`

但需要注意可能需要配置GitHub token或处理认证问题。