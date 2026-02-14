#!/bin/bash
# ============================================
# Silicon-Empire 一键部署脚本
# 在服务器 43.167.223.116 上运行
# ============================================
set -e

echo "🛸 Silicon-Empire 部署开始"
echo "=================================="

# 1. 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "📦 安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

if ! command -v docker-compose &> /dev/null; then
    echo "📦 安装 Docker Compose..."
    apt-get update && apt-get install -y docker-compose-plugin
fi

echo "✅ Docker 就绪"

# 2. 创建项目目录
PROJECT_DIR="/opt/silicon-empire"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📁 创建项目目录: $PROJECT_DIR"
    mkdir -p $PROJECT_DIR
fi

# 3. 同步代码 (如果是 git 项目)
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "📥 拉取最新代码..."
    cd $PROJECT_DIR && git pull
else
    echo "⚠️  请先将代码上传到 $PROJECT_DIR"
    echo "    方式 1: git clone <repo> $PROJECT_DIR"
    echo "    方式 2: scp -r ./silicon-empire/ root@43.167.223.116:$PROJECT_DIR"
fi

cd $PROJECT_DIR

# 4. 检查 .env
if [ ! -f .env ]; then
    echo "❌ .env 文件不存在！请先复制 .env.example 并填入凭证"
    exit 1
fi
echo "✅ .env 配置文件存在"

# 5. 防火墙
echo "🔥 配置防火墙..."
ufw allow 8000/tcp comment "Silicon-Empire API" 2>/dev/null || true
ufw allow 5678/tcp comment "n8n Dashboard" 2>/dev/null || true
echo "✅ 防火墙已配置 (8000, 5678)"

# 6. 启动服务
echo ""
echo "🚀 启动 Docker 服务..."
docker compose -f docker-compose.prod.yml up -d --build

# 7. 等待健康检查
echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 8. 验证
echo ""
echo "🔍 健康检查..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API 服务正常 (port 8000)"
else
    echo "⚠️  API 尚未就绪，请稍后检查: docker logs silicon-empire-api"
fi

echo ""
echo "=================================="
echo "📊 服务状态:"
docker compose -f docker-compose.prod.yml ps
echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 访问地址:"
echo "   API:  http://43.167.223.116:8000"
echo "   n8n:  http://43.167.223.116:5678 (admin / silicon-empire)"
echo "   健康: http://43.167.223.116:8000/health"
echo ""
echo "📋 常用命令:"
echo "   查看日志: docker logs silicon-empire-api -f"
echo "   重启:     docker compose -f docker-compose.prod.yml restart"
echo "   停止:     docker compose -f docker-compose.prod.yml down"
echo "=================================="
